"""Jev 어댑터(integrations/jev): HTTP 형식, 재시도, 오류 처리, 인증키 비노출. 네트워크 없이 가짜 전송으로 시험한다."""

from __future__ import annotations

import json

import httpx
import pytest

from engine.v2.ports import RerankCandidate, RerankError, RerankQuery
from integrations.jev.client import JevClient, JevError
from integrations.jev.reranker import LEVELS, JevReranker, build_questions, build_state, parse_answers

KEY = "apikey_TEST_SECRET_123"


def client(handler) -> JevClient:
    return JevClient(KEY, model="jev-1.14.0", transport=httpx.MockTransport(handler))


def ok(answers):
    return httpx.Response(200, json={"model": "jev-1.14.0", "answers": answers, "usage": {}})


QUERY = RerankQuery(
    kind="dish", query="얼큰한 국물",
    candidates=(RerankCandidate("c0", "김치찌개", "한식", {"spicy": 3, "salty": 3, "sweet": 0, "sour": 1, "umami": 3,
                                                       "savory": 1}, ("돼지고기", "배추김치")),
                RerankCandidate("c1", "크림파스타", "미분류", None, ("파스타",))),
    skill_level=1, taste_preferences={"spicy": {"preferred": 4}},
)


def test_request_shape_and_model():
    seen = []

    def handler(req):
        seen.append(req)
        return ok({})

    client(handler).system_one({"a": 1}, {"q": {"type": "noul", "instructions": "x"}}, timeout_s=2)
    req = seen[0]
    assert req.method == "POST" and req.url.path == "/v1/systemone"
    assert req.headers["authorization"] == f"Bearer {KEY}"
    body = json.loads(req.content)
    assert body["model"] == "jev-1.14.0" and body["state"] == {"a": 1} and "q" in body["questions"]


def test_retries_once_on_429():
    calls = []

    def handler(req):
        calls.append(1)
        return httpx.Response(429) if len(calls) == 1 else ok({"q": {"type": "noul", "noul": 0.5}})

    assert client(handler).system_one("s", {"q": {}}, timeout_s=5) == {"q": {"type": "noul", "noul": 0.5}}
    assert len(calls) == 2


@pytest.mark.parametrize("status", [400, 401, 422, 500])
def test_http_error_raises_without_key(status):
    with pytest.raises(JevError) as exc:
        client(lambda req: httpx.Response(status, text="bad request")).system_one("s", {}, timeout_s=2)
    assert str(status) in str(exc.value) and KEY not in str(exc.value)


def test_timeout_raises():
    def handler(req):
        raise httpx.ReadTimeout("slow", request=req)

    with pytest.raises(JevError, match="시간 초과"):
        client(handler).system_one("s", {}, timeout_s=1)


def test_malformed_response_raises():
    with pytest.raises(JevError):
        client(lambda req: httpx.Response(200, json={"nope": 1})).system_one("s", {}, timeout_s=1)


def test_repr_hides_key():
    assert KEY not in repr(client(lambda req: ok({})))


def test_state_and_questions():
    state = build_state(QUERY)
    assert state == {"user_request": "얼큰한 국물", "cooking_skill": "beginner cook",
                     "taste_preferences": {"spiciness": {"preferred_level_0_to_5": 4}}}
    qs = build_questions(QUERY)
    assert set(qs) == {"c0", "c1"}
    assert qs["c0"]["type"] == "score" and qs["c0"]["criteria"] == LEVELS
    assert qs["c0"]["instructions"]["recipe"]["cuisine"] == "한식"
    assert "cuisine" not in qs["c1"]["instructions"]["recipe"]  # 미분류는 보내지 않는다
    assert "taste_0_to_5" not in qs["c1"]["instructions"]["recipe"]  # 맛 모름


def test_parse_answers_normalizes_and_filters():
    raw = {"c0": {"type": "score", "score": 3.0, "confidence": 0.8},
           "c1": {"type": "choice", "choice": "x", "confidence": 1.0},  # 유형이 다름
           "c9": {"type": "score", "score": 4.0, "confidence": 1.0},  # 보내지 않은 key
           "c2": {"type": "score", "score": "4", "confidence": 1.0}}  # 숫자가 아님
    out = parse_answers(raw, {"c0", "c1", "c2"})
    assert set(out) == {"c0"}
    assert out["c0"].score == pytest.approx(0.75) and out["c0"].confidence == 0.8


def test_reranker_maps_error():
    rr = JevReranker(client(lambda req: httpx.Response(529)))
    with pytest.raises(RerankError):
        rr.rerank(QUERY, timeout_s=0.5)


def test_reranker_end_to_end():
    def handler(req):
        qs = json.loads(req.content)["questions"]
        return ok({k: {"type": "score", "score": 4.0 if k == "c0" else 0.0, "confidence": 0.9} for k in qs})

    out = JevReranker(client(handler)).rerank(QUERY, timeout_s=2)
    assert out["c0"].score == 1.0 and out["c1"].score == 0.0
