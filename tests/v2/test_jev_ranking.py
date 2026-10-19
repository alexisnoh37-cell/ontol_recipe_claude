"""Jev가 순위를 정하는 경로(decisions D10, docs/plan.md 부록 G-12)의 동작. 안전성은 tests/allergy/test_v2_judge_safety.py."""

from __future__ import annotations

import json
from dataclasses import replace

import httpx
import pytest

from engine.model import Preference, TastePreference, UserContext
from engine.v2.config import load_v2_config
from engine.v2.model import V2Request
from engine.v2.ports import RerankAnswer
from engine.v2.recommend import RecommenderV2
from integrations.jev.client import JevClient
from integrations.jev.judge import JevJudge, build_judge_questions, build_state, parse_judge
from tests.allergy import fixtures as fx
from tests.support.engine_fixtures import CONFIG_DIR, build_recommender

LIMIT = 50


class Table:
    """후보 제목 → 항목별 점수. screen은 제목 → 점수."""

    model = "table-judge"

    def __init__(self, judge_scores=None, screen_scores=None, default=0.5):
        self.judge_scores = judge_scores or {}
        self.screen_scores = screen_scores or {}
        self.default = default
        self.judge_calls, self.screen_calls = [], []

    def screen(self, profile, candidates, *, timeout_s):
        self.screen_calls.append((profile, candidates))
        return {c.key: self.screen_scores.get(c.title, 0.0) for c in candidates}

    def judge(self, profile, candidates, aspects, *, timeout_s):
        self.judge_calls.append((profile, candidates, aspects))
        return {c.key: {a: RerankAnswer(self.judge_scores.get(c.title, self.default), 0.9) for a in aspects}
                for c in candidates}


def make(compiled, judge, **overrides):
    cfg = replace(load_v2_config(CONFIG_DIR), **overrides)
    return RecommenderV2.from_v1(build_recommender(compiled, fx.RECIPES), cfg, judge=judge)


def titles(result):
    return [i.item.title for i in result.items]


def test_order_follows_jev_total(compiled):
    judge = Table({"고추장 감자조림": 1.0, "감자구이": 0.1})
    r = make(compiled, judge).recommend(UserContext(), V2Request("dish", query="감자", limit=LIMIT))
    assert r.ranking == "jev" and r.rerank_used and r.rerank_model == "table-judge"
    assert titles(r)[0] == "고추장 감자조림" and titles(r)[-1] == "감자구이"
    top = r.items[0].item
    assert top.score == 1.0 and top.breakdown["J"] == 1.0 and top.breakdown["J_conf"] == 0.9
    assert {"J_request", "J_skill"} <= set(top.breakdown)
    assert not {"I", "K", "T", "P", "D", "M", "S"} & set(top.breakdown)  # 규칙 점수는 쓰지 않는다


def test_aspects_follow_available_info(compiled):
    judge = Table()
    v2 = make(compiled, judge)
    v2.recommend(UserContext(), V2Request("dish", query="감자"))
    assert judge.judge_calls[-1][2] == ("request", "skill")
    user = UserContext(preferences=(Preference("ingredient", "potato", 1), Preference("cuisine", "한식", 1)),
                       tastes=(TastePreference("spicy", preferred_level=2),), pantry=frozenset({"potato"}))
    v2.recommend(user, V2Request("pantry"))
    assert judge.judge_calls[-1][2] == ("taste", "ingredients", "cuisine", "skill", "pantry")


def test_pantry_groups_kept_and_order_within(compiled):
    judge = Table({"감자구이": 0.1, "고추장 감자조림": 0.9, "버터감자": 1.0})
    r = make(compiled, judge).recommend(UserContext(pantry=frozenset({"potato"})), V2Request("pantry", limit=LIMIT))
    groups = [i.group for i in r.items]
    assert groups == sorted(groups, key=lambda g: g != "ready")
    ready = [i.item.title for i in r.items if i.group == "ready"]
    assert ready[0] == "고추장 감자조림" and ready[-1] == "감자구이"
    near = [i for i in r.items if i.group == "near"]
    assert near[0].item.title == "버터감자"  # Jev 점수가 가장 높아도 near 묶음 안에 둔다
    _, cands, _ = judge.judge_calls[-1]
    bt = next(c for c in cands if c.title == "버터감자")
    assert bt.missing_ingredients == ("버터",)
    assert judge.judge_calls[-1][0].ingredients_on_hand == ("감자",)


def test_dish_screen_used_only_when_pool_small(compiled):
    judge = Table(screen_scores={"버섯볶음": 1.0, "파전": 0.9})
    r = make(compiled, judge).recommend(UserContext(), V2Request("dish", query="오늘 저녁 뭐 먹지", limit=LIMIT))
    assert judge.screen_calls and "jev_screened" in r.notes
    assert set(titles(r)[:2]) == {"버섯볶음", "파전"}
    judge2 = Table()
    make(compiled, judge2, ranking_min_pool=1).recommend(UserContext(), V2Request("dish", query="감자"))
    assert not judge2.screen_calls


