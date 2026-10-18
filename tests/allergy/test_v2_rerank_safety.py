"""추천 v2 Jev 재정렬 안전성(docs/plan.md 부록 G-4·G-8, decisions D7). 신규 — 사람 승인 대상.

재정렬은 규칙 필터를 통과한 목록 안에서 순서만 바꾼다. Jev가 어떤 답을 주든(목록 밖 key, 높은 점수, 오류)
제외된 레시피가 되살아나거나 목록 구성이 바뀌지 않는다. Jev에 알레르기 정보·사용자 id·레시피 id를 보내지 않는다.
실제 Jev 어댑터(integrations/jev)를 가짜 HTTP 전송으로 시험한다(네트워크 없음).
"""

from __future__ import annotations

import json

import httpx
import pytest

from engine.v2.config import load_v2_config
from engine.v2.model import V2Request
from engine.v2.ports import RerankAnswer, RerankError
from engine.v2.recommend import RecommenderV2
from integrations.jev.client import JevClient
from integrations.jev.reranker import JevReranker
from tests.allergy import fixtures as fx
from tests.support.engine_fixtures import CONFIG_DIR, build_recommender

LIMIT = len(fx.RECIPES) + 10
UNSAFE_FOR_SHRIMP = {"shrimp_stirfry", "cabbage_saeujeot_soup", "kimchi_fried_rice", "kimchi_sauce_potato",
                     "jeotgal_cabbage_salad"}


class Hostile:
    """보낸 후보 key에 최고점을 주고, 목록에 없는 key(레시피 id 포함)에도 답을 붙이는 가짜 재정렬기."""

    model = "fake"

    def __init__(self):
        self.queries = []

    def rerank(self, query, *, timeout_s):
        self.queries.append(query)
        out = {c.key: RerankAnswer(1.0, 1.0) for c in query.candidates}
        out.update({rid: RerankAnswer(1.0, 1.0) for rid in fx.RECIPE_IDS})
        out.update({f"c{i}": RerankAnswer(1.0, 1.0) for i in range(100, 120)})
        return out


class Failing:
    model = "fake"

    def rerank(self, query, *, timeout_s):
        raise RerankError("down")


class Broken:
    model = "fake"

    def rerank(self, query, *, timeout_s):
        raise RuntimeError("bug")


def make(compiled, reranker):
    return RecommenderV2.from_v1(build_recommender(compiled, fx.RECIPES), load_v2_config(CONFIG_DIR), reranker)


def ids(result):
    return [i.item.recipe_id for i in result.items]


REQUESTS = [V2Request("pantry", limit=LIMIT, rerank=True), V2Request("dish", query="볶음", limit=LIMIT, rerank=True),
            V2Request("dish", query="새우볶음", limit=LIMIT, rerank=True)]


@pytest.mark.parametrize("req", REQUESTS, ids=["pantry", "dish-볶음", "dish-새우볶음"])
@pytest.mark.parametrize("reranker_cls", [Hostile, Failing, Broken])
def test_rerank_never_changes_membership(compiled, req, reranker_cls):
    user = fx.user("shrimp")
    base = make(compiled, None).recommend(user, req)
    got = make(compiled, reranker_cls()).recommend(user, req)
    assert set(ids(got)) == set(ids(base))
    assert not set(ids(got)) & UNSAFE_FOR_SHRIMP
    if reranker_cls is not Hostile:
        assert ids(got) == ids(base) and not got.rerank_used and "rerank_unavailable" in got.notes


def test_rerank_keeps_pantry_groups(compiled):
    got = make(compiled, Hostile()).recommend(fx.NO_ALLERGY, V2Request("pantry", limit=LIMIT, rerank=True))
    groups = [i.group for i in got.items]
    assert groups == sorted(groups, key=lambda g: g != "ready"), "재정렬 후에도 ready 묶음이 near보다 앞서야 한다"


def test_rerank_query_has_no_allergy_or_ids(compiled):
    hostile = Hostile()
    user = fx.user("shrimp", "egg", preferences=(fx.hard_dislike("cucumber"),))
    make(compiled, hostile).recommend(user, V2Request("dish", query="감자", limit=LIMIT, rerank=True))
    assert hostile.queries
    for q in hostile.queries:
        fields = set(vars(q))
        assert not {"allergen_groups", "preferences", "pantry", "user_id", "profile_id"} & fields
        for c in q.candidates:
            assert c.key.startswith("c") and c.key not in fx.RECIPE_IDS


def test_jev_wire_payload_has_no_allergy_ids_or_key(compiled):
    """실제 어댑터가 보내는 HTTP 본문: 알레르기 그룹·레시피 id 없음, 인증키는 헤더에만."""
    sent = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append((dict(request.headers), json.loads(request.content)))
        body = json.loads(request.content)
        answers = {k: {"type": "score", "score": 4.0, "confidence": 0.9} for k in body["questions"]}
        return httpx.Response(200, json={"model": "jev-1.14.0", "answers": answers, "usage": {}})

    key = "apikey_TEST_SECRET"
    client = JevClient(key, model="jev-1.14.0", transport=httpx.MockTransport(handler))
    user = fx.user("shrimp", "egg")
    result = make(compiled, JevReranker(client)).recommend(user, V2Request("dish", query="감자", limit=LIMIT, rerank=True))
    assert result.rerank_used and sent
    for headers, body in sent:
        assert headers["authorization"] == f"Bearer {key}"
        text = json.dumps(body, ensure_ascii=False)
        assert key not in text
        for token in ("shrimp", "egg", "allerg", "알레르기", *fx.RECIPE_IDS):
            assert token not in text, f"Jev 요청 본문에 {token!r}이(가) 있습니다"
