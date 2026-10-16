"""POST /analyze-recipe (docs/plan.md 부록 E): DB에 없는 레시피의 재료·알레르기 구조, 저장 안 함, 사용자 판정.

데이터는 실제 knowledge/·data/recipes/(load_files), 사용자는 메모리 저장소. 판정은 엔진의 UserConstraints.check를
그대로 쓰므로 여기서는 연결(미매칭·concept·possible 처리, 경로, 입력 검증, 로그)을 본다.
"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from storage.engine_source import load_files
from storage.users import InMemoryUserStore

MAPO = "[양념장]\n두부 1모, 다진 돼지고기 100g\n두반장 1큰술, 굴소스 약간\n해산물 50g\n트러플 오일 1작은술\n물 200ml"
KNOWN_ONLY = "두부 1모\n다진 돼지고기 100g\n대파 1대"


@pytest.fixture(scope="module")
def data():
    return load_files()


@pytest.fixture()
def log_path(tmp_path):
    return tmp_path / "exclusions.jsonl"


@pytest.fixture()
def client(data, log_path):
    return TestClient(create_app(lambda: data, InMemoryUserStore(), exclusion_log=log_path))


def analyze(client, text=MAPO, status=200, **extra):
    r = client.post("/analyze-recipe", json={"title": "AI 마파두부", "text": text, **extra})
    assert r.status_code == status, r.text
    return r.json()


def line(body, n):
    return next(x for x in body["lines"] if x["line_no"] == n)


def base_graph(client):
    return client.get("/graph", params={"recipes": "none"}).json()


# --- 구조 -------------------------------------------------------------------------------------------


def test_lines_are_mapped_concept_or_unmapped(client):
    body = analyze(client)
    assert [(x["raw_text"], x["status"]) for x in body["lines"]] == [
        ("두부 1모", "mapped"), ("다진 돼지고기 100g", "mapped"), ("두반장 1큰술", "mapped"), ("굴소스 약간", "mapped"),
        ("해산물 50g", "concept"), ("트러플 오일 1작은술", "unmapped"),
    ]
    assert [line(body, n)["ingredient"]["id"] for n in (1, 2, 3, 4)] == ["tofu", "ground_pork", "doubanjiang", "oyster_sauce"]
    assert line(body, 5)["ingredient"] is None and line(body, 5)["concept"]["id"] == "seafood"
    assert body["counts"] == {"lines": 6, "mapped": 4, "concept": 1, "unmapped": 1}
    assert body["skipped"] == ["양념장", "물 200ml"]  # 버린 항목은 숨기지 않는다
    assert body["judgement"] is None  # 사용자를 주지 않으면 구조만
    assert body["recipe_id"].startswith("adhoc_")


def test_text_and_ingredient_list_give_same_lines(client):
    a = analyze(client, text=KNOWN_ONLY)
    r = client.post("/analyze-recipe", json={"title": "AI 마파두부", "ingredients": KNOWN_ONLY.split("\n")})
    assert r.status_code == 200
    assert r.json()["lines"] == a["lines"]


def test_line_structure_matches_compiled_knowledge(client):
    """줄별 알레르기 행은 /graph 재료 노드의 allergens(컴파일된 closure)와 같다. is_a·원천도 컴파일 결과 그대로."""
    body = analyze(client)
    nodes = {n["id"]: n for n in base_graph(client)["nodes"]}
    for x in body["lines"]:
        if x["status"] != "mapped":
            assert x["allergens"] == [] and x["is_a"] == [] and x["derived_from"] == []
            continue
        expected = nodes[x["ingredient"]["node"]]["allergens"]
        assert [{k: a[k] for k in ("group", "certainty", "via", "path_links")} for a in x["allergens"]] == expected
    assert [a["id"] for a in line(body, 2)["is_a"]] == ["pork", "meat"]  # 다진 돼지고기 → 돼지고기 → 고기
    assert {(s["id"], s["certainty"]) for s in line(body, 1)["derived_from"]} == {("soybean", "definite")}
    soy = {a["group_id"]: a["certainty"] for a in line(body, 3)["allergens"]}
    assert soy["soybean"] == "possible"  # 두반장: 대두 포함 가능


def test_recipe_summary_and_overlay_graph(client):
    body = analyze(client)
    groups = {a["group_id"]: a for a in body["allergens"]}
    assert groups["soybean"]["certainty"] == "definite"  # 두부 줄이 definite
    assert {h["line_no"] for h in groups["soybean"]["hits"]} == {1, 3, 4}
    assert groups["pork"]["certainty"] == "definite"

    rid = body["recipe_id"]
    g = body["graph"]
    recipe = g["nodes"][0]
    assert recipe["id"] == f"rcp:{rid}" and recipe["adhoc"] and recipe["has_unmapped"]
    assert recipe["allergens"] == [{k: a[k] for k in ("group", "certainty", "optional_only", "hits")}
                                   for a in body["allergens"]]
    raw = {n["id"]: n for n in g["nodes"][1:]}
    assert set(raw) == {f"raw:{rid}#5", f"raw:{rid}#6"} and all(n["kind"] == "unmapped" for n in raw.values())
    assert raw[f"raw:{rid}#5"]["concept"] == "ing:seafood"
    uses = [lk for lk in g["links"] if lk["type"] == "uses"]
    assert [lk["target"] for lk in uses] == ["ing:tofu", "ing:ground_pork", "ing:doubanjiang", "ing:oyster_sauce"]
    assert [lk["target"] for lk in g["links"] if lk["type"] == "unmapped"] == [f"raw:{rid}#5", f"raw:{rid}#6"]

    # 겹쳐 보기 간선 끝은 기존 그래프 노드이거나 겹쳐 보기 노드다
    known = {n["id"] for n in base_graph(client)["nodes"]} | {n["id"] for n in g["nodes"]}
    assert all(lk["source"] in known and lk["target"] in known for lk in g["links"])


def test_analysis_is_not_saved(client):
    before = client.get("/graph", params={"recipes": "all"})
    health = client.get("/health").json()
    analyze(client, allergen_groups=["soybean"])
    after = client.get("/graph", params={"recipes": "all"})
    assert after.headers["etag"] == before.headers["etag"]
    assert client.get("/health").json()["recipes"] == health["recipes"]
    assert not any(n["id"].startswith("rcp:adhoc_") for n in after.json()["nodes"])


# --- 사용자 판정 ------------------------------------------------------------------------------------


def test_allergy_excludes_definite_possible_and_unmapped_lines(client):
    body = analyze(client, allergen_groups=["soybean"])
    j = body["judgement"]
    assert j["excluded"] and [g["id"] for g in j["allergen_groups"]] == ["soybean"]
    allergen = {(e["ingredient"], e["certainty"]) for e in j["exclusions"] if e["reason"] == "allergen"}
    assert allergen == {("ing:tofu", "definite"), ("ing:doubanjiang", "possible"), ("ing:oyster_sauce", "possible")}
    unmapped = [e for e in j["exclusions"] if e["reason"] == "unmapped_ingredient"]
    assert [e["lines"] for e in unmapped] == [[5], [6]]  # concept 줄도 미매칭으로 제외(A1)
    rid = body["recipe_id"]
    assert [e["path_links"] for e in unmapped] == [[f"unm:{rid}#5"], [f"unm:{rid}#6"]]
    assert "매운맛 한도" in j["not_checked"]


def test_allergy_paths_walk_real_links(client):
    body = analyze(client, allergen_groups=["soybean"])
    links = {lk["id"] for lk in base_graph(client)["links"]} | {lk["id"] for lk in body["graph"]["links"]}
    for e in body["judgement"]["exclusions"]:
        assert e["path_links"] and all(x in links for x in e["path_links"]), e


def test_unrelated_allergy_still_excludes_unmapped_lines(client):
    """알레르기와 무관해 보여도 미매칭 줄이 있으면 판정할 수 없으므로 제외(안전 규칙)."""
    j = analyze(client, allergen_groups=["peach"])["judgement"]
    assert j["excluded"] and {e["reason"] for e in j["exclusions"]} == {"unmapped_ingredient"}


def test_no_allergy_passes_even_with_unmapped_lines(client):
    pid = client.post("/profiles", json={"display_name": "알레르기 없음", "skill_level": 2}).json()["id"]
    j = analyze(client, profile_id=pid)["judgement"]
    assert not j["excluded"] and j["exclusions"] == [] and j["allergen_groups"] == []


def test_known_only_recipe_passes_allergy_it_does_not_touch(client):
    j = analyze(client, text=KNOWN_ONLY, allergen_groups=["egg"])["judgement"]
    assert not j["excluded"]


def test_bundle_group_from_persona_reports_source_group(client):
    """페르소나(multi_allergy: 계란·우유·갑각류 묶음). 새우 줄은 묶음으로 제외되고 실제 걸린 기본 그룹을 함께 준다."""
    j = analyze(client, text="새우 100g\n두부 1모", persona_id="multi_allergy")["judgement"]
    hit = [e for e in j["exclusions"] if e["reason"] == "allergen"]
    assert [(e["ingredient"], e["target_node"], e["source_group"]) for e in hit] == [
        ("ing:shrimp_raw", "ag:crustacean_bundle", "ag:shrimp")]


def test_hard_dislike_from_profile(client):
    pid = client.post("/profiles", json={"display_name": "돼지고기 싫음", "skill_level": 2}).json()["id"]
    r = client.put(f"/profiles/{pid}/preferences", json={"preferences": [
        {"target_type": "ingredient", "target_id": "pork", "polarity": -1, "is_hard": True}]})
    assert r.status_code == 200
    j = analyze(client, text=KNOWN_ONLY, profile_id=pid)["judgement"]
    assert [(e["reason"], e["ingredient"], e["target_node"]) for e in j["exclusions"]] == [
        ("hard_dislike_ingredient", "ing:ground_pork", "ing:pork")]


def test_exclusions_are_logged(client, log_path):
    body = analyze(client, allergen_groups=["soybean"])
    rows = [json.loads(x) for x in log_path.read_text(encoding="utf-8").splitlines()]
    assert rows and {r["recipe_id"] for r in rows} == {body["recipe_id"]}
    assert len(rows) == len(body["judgement"]["exclusions"])


# --- 입력 검증 --------------------------------------------------------------------------------------


@pytest.mark.parametrize("payload", [
    {"title": "x"},  # 재료 없음
    {"title": "x", "text": "두부", "ingredients": ["두부"]},  # 둘 다
    {"title": "x", "text": "두부", "persona_id": "multi_allergy", "allergen_groups": ["egg"]},  # 사용자 둘
    {"title": " ", "text": "두부"},
    {"title": "x", "text": "두부", "unknown": 1},
])
def test_shape_errors_are_422(client, payload):
    assert client.post("/analyze-recipe", json=payload).status_code == 422


def test_reference_errors(client):
    assert client.post("/analyze-recipe", json={"title": "x", "text": "물 1컵"}).status_code == 400  # 재료 없음
    assert client.post("/analyze-recipe", json={"title": "x", "text": "두부", "allergen_groups": ["nope"]}).status_code == 400
    assert client.post("/analyze-recipe", json={"title": "x", "text": "두부", "persona_id": "nope"}).status_code == 404
    assert client.post("/analyze-recipe", json={"title": "x", "text": "두부", "profile_id": 999}).status_code == 404
