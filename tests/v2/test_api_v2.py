"""추천 v2 API(api/v2.py). 실제 knowledge/·레시피(load_files), 사용자는 메모리 저장소, Jev는 가짜."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api.v2 import create_v2_app
from engine.v2.ports import RerankAnswer
from storage.engine_source import load_files
from storage.personas import load_personas
from storage.users import InMemoryUserStore


class Fake:
    model = "fake-jev"

    def __init__(self):
        self.calls = 0

    def rerank(self, query, *, timeout_s):
        self.calls += 1
        return {c.key: RerankAnswer(0.5, 0.9) for c in query.candidates}


@pytest.fixture(scope="module")
def data():
    return load_files()


@pytest.fixture()
def log_path(tmp_path):
    return tmp_path / "exclusions.jsonl"


def make_client(data, log_path, reranker=None) -> TestClient:
    return TestClient(create_v2_app(lambda: data, InMemoryUserStore(), exclusion_log=log_path,
                                    reranker_factory=lambda cfg: reranker))


@pytest.fixture()
def client(data, log_path):
    return make_client(data, log_path)


def profile(client, **fields) -> int:
    pid = client.post("/profiles", json={"display_name": "v2", "skill_level": 1}).json()["id"]
    if fields:
        assert client.patch(f"/profiles/{pid}", json=fields).status_code == 200
    return pid


def test_info_without_key(client):
    body = client.get("/v2/info").json()
    assert body["rerank_available"] is False and body["rerank_model"] == "jev-1.14.0"


def test_random_by_persona(client):
    pid = load_personas()[0].id
    body = client.post("/v2/recommend", json={"persona_id": pid, "mode": "random", "seed": 5}).json()
    assert body["mode"] == "random" and body["seed"] == 5 and body["items"]
    assert {"I", "K", "T", "P", "D", "M"} <= {b["key"] for b in body["items"][0]["breakdown"]}
    again = client.post("/v2/recommend", json={"persona_id": pid, "mode": "random", "seed": 5}).json()
    assert [i["recipe_id"] for i in again["items"]] == [i["recipe_id"] for i in body["items"]]


def test_pantry_groups_and_labels(client):
    pid = profile(client)
    body = client.post("/v2/recommend", json={"profile_id": pid, "mode": "pantry",
                                              "pantry": ["egg", "green_onion", "rice"], "limit": 30}).json()
    groups = [i["group"] for i in body["items"]]
    assert groups and set(groups) <= {"ready", "near"}
    assert groups == sorted(groups, key=lambda g: g != "ready")
    ready = [i for i in body["items"] if i["group"] == "ready"]
    assert ready and ready[0]["group_label"] and ready[0]["required_missing_count"] == 0
    assert body["rerank_used"] is False and body["notes"][0]["code"] == "rerank_off"


def test_dish_with_allergy_logs_exclusions(client, log_path):
    pid = profile(client)
    client.put(f"/profiles/{pid}/preferences",
               json={"preferences": [{"target_type": "allergen_group", "target_id": "shrimp", "polarity": -1,
                                      "is_hard": True}]})
    body = client.post("/v2/recommend", json={"profile_id": pid, "mode": "dish", "query": "새우볶음밥"}).json()
    excluded = {json.loads(line)["recipe_id"] for line in log_path.read_text(encoding="utf-8").splitlines()}
    assert excluded and not excluded & {i["recipe_id"] for i in body["items"]}
    assert all(json.loads(line)["engine"] == "v2" for line in log_path.read_text(encoding="utf-8").splitlines())
    assert body["excluded_total"] == len(excluded)
    assert any(s["reason"] == "allergen" for s in body["exclusion_summary"])


def test_dish_requires_query(client):
    pid = profile(client)
    assert client.post("/v2/recommend", json={"profile_id": pid, "mode": "dish"}).status_code == 422


def test_unknown_pantry_id(client):
    pid = profile(client)
    r = client.post("/v2/recommend", json={"profile_id": pid, "mode": "pantry", "pantry": ["no_such"]})
    assert r.status_code == 400


def test_rerank_used_with_reranker(data, log_path):
    fake = Fake()
    c = make_client(data, log_path, fake)
    pid = profile(c)
    body = c.post("/v2/recommend", json={"profile_id": pid, "mode": "dish", "query": "김치찌개"}).json()
    assert fake.calls == 1 and body["rerank_used"] and body["rerank_model"] == "fake-jev"
    keys = {b["key"]: b["label"] for b in body["items"][0]["breakdown"]}
    assert keys["S"] == "찾는 요리와 비슷함" and keys["J"] == "Jev 적합도"
    off = c.post("/v2/recommend", json={"profile_id": pid, "mode": "dish", "query": "김치찌개", "rerank": False}).json()
    assert fake.calls == 1 and not off["rerank_used"]


def test_v1_routes_unchanged(client):
    pid = profile(client, pantry=["egg", "rice"])
    r = client.post("/recommend", json={"profile_id": pid})
    assert r.status_code == 200 and "items" in r.json()


def test_root_redirects_to_docs(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/docs"


def test_v2_personas_listed(client):
    body = client.get("/v2/personas").json()
    assert len(body) == 5 and all(p["checks"] and p["try_dish"] for p in body)
    assert body[0]["allergens"][0]["name"]


def test_v2_persona_recommend(client):
    pid = client.get("/v2/personas").json()[0]["id"]
    body = client.post("/v2/recommend", json={"persona_id": pid, "mode": "dish", "query": "김치찌개"}).json()
    assert "dish_excluded" in [n["code"] for n in body["notes"]]


def test_inline_profile(client):
    profile = {"allergens": ["egg"], "never_eat": ["cucumber"], "likes": ["potato"], "dislikes": ["onion"],
               "spicy_level": 2, "cuisine_likes": ["한식"], "skill_level": 1}
    body = client.post("/v2/recommend", json={"profile": profile, "mode": "pantry", "pantry": ["potato", "rice"]}).json()
    assert body["items"] and body["profile_id"] is None


@pytest.mark.parametrize("profile,status", [
    ({"likes": ["no_such"]}, 400),
    ({"cuisine_likes": ["태국식"]}, 400),
    ({"likes": ["egg"], "dislikes": ["egg"]}, 400),
    ({"allergens": ["no_group"]}, 400),
    ({"spicy_level": 9}, 422),
])
def test_inline_profile_rejects_bad_input(client, profile, status):
    r = client.post("/v2/recommend", json={"profile": profile, "mode": "random"})
    assert r.status_code == status, r.text


def test_exactly_one_subject(client):
    r = client.post("/v2/recommend", json={"profile": {}, "persona_id": "x", "mode": "random"})
    assert r.status_code == 422


def test_jev_ranking_via_api(data, log_path):
    from engine.v2.ports import RerankAnswer

    class Judge:
        model = "fake-judge"

        def screen(self, profile, candidates, *, timeout_s):
            return {c.key: 0.5 for c in candidates}

        def judge(self, profile, candidates, aspects, *, timeout_s):
            return {c.key: {a: RerankAnswer(0.7, 0.8) for a in aspects} for c in candidates}

    c = TestClient(create_v2_app(lambda: data, InMemoryUserStore(), exclusion_log=log_path,
                                 judge_factory=lambda cfg: Judge()))
    assert c.get("/v2/info").json()["ranking"] == "jev"
    pid = c.get("/v2/personas").json()[0]["id"]
    body = c.post("/v2/recommend", json={"persona_id": pid, "mode": "dish", "query": "얼큰한 국물"}).json()
    assert body["ranking"] == "jev" and body["rerank_model"] == "fake-judge" and body["items"]
    labels = {b["key"]: b["label"] for b in body["items"][0]["breakdown"]}
    assert labels["J_request"] == "요청과 맞음(Jev)" and "I" not in labels
    off = c.post("/v2/recommend", json={"persona_id": pid, "mode": "dish", "query": "얼큰한 국물",
                                        "rerank": False}).json()
    assert off["ranking"] == "rules"
