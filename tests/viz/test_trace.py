"""POST /recommend trace 옵션과 페르소나 (docs/plan.md 부록 D-3·D-4).

trace는 엔진이 이미 계산한 값을 모을 뿐이다. trace=true의 추천·제외 결과가 일반 /recommend와 같고,
후보 = 통과 ∪ 제외, 최종 순위가 items 순서와 같고, 화면이 그릴 path_links가 /graph에 모두 있는지 확인한다.
"""

from __future__ import annotations

import json

import pytest

from api.main import user_context
from engine.model import RecommendRequest
from storage.personas import load_personas

PERSONAS = {p.id: p for p in load_personas()}

# 제외 사유를 골고루 만드는 저장 프로필(묶음 알레르기, 매운맛 한도, 조리기구, 절대 불선호, 시간 절대)
PROFILES = {
    "seafood_allergy": {
        "fields": {"pantry": ["kimchi", "pork_belly", "egg", "potato", "rice", "green_onion"], "equipment": ["냄비"]},
        "prefs": [{"target_type": "allergen_group", "target_id": "seafood_bundle"},
                  {"target_type": "allergen_group", "target_id": "wheat"}],
        "req": {},
    },
    "spicy_and_time": {
        "fields": {"pantry": ["kimchi", "pork_belly", "potato", "squid", "onion", "milk"],
                   "tastes": [{"dimension": "spicy", "max_level": 1}]},
        "prefs": [],
        "req": {"max_time_min": 20, "time_is_hard": True},
    },
    "hard_dislike": {
        "fields": {"pantry": ["kimchi", "pork_belly", "tofu", "egg", "rice"]},
        "prefs": [{"target_type": "ingredient", "target_id": "pork", "is_hard": True},
                  {"target_type": "cuisine", "target_id": "일식", "is_hard": True}],
        "req": {},
    },
}

SUBJECTS = [("persona", p) for p in PERSONAS] + [("profile", name) for name in PROFILES]


def make_subject(client, kind: str, key: str) -> dict:
    if kind == "persona":
        return {"persona_id": key}
    spec = PROFILES[key]
    pid = client.post("/profiles", json={"display_name": key, "skill_level": 2}).json()["id"]
    assert client.patch(f"/profiles/{pid}", json=spec["fields"]).status_code == 200
    if spec["prefs"]:
        assert client.put(f"/profiles/{pid}/preferences", json={"preferences": spec["prefs"]}).status_code == 200
    return {"profile_id": pid, **spec["req"]}


