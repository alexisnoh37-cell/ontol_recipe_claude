"""실제 knowledge/ 파일 스모크 테스트. 데이터를 고친 뒤에도 핵심 불변식이 유지되는지 본다."""

from __future__ import annotations

from pathlib import Path

import pytest

from kb import compile_paths

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def ck():
    return compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")


def test_real_knowledge_compiles(ck):
    assert len(ck.ingredients) > 0


def test_hidden_allergens(ck):
    shrimp = ck.closure_of("shrimp")
    assert shrimp["saeujeot"].certainty == "definite"
    assert shrimp["kimchi"].certainty == "possible"
    assert ck.closure_of("soybean")["doenjang"].certainty == "definite"
    assert ck.closure_of("wheat")["doenjang"].certainty == "possible"
    assert ck.closure_of("wheat")["soy_sauce"].certainty == "definite"
    assert ck.closure_of("egg")["mayonnaise"].certainty == "definite"
    assert ck.closure_of("peanut")["peanut_butter"].certainty == "definite"
    assert ck.closure_of("milk")["butter"].certainty == "definite"


def test_pantry_staples_resolve_and_garlic_renamed(ck):
    assert "garlic" in ck.pantry_staples
    assert "garlic_minced" not in ck.ingredient_ids
    staples = {i.id for i in ck.ingredients if i.is_pantry_staple}
    assert staples == set(ck.pantry_staples)


def test_garlic_minced_is_form_alias(ck):
    by_norm = {a.alias_norm: a for a in ck.aliases}
    assert by_norm["다진마늘"].ingredient_id == "garlic"
    assert by_norm["다진마늘"].form == "minced"


def test_ambiguous_alias_removed_and_soybean_oil_separate(ck):
    assert "파" not in {a.alias_norm for a in ck.aliases}
    by_norm = {a.alias_norm: a.ingredient_id for a in ck.aliases}
    assert by_norm["콩기름"] == "soybean_oil"
    assert ck.closure_of("soybean")["soybean_oil"].certainty == "possible"


def test_all_knowledge_is_reviewed(ck):
    # 0-4 사람 검수 완료(2026-10-03). 새로 추가하는 항목은 draft로 넣고 검수 후 reviewed로 바꾼다.
    assert all(i.status == "reviewed" for i in ck.ingredients)
    assert all(g.status == "reviewed" for g in ck.allergen_groups)


# --- D4 알레르기 그룹 확정 내용 (docs/decisions.md) -------------------------

OFFICIAL_19 = {
    "egg", "milk", "buckwheat", "peanut", "soybean", "wheat", "mackerel", "crab", "shrimp", "pork",
    "peach", "tomato", "sulfites", "walnut", "chicken", "beef", "squid", "shellfish", "pine_nut",
}
CUSTOM = {"other_fish", "sesame", "other_cephalopods", "other_tree_nuts"}
BUNDLES = {
    "crustacean_bundle": {"shrimp", "crab"},
    "nuts_bundle": {"peanut", "walnut", "pine_nut", "other_tree_nuts"},
    "fish_bundle": {"mackerel", "other_fish"},
    "seafood_bundle": {"shrimp", "crab", "squid", "other_cephalopods", "shellfish", "mackerel", "other_fish"},
}


def test_d4_groups_match_decision(ck):
    base = {g.id: g for g in ck.allergen_groups if g.kind == "base"}
    assert {gid for gid, g in base.items() if g.official} == OFFICIAL_19
    assert {gid for gid, g in base.items() if not g.official} == CUSTOM
    assert all(base[g].source == "law_annex2" for g in OFFICIAL_19)
    assert all(base[g].source == "custom" for g in CUSTOM)
    members = {}
    for m in ck.group_members:
        members.setdefault(m.bundle_id, set()).add(m.member_id)
    assert members == BUNDLES


def test_allergens_yaml_declares_official_and_source_explicitly():
    # 스키마 기본값(false/custom)에 기대지 않고 파일에 직접 적었는지 확인
    import yaml

    data = yaml.safe_load((ROOT / "knowledge" / "allergens.yaml").read_text(encoding="utf-8"))
    for item in data["groups"] + data["bundles"]:
        assert "official" in item and "source" in item, item["id"]


def test_every_base_group_has_ingredients(ck):
    assert not [w for w in ck.warnings if w.code == "empty_allergen_group"]


def test_plan_5_2_hidden_allergen_checklist(ck):
    # docs/plan.md 5-2 체크리스트와 0-4 추가 항목
    expected = [
        ("shrimp", "saeujeot"), ("other_fish", "anchovy_fish_sauce"), ("other_fish", "fish_sauce"),
        ("shrimp", "kimchi"), ("shellfish", "oyster_sauce"), ("egg", "mayonnaise"),
        ("peanut", "peanut_butter"), ("soybean", "soy_sauce"), ("wheat", "soy_sauce"),
        ("soybean", "doenjang"), ("wheat", "doenjang"), ("soybean", "gochujang"), ("wheat", "gochujang"),
        ("milk", "butter"), ("milk", "cheese"), ("milk", "heavy_cream"),
        ("wheat", "buchimgaru"), ("wheat", "bread_crumbs"), ("wheat", "curry_powder"),
        ("other_fish", "anchovy_stock"), ("sesame", "sesame_oil"), ("mackerel", "fish_cake"),
        ("other_fish", "fish_cake"), ("pork", "ham"), ("pork", "sausage"), ("sulfites", "wine"),
        ("sulfites", "raisin"),
    ]
    missing = [(g, i) for g, i in expected if i not in ck.closure_of(g)]
    assert not missing


def test_review_table_is_up_to_date(ck):
    import importlib.util

    spec = importlib.util.spec_from_file_location("make_review", ROOT / "scripts" / "make_review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    committed = (ROOT / "docs" / "review" / "ingredients_review.md").read_text(encoding="utf-8")
    assert committed == module.render(ck), "검수표가 최신이 아닙니다: uv run python scripts/make_review.py"


def test_review_fixes_0_4(ck):
    # 0-4 검수 안전 수정
    for octo in ("octopus", "small_octopus", "webfoot_octopus"):
        assert ck.closure_of("other_cephalopods")[octo].certainty == "definite"
        assert octo in ck.closure_of("seafood_bundle")
    assert ck.closure_of("other_tree_nuts")["almond"].certainty == "definite"
    assert ck.closure_of("other_tree_nuts")["chestnut"].certainty == "possible"
    assert "almond" in ck.closure_of("nuts_bundle")
    assert {g.id: g.display_name for g in ck.allergen_groups}["nuts_bundle"] == "견과류"
    assert ck.closure_of("shellfish")["jeotgal"].certainty == "possible"
    assert ck.closure_of("shellfish")["eorigul_jeot"].certainty == "definite"
    assert ck.closure_of("shellfish")["jogae_jeot"].certainty == "definite"
    for kimchi in ("kimchi", "kkakdugi"):
        assert ck.closure_of("wheat")[kimchi].certainty == "possible"
        assert ck.closure_of("shellfish")[kimchi].certainty == "possible"
