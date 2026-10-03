"""시연용 저장 프로필(scripts/seed_demo_profiles.py, viz-5): id가 실제 지식에 있고, 다시 실행하면 건너뛰며,
README "시연 순서"의 장면이 실제 trace 응답에 나오는지 확인한다(화면은 trace를 그대로 그린다)."""

from __future__ import annotations

from scripts.seed_demo_profiles import DEMO_PROFILES, check_ids, seed


def run_trace(client, pid: int) -> dict:
    r = client.post("/recommend", json={"profile_id": pid, "trace": True, "limit": 10})
    assert r.status_code == 200, r.text
    return r.json()["trace"]


def seeded(client, store) -> dict[str, dict]:
    return {name: run_trace(client, pid) for name, pid, _ in seed(store)}


def test_ids_exist_in_knowledge(data):
    assert check_ids(data.knowledge) == []


def test_seed_skips_existing(store):
    first = seed(store)
    assert [c for _, _, c in first] == [True] * len(DEMO_PROFILES)
    second = seed(store)
    assert [c for _, _, c in second] == [False] * len(DEMO_PROFILES)
    assert [pid for _, pid, _ in second] == [pid for _, pid, _ in first]
    assert len(store.list()) == len(DEMO_PROFILES)
    shrimp = store.get(first[0][1])
    assert [(r.target_type, r.target_id, r.is_hard) for r in shrimp.preferences] == [("allergen_group", "shrimp", True)]


def allergen_rows(t: dict, recipe: str) -> list[dict]:
    return [e for e in t["exclusions"] if e["recipe"] == recipe and e["reason"] == "allergen"]


def test_shrimp_scene(client, store):
    t = seeded(client, store)["시연: 새우 알레르기"]
    for recipe in ("rcp:kimchi_jjigae", "rcp:gyeranjjim"):
        assert t["excluded"].get(recipe) == "allergen", recipe
        rows = allergen_rows(t, recipe)
        assert rows and all(e["source_group"] == "ag:shrimp" for e in rows)
        assert any("ing:saeujeot" in e["via"] for e in rows)  # 새우젓 → 새우 경로
    kimchi = allergen_rows(t, "rcp:kimchi_jjigae")
    assert any(e["via"][:1] == ["ing:kimchi"] for e in kimchi)  # 배추김치 → 새우젓 → 새우


def test_spicy_scene(client, store):
    t = seeded(client, store)["시연: 매운 것 못 먹음"]
    assert t["user"]["spicy_max"] == 1
    spicy = [r for r, reason in t["excluded"].items() if reason == "spicy_limit"]
    assert len(spicy) >= 2
    assert not t["user"]["allergen_groups"]


def test_nuts_scene(client, store):
    t = seeded(client, store)["시연: 견과류 알레르기"]
    assert t["excluded"].get("rcp:myeolchi_bokkeum") == "allergen"
    rows = allergen_rows(t, "rcp:myeolchi_bokkeum")
    assert any(e["ingredient"] == "ing:almond" and e["target_node"] == "ag:nuts_bundle" for e in rows)