def test_screen_respects_pool_size(compiled):
    judge = Table(screen_scores={r.title: 1.0 for r in fx.RECIPES})
    r = make(compiled, judge, ranking_pool_size=3).recommend(UserContext(), V2Request("dish", query="오늘 저녁",
                                                                                       limit=LIMIT))
    assert len(judge.judge_calls[-1][1]) == 3 and len(r.items) == 3


def test_random_pool_and_seed(compiled):
    judge = Table()
    v2 = make(compiled, judge, ranking_pool_size=5)
    a = v2.recommend(UserContext(), V2Request("random", seed=7, limit=3))
    b = v2.recommend(UserContext(), V2Request("random", seed=7, limit=3))
    assert titles(a) == titles(b) and len(a.items) == 3 and a.seed == 7
    assert len(judge.judge_calls[0][1]) == 5  # 무작위 5개 중 Jev가 3개를 고른다


def test_rerank_false_uses_rules(compiled):
    judge = Table()
    r = make(compiled, judge).recommend(UserContext(), V2Request("dish", query="감자", rerank=False))
    assert not judge.judge_calls and r.ranking == "rules" and "I" in r.items[0].item.breakdown


def test_rules_mode_config_ignores_judge(compiled):
    judge = Table()
    r = make(compiled, judge, ranking_mode="rules").recommend(UserContext(), V2Request("dish", query="감자"))
    assert not judge.judge_calls and r.ranking == "rules"


def test_unusable_answers_fall_back(compiled):
    class Empty(Table):
        def judge(self, profile, candidates, aspects, *, timeout_s):
            return {c.key: {} for c in candidates}

    r = make(compiled, Empty()).recommend(UserContext(), V2Request("dish", query="감자"))
    assert r.ranking == "rules" and "jev_unavailable" in r.notes


def test_missing_answer_goes_last(compiled):
    class Partial(Table):
        def judge(self, profile, candidates, aspects, *, timeout_s):
            out = super().judge(profile, candidates, aspects, timeout_s=timeout_s)
            out.pop(candidates[0].key)
            return out

    r = make(compiled, Partial(default=0.6)).recommend(UserContext(), V2Request("dish", query="감자", limit=LIMIT))
    assert r.items[-1].item.score == 0.0 and r.items[-1].item.breakdown["J_conf"] == 0.0


# --- 어댑터 ------------------------------------------------------------------------------------------------


def test_adapter_question_keys_and_parse():
    from engine.v2.ports import JudgeCandidate, JudgeProfile

    cands = (JudgeCandidate("c0", "감자조림", "한식", 0, 1, ("감자",)),
             JudgeCandidate("c1", "감자전", None, None, None, ("감자",), ("부침가루",)))
    qs = build_judge_questions(cands, ("request", "skill"))
    assert set(qs) == {"c0__request", "c0__skill", "c1__request", "c1__skill"}
    assert "cuisine" not in qs["c1__skill"]["instructions"]["recipe"]
    assert qs["c1__skill"]["instructions"]["recipe"]["missing_ingredients"] == ["부침가루"]
    raw = {"c0__request": {"type": "score", "score": 4.0, "confidence": 0.8},
           "c0__skill": {"type": "choice", "choice": "x"}, "c9__request": {"type": "score", "score": 4, "confidence": 1}}
    out = parse_judge(raw, cands, ("request", "skill"))
    assert set(out) == {"c0"} and out["c0"]["request"].score == 1.0 and "skill" not in out["c0"]
    state = build_state(JudgeProfile(skill_level=1, request="감자", liked_ingredients=("감자",)))
    assert state == {"user_request": "감자", "cooking_skill": "beginner cook", "liked_ingredients": ["감자"]}


def test_adapter_screen_chunks_in_parallel():
    from engine.v2.ports import JudgeCandidate, JudgeProfile

    calls = []

    def handler(request):
        qs = json.loads(request.content)["questions"]
        calls.append(len(qs))
        return httpx.Response(200, json={"answers": {k: {"type": "score", "score": 2.0, "confidence": 0.5}
                                                    for k in qs}, "usage": {}})

    judge = JevJudge(JevClient("k", model="jev-1.14.0", transport=httpx.MockTransport(handler)), screen_chunk=4)
    cands = tuple(JudgeCandidate(f"c{i}", f"요리{i}", None, None, None, ()) for i in range(10))
    out = judge.screen(JudgeProfile(), cands, timeout_s=5)
    assert sorted(calls) == [2, 4, 4] and len(out) == 10 and out["c3"] == pytest.approx(0.5)


def test_spicy_max_not_asked_as_taste(compiled):
    """매운맛 선호 5(최대)는 Jev 취향 질문에서 뺀다(5는 '한도 없음'으로만 본다, D10 보완)."""
    judge = Table()
    v2 = make(compiled, judge)
    v2.recommend(UserContext(tastes=(TastePreference("spicy", preferred_level=5),)), V2Request("dish", query="감자"))
    profile, _, aspects = judge.judge_calls[-1]
    assert "taste" not in aspects and profile.spicy_preference is None
    v2.recommend(UserContext(tastes=(TastePreference("spicy", preferred_level=4),)), V2Request("dish", query="감자"))
    profile, _, aspects = judge.judge_calls[-1]
    assert "taste" in aspects and profile.spicy_preference == 4
