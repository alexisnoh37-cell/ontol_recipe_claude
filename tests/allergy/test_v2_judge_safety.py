"""Jev가 순위를 정하는 경로(decisions D10, docs/plan.md 부록 G-12)의 안전성. 신규 — 사람 승인 대상.

제외는 규칙이 먼저 끝낸다. Jev 판단기가 어떤 답을 주든(보낸 적 없는 key, 레시피 id, 최고점, 오류)
제외된 레시피가 결과에 들어오지 않는다. 걸러내기(screen) 보충 경로도 제외를 통과한 레시피만 본다.
Jev에는 알레르기·절대 안 먹는 재료·사용자 id·레시피 id를 보내지 않는다(실제 어댑터를 가짜 HTTP로 시험).
"""

from __future__ import annotations

import json

import httpx
import pytest

from engine.v2.config import load_v2_config
from engine.v2.model import V2Request
from engine.v2.ports import ASPECTS, RerankAnswer, RerankError
from engine.v2.profile import SimpleProfile
from engine.v2.recommend import RecommenderV2
from integrations.jev.client import JevClient
from integrations.jev.judge import JevJudge
from tests.allergy import fixtures as fx
from tests.support.engine_fixtures import CONFIG_DIR, build_recommender

LIMIT = len(fx.RECIPES) + 10
UNSAFE_FOR_SHRIMP = {"shrimp_stirfry", "cabbage_saeujeot_soup", "kimchi_fried_rice", "kimchi_sauce_potato",
                     "jeotgal_cabbage_salad"}


class Hostile:
    """보낸 후보에 최고점을 주고, 보낸 적 없는 key(레시피 id 포함)에도 답을 붙인다."""

    model = "fake-judge"

    def __init__(self):
        self.calls: list[tuple[str, object, tuple]] = []

    def _extra(self):
        return {**{rid: 1.0 for rid in fx.RECIPE_IDS}, **{f"c{i}": 1.0 for i in range(100, 120)}}

    def screen(self, profile, candidates, *, timeout_s):
        self.calls.append(("screen", profile, candidates))
        return {**{c.key: 1.0 for c in candidates}, **self._extra()}

    def judge(self, profile, candidates, aspects, *, timeout_s):
        self.calls.append(("judge", profile, candidates))
        full = {a: RerankAnswer(1.0, 1.0) for a in ASPECTS}
        return {**{c.key: full for c in candidates}, **{k: full for k in self._extra()}}


class Failing:
    model = "fake-judge"

    def screen(self, profile, candidates, *, timeout_s):
        raise RerankError("down")

    def judge(self, profile, candidates, aspects, *, timeout_s):
        raise RerankError("down")


class Broken(Failing):
    def judge(self, profile, candidates, aspects, *, timeout_s):
        raise RuntimeError("bug")


def make(compiled, judge):
    cfg = load_v2_config(CONFIG_DIR)
    assert cfg.ranking_mode == "jev"
    return RecommenderV2.from_v1(build_recommender(compiled, fx.RECIPES), cfg, judge=judge)


def ids(result):
    return {i.item.recipe_id for i in result.items}


REQUESTS = [
    V2Request("random", seed=1, limit=LIMIT),
    V2Request("pantry", limit=LIMIT),
    V2Request("dish", query="볶음", limit=LIMIT),
    V2Request("dish", query="새우볶음", limit=LIMIT),
    V2Request("dish", query="아무 문장이나 오늘 저녁", limit=LIMIT),  # 관련 후보 없음 → 걸러내기 보충
]
REQ_IDS = ["random", "pantry", "dish-볶음", "dish-새우볶음", "dish-걸러내기"]


@pytest.mark.parametrize("req", REQUESTS, ids=REQ_IDS)
def test_hostile_judge_never_adds_unsafe(compiled, req):
    hostile = Hostile()
    got = make(compiled, hostile).recommend(fx.user("shrimp"), req)
    assert not ids(got) & UNSAFE_FOR_SHRIMP
    assert got.ranking == "jev" and hostile.calls
    sent = {c.key for _, _, cands in hostile.calls for c in cands}
    assert all(k.startswith("c") and k not in fx.RECIPE_IDS for k in sent)


@pytest.mark.parametrize("req", REQUESTS, ids=REQ_IDS)
def test_judge_result_subset_of_rules_passing(compiled, req):
    """Jev 경로 결과는 규칙 경로가 '제외하지 않은' 레시피 안에 있다."""
    user = fx.user("shrimp", "egg")
    rules_all = make(compiled, None).recommend(user, V2Request("random", seed=1, limit=LIMIT, rerank=False))
    got = make(compiled, Hostile()).recommend(user, req)
    assert ids(got) <= ids(rules_all)


@pytest.mark.parametrize("judge_cls", [Failing, Broken])
@pytest.mark.parametrize("req", REQUESTS[:4], ids=REQ_IDS[:4])
def test_failure_falls_back_to_rules(compiled, req, judge_cls):
    user = fx.user("shrimp")
    base = make(compiled, None).recommend(user, req)
    got = make(compiled, judge_cls()).recommend(user, req)
    assert [i.item.recipe_id for i in got.items] == [i.item.recipe_id for i in base.items]
    assert got.ranking == "rules" and "jev_unavailable" in got.notes
    assert not ids(got) & UNSAFE_FOR_SHRIMP


def test_profile_sent_to_judge_has_no_hard_constraints(compiled):
    hostile = Hostile()
    profile = SimpleProfile(allergens=frozenset({"shrimp", "egg"}), never_eat=frozenset({"cucumber"}),
                            likes=frozenset({"potato"}), dislikes=frozenset({"mushroom"}), spicy_level=1,
                            skill_level=1)
    make(compiled, hostile).recommend(profile.to_user_context(pantry=fx.PANTRY),
                                      V2Request("dish", query="감자", limit=LIMIT))
    for _, p, _ in hostile.calls:
        assert p.liked_ingredients == ("감자",) and p.disliked_ingredients == ("버섯",)
        assert "오이" not in p.liked_ingredients + p.disliked_ingredients
        assert not {"allergen_groups", "never_eat", "user_id", "profile_id"} & set(vars(p))


def test_wire_payload_has_no_allergy_never_eat_ids_or_key(compiled):
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append((dict(request.headers), body))
        answers = {k: {"type": "score", "score": 3.0, "confidence": 0.9} for k in body["questions"]}
        return httpx.Response(200, json={"model": "jev-1.14.0", "answers": answers, "usage": {}})

    key = "apikey_TEST_SECRET"
    judge = JevJudge(JevClient(key, model="jev-1.14.0", transport=httpx.MockTransport(handler)))
    profile = SimpleProfile(allergens=frozenset({"shrimp", "egg"}), never_eat=frozenset({"cucumber"}),
                            likes=frozenset({"potato"}))
    user = profile.to_user_context(pantry=fx.PANTRY)
    v2 = make(compiled, judge)
    # 사용자가 직접 쓴 요청 문장("새우볶음")은 그대로 보내므로 이 검사에서는 뺀다
    for req in [r for r in REQUESTS if r.query != "새우볶음"]:
        result = v2.recommend(user, req)
        assert result.ranking == "jev"
    assert sent
    for headers, body in sent:
        assert headers["authorization"] == f"Bearer {key}"
        text = json.dumps(body, ensure_ascii=False)
        assert key not in text and "감자" in text
        for token in ("shrimp", "egg", "allerg", "알레르기", "오이", "새우", "계란", *fx.RECIPE_IDS):
            assert token not in text, f"Jev 요청 본문에 {token!r}이(가) 있습니다"