def post(client, body: dict) -> dict:
    r = client.post("/recommend", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def graph_index(client) -> tuple[set[str], dict[str, dict]]:
    g = client.get("/graph", params={"recipes": "all"}).json()
    return {lk["id"] for lk in g["links"]}, {n["id"]: n for n in g["nodes"]}


@pytest.mark.parametrize(("kind", "key"), SUBJECTS)
def test_trace_matches_plain_recommend(client, kind, key):
    body = make_subject(client, kind, key)
    plain = post(client, body)
    traced = post(client, {**body, "trace": True})
    assert "trace" not in plain
    for k in ("items", "exclusion_summary", "excluded_total", "disclaimer", "profile_id"):
        assert traced[k] == plain[k], k
    t = traced["trace"]
    excluded = {e["recipe"] for e in t["exclusions"]}
    assert set(t["excluded"]) == excluded
    assert len(excluded) == plain["excluded_total"]
    candidates = {c["recipe"] for c in t["candidates"]}
    passed = {s["recipe"] for s in t["scored"]}
    assert passed | excluded == candidates and not passed & excluded
    shown = [s for s in t["scored"] if s["shown"]]
    assert [s["recipe"] for s in shown] == [f"rcp:{i['recipe_id']}" for i in plain["items"]]
    for s, item in zip(shown, plain["items"]):
        assert s["score"] == item["score"]
        assert s["breakdown"] == {b["key"]: b["value"] for b in item["breakdown"]}
    assert [s["final_rank"] for s in t["scored"]] == list(range(1, len(t["scored"]) + 1))
    assert sorted(s["score_rank"] for s in t["scored"]) == list(range(1, len(t["scored"]) + 1))


@pytest.mark.parametrize(("kind", "key"), SUBJECTS)
def test_trace_exclusions_equal_engine_exclusions(client, store, kind, key):
    """trace의 제외 행 = 엔진 recommend()의 제외 행(사유, 재료, 대상, certainty, via)."""
    body = make_subject(client, kind, key)
    t = post(client, {**body, "trace": True})["trace"]
    if kind == "persona":
        user, req = PERSONAS[key].user, PERSONAS[key].request
    else:
        user = user_context(store.get(body["profile_id"]))
        req = RecommendRequest(max_time_min=body.get("max_time_min"), time_is_hard=body.get("time_is_hard", False))
    recommender = client.app.state.engine_state.recommender
    engine_rows = {(f"rcp:{e.recipe_id}", e.reason.value, f"ing:{e.ingredient_id}" if e.ingredient_id else None,
                    e.target, e.certainty, tuple(f"ing:{x}" for x in e.via))
                   for e in recommender.recommend(user, req).exclusions}
    trace_rows = {(e["recipe"], e["reason"], e["ingredient"], e["target"], e["certainty"], tuple(e["via"]))
                  for e in t["exclusions"]}
    assert trace_rows == engine_rows


def test_profiles_cover_every_exclusion_reason(client):
    reasons = set()
    for name in PROFILES:
        t = post(client, {**make_subject(client, "profile", name), "trace": True})["trace"]
        reasons |= {e["reason"] for e in t["exclusions"]}
    assert {"allergen", "hard_dislike_ingredient", "hard_dislike_cuisine", "spicy_limit", "equipment", "time"} <= reasons


@pytest.mark.parametrize(("kind", "key"), SUBJECTS)
def test_path_links_exist_on_graph(client, kind, key):
    links, nodes = graph_index(client)
    t = post(client, {**make_subject(client, kind, key), "trace": True})["trace"]
    for e in t["exclusions"]:
        assert set(e["path_links"]) <= links, e
        if e["reason"] == "allergen":
            assert e["path_links"], e
            assert nodes[e["source_group"]]["group_kind"] == "base"
            target = nodes[e["target_node"]]
            assert e["source_group"] == e["target_node"] or e["source_group"] in target["members"]
            # via 연속 쌍이 모두 링크로 이어짐(빛이 끊기지 않음): 묶음·지정 링크 + via 쌍 수 + 사용 링크
            assert len([x for x in e["path_links"] if x.startswith(("isa:", "der:"))]) == len(e["via"]) - 1
    assert set(t["pantry"]["owned_links"]) <= links
    for c in t["candidates"]:
        assert any(line["basis"] for line in c["lines"]), c["recipe"]  # 엔진이 후보로 잡은 근거 줄이 있다
        assert all(line["link"] in links for line in c["lines"] if line["link"])


def test_multi_allergy_bundle_exclusion_lights_shrimp_path(client):
    """갑각류 묶음 알레르기 → 계란찜(새우젓) 제외: 묶음 → 새우 그룹 → … → 계란찜 경로."""
    t = post(client, {"persona_id": "multi_allergy", "trace": True, "pantry": ["egg", "potato"]})["trace"]
    rows = [e for e in t["exclusions"] if e["recipe"] == "rcp:gyeranjjim" and e["target"] == "crustacean_bundle"]
    assert rows
    row = rows[0]
    assert row["source_group"] == "ag:shrimp"
    assert row["path_links"][0] == "mem:crustacean_bundle>shrimp"
    assert row["path_links"][1].startswith("alg:") and row["path_links"][1].endswith(">shrimp")
    assert row["path_links"][-1].startswith("use:gyeranjjim#")
    assert t["excluded"]["rcp:gyeranjjim"] == "allergen"


def test_owned_includes_is_a_ancestors(client):
    t = post(client, {"persona_id": "korean_lover", "trace": True})["trace"]
    owned = {o["node"]: o for o in t["pantry"]["owned"]}
    assert owned["ing:pork_belly"]["because"] == "pantry"
    assert owned["ing:pork"]["because"] == "ancestor" and "ing:pork_belly" in owned["ing:pork"]["from"]
    assert "isa:pork_belly>pork" in t["pantry"]["owned_links"]
    assert any(o["because"] == "staple" for o in owned.values())


def test_subject_validation(client):
    assert client.post("/recommend", json={}).status_code == 422
    assert client.post("/recommend", json={"profile_id": 1, "persona_id": "beginner"}).status_code == 422
    assert client.post("/recommend", json={"persona_id": "nobody"}).status_code == 404


def test_personas_endpoint(client):
    ps = client.get("/personas").json()
    assert [p["id"] for p in ps] == list(PERSONAS) and len(ps) == 8
    multi = next(p for p in ps if p["id"] == "multi_allergy")
    assert {g["id"] for g in multi["allergen_groups"]} == {"egg", "milk", "crustacean_bundle"}


def test_persona_exclusion_log(client, tmp_path):
    post(client, {"persona_id": "multi_allergy"})
    rows = [json.loads(x) for x in (tmp_path / "exclusions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows and all(r["profile_id"] is None and r["persona_id"] == "multi_allergy" for r in rows)
