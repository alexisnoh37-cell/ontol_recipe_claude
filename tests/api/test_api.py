"""FastAPI (Phase 1-5): 프로필·선호 저장, 추천 응답 형식, 별칭 검색, 알레르기 그룹 구분, 화면 안내 문구.

데이터는 실제 knowledge/·data/recipes/(storage.engine_source.load_files), 사용자는 메모리 저장소.
DB 저장소는 tests/storage/test_users.py가 같은 동작을 검사한다.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from storage.engine_source import load_files
from storage.users import InMemoryUserStore


@pytest.fixture(scope="module")
def data():
    return load_files()


@pytest.fixture()
def log_path(tmp_path):
    return tmp_path / "exclusions.jsonl"


@pytest.fixture()
def client(data, log_path):
    return TestClient(create_app(lambda: data, InMemoryUserStore(), exclusion_log=log_path))


def make_profile(client, name="테스트", **fields) -> int:
    pid = client.post("/profiles", json={"display_name": name, "skill_level": 2}).json()["id"]
    if fields:
        r = client.patch(f"/profiles/{pid}", json=fields)
        assert r.status_code == 200, r.text
    return pid


def set_prefs(client, pid, prefs):
    r = client.put(f"/profiles/{pid}/preferences", json={"preferences": prefs})
    assert r.status_code == 200, r.text
    return r.json()


# --- 프로필 -----------------------------------------------------------------------------------------


def test_profile_create_update_and_list(client):
    r = client.post("/profiles", json={"display_name": "엄마", "skill_level": 3, "household_size": 4})
    assert r.status_code == 201
    pid = r.json()["id"]
    r = client.patch(f"/profiles/{pid}", json={
        "skill_level": 2, "pantry": ["egg", "rice", "egg"], "equipment": ["오븐"],
        "tastes": [{"dimension": "spicy", "preferred_level": 1, "max_level": 2}],
    })
    body = r.json()
    assert body["skill_level"] == 2 and body["household_size"] == 4
    assert body["pantry"] == [{"id": "egg", "name": "계란"}, {"id": "rice", "name": "쌀"}]
    assert body["equipment"] == ["오븐"]
    assert client.get(f"/profiles/{pid}").json() == body
    assert [p["display_name"] for p in client.get("/profiles").json()] == ["엄마"]
    assert client.post("/profiles", json={"display_name": "엄마"}).status_code == 409


def test_profile_rejects_unknown_or_concept_pantry_and_bad_shape(client):
    pid = make_profile(client)
    assert client.patch(f"/profiles/{pid}", json={"pantry": ["no_such"]}).status_code == 400
    assert client.patch(f"/profiles/{pid}", json={"pantry": ["seafood"]}).status_code == 400  # concept
    assert client.patch(f"/profiles/{pid}", json={"equipment": ["화덕"]}).status_code == 400
    assert client.patch(f"/profiles/{pid}", json={"skill_level": 4}).status_code == 422
    bad_taste = {"tastes": [{"dimension": "spicy", "preferred_level": 4, "max_level": 2}]}
    assert client.patch(f"/profiles/{pid}", json=bad_taste).status_code == 422
    assert client.get("/profiles/999").status_code == 404


def test_preferences_saved_and_allergen_forced_hard(client):
    pid = make_profile(client)
    body = set_prefs(client, pid, [
        {"target_type": "allergen_group", "target_id": "shrimp", "polarity": 1},  # 알레르기는 항상 절대 제외로 저장
        {"target_type": "cuisine", "target_id": "한식", "polarity": 1, "strength": 0.8},
        {"target_type": "ingredient", "target_id": "seafood", "polarity": 1, "strength": 0.5},  # concept 선호 허용
    ])
    allergen = [p for p in body["preferences"] if p["target_type"] == "allergen_group"][0]
    assert allergen["polarity"] == -1 and allergen["is_hard"] is True
    assert body["allergen_groups"] == [{"id": "shrimp", "name": "새우"}]
    for bad in ({"target_type": "allergen_group", "target_id": "nope"},
                {"target_type": "ingredient", "target_id": "nope"},
                {"target_type": "cuisine", "target_id": "멕시코식"}):
        assert client.put(f"/profiles/{pid}/preferences", json={"preferences": [bad]}).status_code == 400
    hard_like = {"target_type": "ingredient", "target_id": "egg", "polarity": 1, "is_hard": True}
    assert client.put(f"/profiles/{pid}/preferences", json={"preferences": [hard_like]}).status_code == 422


# --- 지식 조회 --------------------------------------------------------------------------------------


def test_ingredient_search_by_alias(client):
    hits = client.get("/ingredients/search", params={"q": "달걀"}).json()
    assert hits[0]["id"] == "egg" and hits[0]["name"] == "계란" and hits[0]["matched"] == "달걀"
    assert client.get("/ingredients/search", params={"q": "다진 마늘"}).json()[0]["id"] == "garlic"
    ids = [h["id"] for h in client.get("/ingredients/search", params={"q": "해산물"}).json()]
    assert "seafood" not in ids  # concept는 기본 제외
    ids = [h["id"] for h in client.get("/ingredients/search",
                                       params={"q": "해산물", "include_concepts": True}).json()]
    assert "seafood" in ids
    assert client.get("/ingredients/search", params={"q": "ㅋㅋㅋ없는재료"}).json() == []


def test_allergen_groups_official_custom_bundle(client):
    groups = {g["id"]: g for g in client.get("/allergen-groups").json()}
    assert sum(g["category"] == "official" for g in groups.values()) == 19
    assert groups["shrimp"]["category_label"] == "법정 표시 대상"
    assert groups["sesame"]["category"] == "custom" and groups["other_fish"]["category"] == "custom"
    assert groups["fish_bundle"]["category"] == "bundle"
    assert {m["id"] for m in groups["fish_bundle"]["members"]} == {"mackerel", "other_fish"}
    assert groups["mackerel"]["notice"] == "다른 생선에도 반응하면 '생선 전체'를 선택하세요."
    order = [g["category"] for g in client.get("/allergen-groups").json()]
    assert order == sorted(order, key=["official", "custom", "bundle"].index)


# --- 추천 -------------------------------------------------------------------------------------------


def test_recommend_response_shape_names_and_breakdown(client):
    pid = make_profile(client, pantry=["pork", "kimchi", "rice", "egg"])
    r = client.post("/recommend", json={"profile_id": pid, "limit": 5})
    assert r.status_code == 200, r.text
    body = r.json()
    assert 0 < len(body["items"]) <= 5 and body["disclaimer"]
    for item in body["items"]:
        assert [b["key"] for b in item["breakdown"]] == list("IKTPDM")
        for m in item["missing"]:
            assert m["name"] and m["name"] != m["id"]  # id 대신 이름
        for note in item["notes"] + [item["missing_text"] or "", item["nice_to_have_text"] or ""]:
            assert "(는)" not in note and "(를)" not in note and "(가)" not in note


def test_recommend_allergy_excludes_and_summarises(client, log_path):
    pid = make_profile(client, pantry=["kimchi", "pork", "rice", "egg"])
    set_prefs(client, pid, [{"target_type": "allergen_group", "target_id": "shrimp"}])
    body = client.post("/recommend", json={"profile_id": pid}).json()
    titles = [i["recipe_id"] for i in body["items"]]
    assert "kimchi_jjigae" not in titles  # 김치(새우 포함 가능) → 제외
    summary = {s["reason"]: s for s in body["exclusion_summary"]}
    assert summary["allergen"]["count"] >= 1 and summary["allergen"]["label"].startswith("알레르기")
    assert summary["allergen"]["examples"]
    lines = [json.loads(x) for x in log_path.read_text(encoding="utf-8").splitlines()]
    assert any(x["recipe_id"] == "kimchi_jjigae" and x["reason"] == "allergen" and x["target"] == "shrimp"
               for x in lines)


def test_recommend_pantry_override_and_errors(client):
    pid = make_profile(client, pantry=["egg"])
    body = client.post("/recommend", json={"profile_id": pid, "pantry": ["salmon", "rice"]}).json()
    assert "salmon_don" in [i["recipe_id"] for i in body["items"]]
    assert client.post("/recommend", json={"profile_id": pid, "pantry": ["nope"]}).status_code == 400
    assert client.post("/recommend", json={"profile_id": 999}).status_code == 404


def test_display_notices_salmon_and_cooking_oil(client):
    pid = make_profile(client, pantry=["salmon", "rice"])
    items = {i["recipe_id"]: i for i in client.post("/recommend", json={"profile_id": pid}).json()["items"]}
    assert "횟감용 생연어 사용" in items["salmon_don"]["notices"]
    pid2 = make_profile(client, "기름", pantry=["egg", "rice"])
    items = {i["recipe_id"]: i for i in client.post("/recommend", json={"profile_id": pid2}).json()["items"]}
    oil = [i for i in items.values() if "제품의 기름 종류(콩기름 등)를 확인하세요." in i["notices"]]
    assert oil, "식용유가 들어간 레시피에 기름 종류 안내가 있어야 한다"


def processed_low(data, recipe_id):
    spec = next(r for r in data.recipes if r.id == recipe_id)
    ing = {i.id: i for i in data.knowledge.ingredients}
    return [i for i in dict.fromkeys(line.ingredient for line in spec.ingredients if line.ingredient)
            if ing[i].is_processed and ing[i].confidence == "low"]


def test_label_check_only_for_allergy_users_and_processed_low(client, data):
    """1-6 결정: 알레르기 설정이 있을 때만, 가공품이면서 confidence: low인 재료가 있을 때만, 재료 이름과 함께."""
    pantry = ["kimchi", "pork", "rice", "egg", "potato"]
    pid = make_profile(client, pantry=pantry)
    items = client.post("/recommend", json={"profile_id": pid}).json()["items"]
    assert items and all(i["label_check"] is None for i in items)  # 알레르기 설정 없음 → 표시 없음

    set_prefs(client, pid, [{"target_type": "allergen_group", "target_id": "peach"}])
    items = client.post("/recommend", json={"profile_id": pid}).json()["items"]
    ing = {i.id: i for i in data.knowledge.ingredients}
    shown = 0
    for item in items:
        expected = processed_low(data, item["recipe_id"])
        check = item["label_check"]
        if not expected:
            assert check is None
            continue
        shown += 1
        assert [c["id"] for c in check["ingredients"]] == expected
        assert check["text"] == "제품 성분표를 확인하세요: " + ", ".join(ing[i].name for i in expected)
        for c in check["ingredients"]:  # 단순 재료(소금·설탕 등 비가공품)는 대상 아님
            assert c["id"] not in {"salt", "sugar"} and ing[c["id"]].is_processed
    assert shown, "가공품·low 재료가 든 레시피가 하나 이상 있어야 표시를 검사할 수 있다"
    assert not ing["salt"].is_processed  # 소금이 제외되는 근거(데이터가 바뀌면 이 테스트로 알 수 있게)


def test_missing_split_required_vs_nice_to_have(client, data):
    """1-6: 꼭 필요한 재료(main·sub·비기본 seasoning) / 있으면 좋은 재료(garnish·optional). 판정·점수는 그대로."""
    pid = make_profile(client, pantry=["kimchi", "pork", "rice"])
    items = {i["recipe_id"]: i for i in client.post("/recommend", json={"profile_id": pid}).json()["items"]}
    jj = items["kimchi_jjigae"]
    spec = next(r for r in data.recipes if r.id == "kimchi_jjigae")
    roles = {}
    for line in spec.ingredients:
        roles.setdefault(line.ingredient, set()).add("optional" if line.optional else line.role)
    for m in jj["required_missing"]:
        assert roles[m["id"]] & {"main", "sub", "seasoning"}
    for m in jj["nice_to_have"]:
        assert roles[m["id"]] <= {"garnish", "optional"}
    nice = {m["id"] for m in jj["nice_to_have"]}
    assert {"green_onion", "tofu"} <= nice  # 대파 고명, 두부 선택
    assert jj["missing_text"] is None  # 꼭 필요한 재료는 다 있음 → "모두 갖고 있습니다"와 모순 없음
    assert jj["nice_to_have_text"].endswith("(없어도 조리할 수 있습니다)")
    assert not any("선택 재료라" in n for n in jj["notes"])  # 있으면 좋은 재료로 합쳐 표시
    for item in items.values():  # 기존 missing(엔진 출력)은 그대로 = 꼭 필요한 재료 + 고명
        assert {m["id"] for m in item["missing"]} <= {m["id"] for m in item["required_missing"] + item["nice_to_have"]}


def test_vocab_and_health(client, data):
    v = client.get("/vocab").json()
    assert "한식" in v["cuisines"] and "오븐" in v["equipment"] and v["disclaimer"]
    # 레시피 수는 시드에서 센다(draft 포함, 파일 하나 = 레시피 하나)
    seed_files = sorted((Path(__file__).resolve().parents[2] / "data" / "recipes").glob("*.yaml"))
    assert client.get("/health").json()["recipes"] == len(data.recipes) == len(seed_files) >= 50


# --- 레시피 상세 (ui-1) -----------------------------------------------------------------------------


def test_recipe_detail_lists_all_lines_by_role(client, data):
    body = client.get("/recipes/kimchi_jjigae").json()
    spec = next(r for r in data.recipes if r.id == "kimchi_jjigae")
    assert body["title"] == spec.title and body["cuisine"] == spec.cuisine
    assert [x["raw_text"] for x in body["ingredients"]] == [line.raw_text for line in spec.ingredients]
    labels = {"main": "주재료", "sub": "부재료", "seasoning": "양념", "garnish": "고명"}
    for x in body["ingredients"]:
        assert x["role_label"] == labels[x["role"]]
        assert x["have"] is None  # 보유 기준이 없으면 판단하지 않는다
        if x["id"]:
            assert x["name"] != x["id"]
    assert [s for s in body["steps"]] == [s.text for s in spec.steps]
    assert body["label_check"] is None


def test_recipe_detail_have_follows_engine_rule(client):
    """보유 = 보유 재료·기본 양념과 is_a 조상. 삼겹살 보유 → '돼지고기' 줄 충족, 반대 방향은 아님."""
    have = {x["id"]: x["have"] for x in
            client.get("/recipes/kimchi_jjigae", params={"pantry": ["pork_belly", "kimchi"]}).json()["ingredients"]}
    assert have["pork"] is True and have["kimchi"] is True
    assert have["garlic"] is True  # 기본 양념
    assert have["tofu"] is False
    pid = make_profile(client, pantry=["kimchi"])
    have = {x["id"]: x["have"] for x in
            client.get("/recipes/kimchi_jjigae", params={"profile_id": pid}).json()["ingredients"]}
    assert have["kimchi"] is True and have["pork"] is False
    # pantry를 주면 프로필 보유 재료 대신 쓴다
    have = {x["id"]: x["have"] for x in
            client.get("/recipes/kimchi_jjigae", params={"profile_id": pid, "pantry": ["pork"]}).json()["ingredients"]}
    assert have["kimchi"] is False and have["pork"] is True


def test_recipe_detail_errors(client):
    assert client.get("/recipes/no_such").status_code == 404
    assert client.get("/recipes/kimchi_jjigae", params={"profile_id": 999}).status_code == 404
    assert client.get("/recipes/kimchi_jjigae", params={"pantry": ["nope"]}).status_code == 400
    assert client.get("/recipes/kimchi_jjigae", params={"pantry": ["seafood"]}).status_code == 400  # concept


def test_recipe_detail_label_check_only_with_allergy(client, data):
    ing = {i.id: i for i in data.knowledge.ingredients}
    rid = next(r.id for r in data.recipes
               if any(line.ingredient and ing[line.ingredient].is_processed and ing[line.ingredient].confidence == "low"
                      for line in r.ingredients))
    pid = make_profile(client)
    assert client.get(f"/recipes/{rid}", params={"profile_id": pid}).json()["label_check"] is None
    set_prefs(client, pid, [{"target_type": "allergen_group", "target_id": "shrimp"}])
    check = client.get(f"/recipes/{rid}", params={"profile_id": pid}).json()["label_check"]
    assert check and check["ingredients"]


# --- 재료로 레시피 찾기 (ui-2) ----------------------------------------------------------------------


def test_browse_cookable_and_near_with_names(client):
    body = client.get("/browse", params={"ingredients": ["pork_belly", "kimchi"]}).json()
    assert body["selected"] == [{"id": "pork_belly", "name": "삼겹살"}, {"id": "kimchi", "name": "배추김치"}]
    cookable = {i["recipe_id"]: i for i in body["cookable"]}
    jj = cookable["kimchi_jjigae"]  # 삼겹살 → "돼지고기" 충족(is_a), 양념은 기본 양념, 두부·양파 선택, 대파 고명
    assert jj["missing"] == [] and jj["missing_count"] == 0
    assert [u["id"] for u in jj["used"]] == ["pork_belly", "kimchi"]
    assert {m["id"] for m in jj["optional_missing"]} >= {"tofu", "green_onion"}
    assert jj["allergy_warnings"] == [] and body["allergy_notice"] is None
    assert jj["graph"]["recipe"] == "rcp:kimchi_jjigae" and "ing:pork_belly" in jj["graph"]["used_nodes"]
    for item in body["near"]:
        assert 1 <= item["missing_count"] <= 2 and len(item["missing"]) == item["missing_count"]
        for m in item["missing"]:
            assert m["name"] and m["role"] in {"main", "sub", "seasoning"} and not m["optional"]


def test_browse_allergy_warns_instead_of_excluding(client):
    params = {"ingredients": ["pork_belly", "kimchi"], "allergen_groups": ["shrimp"]}
    body = client.get("/browse", params=params).json()
    jj = next(i for i in body["cookable"] if i["recipe_id"] == "kimchi_jjigae")
    assert any(w["reason"] == "allergen" and w["group"] == "shrimp" and w["certainty"] == "possible"
               for w in jj["allergy_warnings"])  # 김치(새우 포함 가능) → 경고, 목록에는 남는다
    assert body["allergy_notice"]
    pid = make_profile(client, pantry=["pork_belly", "kimchi"])
    set_prefs(client, pid, [{"target_type": "allergen_group", "target_id": "shrimp"}])
    by_profile = client.get("/browse", params={"ingredients": ["pork_belly", "kimchi"], "profile_id": pid}).json()
    assert by_profile["cookable"] == body["cookable"]
    # 추천은 그대로 제외한다
    rec = client.post("/recommend", json={"profile_id": pid}).json()
    assert "kimchi_jjigae" not in [i["recipe_id"] for i in rec["items"]]


def test_browse_max_missing_and_errors(client):
    zero = client.get("/browse", params={"ingredients": ["pork_belly", "kimchi"], "max_missing": 0}).json()
    assert zero["near"] == [] and zero["cookable"]
    assert client.get("/browse").status_code == 422
    assert client.get("/browse", params={"ingredients": ["nope"]}).status_code == 400
    assert client.get("/browse", params={"ingredients": ["seafood"]}).status_code == 400  # concept
    assert client.get("/browse", params={"ingredients": ["egg"], "allergen_groups": ["no_group"]}).status_code == 400
    assert client.get("/browse", params={"ingredients": ["egg"], "profile_id": 999}).status_code == 404
    assert client.get("/browse", params={"ingredients": ["egg"], "persona_id": "nope"}).status_code == 404
    both = {"ingredients": ["egg"], "profile_id": 1, "allergen_groups": ["egg"]}
    assert client.get("/browse", params=both).status_code == 400
    assert client.get("/browse", params={"ingredients": ["egg"], "max_missing": 9}).status_code == 422


def test_commercial_notice_above_ingredients_for_everyone(client, data):
    """um-2·ir-2 사람 결정: 시판 제품이 든 레시피는 알레르기 설정과 무관하게 재료 목록 위에 안내를 띄운다."""
    from api.present import commercial_products, load_display

    _, commercial = commercial_products(load_display())
    assert {"instant_noodle_product", "instant_stock", "starch"} <= commercial
    with_it = next(r for r in data.recipes if any(line.ingredient in commercial for line in r.ingredients))
    without = next(r for r in data.recipes if not any(line.ingredient in commercial for line in r.ingredients))
    pid = make_profile(client)  # 알레르기 설정 없음
    d = client.get(f"/recipes/{with_it.id}", params={"profile_id": pid}).json()
    notice = d["commercial_notice"]
    assert notice["text"] == "시판 제품으로 제품 성분을 확인해 알레르기 유무를 확인하시기 바랍니다."
    assert {i["id"] for i in notice["ingredients"]} <= commercial and notice["ingredients"]
    assert client.get(f"/recipes/{without.id}", params={"profile_id": pid}).json()["commercial_notice"] is None
    node = next(n for n in client.get("/graph", params={"recipes": "all"}).json()["nodes"]
                if n["id"] == f"rcp:{with_it.id}")
    assert node["commercial_notice"]["text"] == notice["text"]


def test_commercial_notice_config_rejects_unknown_ingredient(data):
    from api.present import Catalog, load_display

    display = load_display()
    display["commercial_product_notice"] = {"text": "x", "ingredients": ["no_such_thing"]}
    with pytest.raises(ValueError):
        Catalog(data, display)
