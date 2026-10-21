"""v2 추천 재생 표시 계층(api/viz_v2.py, docs/plan.md 부록 H-3). 실제 knowledge·레시피, Jev는 가짜."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api.v2 import create_v2_app
from engine.v2.ports import RerankAnswer
from storage.engine_source import load_files
from storage.users import InMemoryUserStore


class Judge:
    model = "fake-judge"

    def screen(self, profile, candidates, *, timeout_s):
        return {c.key: 0.4 for c in candidates}

    def judge(self, profile, candidates, aspects, *, timeout_s):
        return {c.key: {a: RerankAnswer((i % 5) / 4, 0.7) for a in aspects} for i, c in enumerate(candidates)}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    data = load_files()
    app = create_v2_app(lambda: data, InMemoryUserStore(), exclusion_log=tmp_path_factory.mktemp("log") / "x.jsonl",
                        judge_factory=lambda cfg: Judge())
    return TestClient(app)


@pytest.fixture(scope="module")
def graph(client):
    g = client.get("/graph", params={"recipes": "all"}).json()
    return {n["id"] for n in g["nodes"]}, {lk["id"] for lk in g["links"]}


SHRIMP = {"allergens": ["crustacean_bundle"], "spicy_level": 3, "skill_level": 1}
CASES = [
    {"persona_id": "t1_shrimp_allergy_spicy", "mode": "dish", "query": "얼큰한 국물요리"},
    {"persona_id": "t2_no_spicy_beginner", "mode": "random", "seed": 3},
    {"persona_id": "t3_milk_egg_allergy_western", "mode": "pantry", "pantry": ["egg", "tofu", "kimchi", "pork"]},
    {"profile": SHRIMP, "mode": "pantry", "pantry": ["egg", "tofu", "kimchi", "pork"], "rerank": False},
    {"profile": SHRIMP, "mode": "dish", "query": "김치찌개"},
]


def node_ids(trace):
    """trace가 가리키는 모든 노드 id(그래프에 있어야 화면이 그릴 수 있다)."""
    out = set(trace["user"]["allergen_groups"]) | set(trace["user"]["hard_dislikes"])
    out |= set(trace["pantry"]["input"]) | {o["node"] for o in trace["pantry"]["owned"]}
    out |= {c["recipe"] for c in trace["checked"]} | {s["recipe"] for s in trace["similarity"]}
    out |= {r for ids in trace["groups"].values() for r in ids} | set(trace["pool"]) | set(trace["screened"])
    out |= {r["recipe"] for r in trace["ranked"]} | set(trace["excluded"])
    for e in trace["exclusions"]:
        out |= {e["recipe"]} | {x for x in (e["ingredient"], e["target_node"], e["source_group"]) if x}
        out |= set(e["via"])
    if trace["query"]:
        out |= set(trace["query"]["ingredients"]) | set(trace["query"]["anchors"])
    for j in (trace["jev"], trace["failed_jev"]):
        if j:
            out |= {c["recipe"] for c in j["candidates"]} | set(j["answers"])
    return out


@pytest.mark.parametrize("body", CASES)
def test_trace_points_into_graph_and_matches_plain(client, graph, body):
    nodes, links = graph
    plain = client.post("/v2/recommend", json=body)
    traced = client.post("/v2/recommend", json={**body, "trace": True})
    assert plain.status_code == traced.status_code == 200, traced.text
    p, t = plain.json(), traced.json()
    assert "trace" not in p and set(t) == set(p) | {"trace"}
    if body["mode"] != "random" or "seed" in body:
        assert [i["recipe_id"] for i in p["items"]] == [i["recipe_id"] for i in t["items"]]
    tr = t["trace"]
    assert node_ids(tr) <= nodes
    assert {lk for e in tr["exclusions"] for lk in e["path_links"]} <= links
    assert set(tr["pantry"]["owned_links"]) <= links
    shown = [r["recipe"] for r in tr["ranked"] if r["shown"]]
    assert sorted(shown) == sorted(f"rcp:{i['recipe_id']}" for i in t["items"])
    assert tr["ranking"] == t["ranking"]


def test_dish_query_rules_and_jev_view(client):
    tr = client.post("/v2/recommend", json={**CASES[0], "trace": True}).json()["trace"]
    q = tr["query"]
    matched = {m for r in q["rules"] for m in r["matched"]}
    assert {"얼큰", "국물"} <= matched  # 키워드 규칙: 얼큰 → 매운맛, 국물 → 제목 낱말
    assert any(r["taste"].get("spicy", {}).get("min") == 3 for r in q["rules"])
    assert "keyword" in q["active"] and tr["similarity"] and all(s["S"] > 0 for s in tr["similarity"])
    jev = tr["jev"]
    assert tr["ranking"] == "jev" and jev and not jev["failed"] and "request" in jev["aspects"]
    assert jev["state"]["user_request"] == "얼큰한 국물요리"
    assert [c["recipe"] for c in jev["candidates"]] == tr["pool"]
    assert set(jev["answers"]) == set(tr["pool"])
    sent = json.dumps(jev, ensure_ascii=False)
    for word in ("새우", "갑각류", "crustacean", "allerg"):
        assert word not in sent
    assert tr["labels"]["aspect_ko"]["request"]


def test_allergy_path_reaches_group(client):
    body = {"profile": SHRIMP, "mode": "dish", "query": "김치찌개", "trace": True}
    tr = client.post("/v2/recommend", json=body).json()["trace"]
    rows = [e for e in tr["exclusions"] if e["reason"] == "allergen"]
    assert rows, "김치찌개류는 새우젓(김치) 때문에 갑각류 알레르기에서 빠져야 한다"
    for e in rows:
        assert e["target_node"] == "ag:crustacean_bundle" and e["path_links"]
        assert e["path_links"][0] == f"mem:crustacean_bundle>{e['source_group'][3:]}"
        assert e["path_links"][-1].startswith(f"use:{e['recipe'][4:]}#")


def test_rules_ranking_view(client):
    tr = client.post("/v2/recommend", json={**CASES[3], "trace": True}).json()["trace"]
    assert tr["ranking"] == "rules" and tr["jev"] is None and not tr["jev_failed"]
    assert tr["groups"]["ready"] and {"I", "K"} <= set(tr["ranked"][0]["breakdown"])
    assert {o["because"] for o in tr["pantry"]["owned"]} >= {"pantry", "staple"}
