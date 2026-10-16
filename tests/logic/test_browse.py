"""재료로 레시피 찾기 단위 테스트 (engine/browse.py, ui-2): 조리 가능·거의 가능, is_a 방향, 기본 양념,
선택·고명, 미매칭, 대체재 미사용, 알레르기는 제외 대신 경고(추천 판정과 같은 근거)."""

from __future__ import annotations

import pytest

from engine.model import ExclusionReason, RecommendRequest, UserContext
from tests.logic.engine_kb import compile_logic_kb, recipe
from tests.support.engine_fixtures import build_recommender

RECIPES = [
    recipe("pork_stew", ("pork", "main"), ("salt", "seasoning")),  # 기본 양념만 더 필요
    recipe("belly_onion", ("pork_belly", "main"), ("onion", "sub")),
    recipe("belly_onion_tofu", ("pork_belly", "main"), ("onion", "sub"), ("tofu", "sub")),
    recipe("belly_three", ("pork_belly", "main"), ("onion", "sub"), ("tofu", "sub"), ("milk", "sub")),
    recipe("onion_egg_garnish", ("onion", "main"), ("egg", "garnish"), ("tofu", "sub", True)),
    recipe("onion_unmapped", ("onion", "main"), (None, "sub")),
    recipe("onion_butter", ("onion", "main"), ("butter", "sub")),
    recipe("tofu_only", ("tofu", "main")),
    recipe("onion_as_sub", ("tofu", "main"), ("onion", "sub")),
]


@pytest.fixture(scope="module")
def recommender():
    return build_recommender(compile_logic_kb(), RECIPES)


def browse(recommender, *selected, allergens=(), max_missing=None):
    r = recommender.browse(selected, allergens, max_missing=max_missing)
    return r, {i.recipe.id: i for i in r.cookable}, {i.recipe.id: i for i in r.near}


def test_cookable_requires_all_required_lines(recommender):
    _, ok, near = browse(recommender, "pork_belly", "onion")
    assert {"pork_stew", "belly_onion"} <= set(ok)  # 삼겹살 → "돼지고기" 충족(is_a), 소금은 기본 양념
    assert near["belly_onion_tofu"].missing == (3,)  # 두부 1개 부족
    assert near["belly_three"].missing == (3, 4)  # 2개 부족 → 기본 한도(2) 안
    assert "tofu_only" not in ok and "tofu_only" not in near  # 고른 재료가 main을 채우지 않음


def test_max_missing_limits_near(recommender):
    _, _, near = browse(recommender, "pork_belly", "onion", max_missing=1)
    assert "belly_onion_tofu" in near and "belly_three" not in near
    _, _, near = browse(recommender, "pork_belly", "onion", max_missing=0)
    assert near == {}


def test_parent_does_not_cover_child(recommender):
    _, ok, near = browse(recommender, "pork", "onion")
    assert "pork_stew" in ok
    assert all(r not in ok and r not in near for r in ("belly_onion", "belly_onion_tofu"))


def test_garnish_and_optional_do_not_block(recommender):
    _, ok, _ = browse(recommender, "onion")
    item = ok["onion_egg_garnish"]
    assert item.missing == () and item.optional_missing == (2, 3)


def test_unmapped_required_line_counts_as_missing(recommender):
    _, ok, near = browse(recommender, "onion")
    assert "onion_unmapped" not in ok and near["onion_unmapped"].missing == (2,)


def test_substitutes_not_used(recommender):
    # 식용유 → 버터 대체 관계가 있어도 조회에서는 쓰지 않는다. 버터가 없으면 부족
    _, _, near = browse(recommender, "onion", "cooking_oil")
    assert near["onion_butter"].missing == (2,)


def test_used_lists_selected_that_fill_lines(recommender):
    _, ok, near = browse(recommender, "pork_belly", "onion", "tofu")
    assert ok["pork_stew"].used == ("pork_belly",)
    assert ok["belly_onion_tofu"].used == ("pork_belly", "onion", "tofu")
    assert "onion_as_sub" in ok  # main 두부를 골랐으므로 대상


def test_unknown_and_concept_selection_ignored(recommender):
    r, ok, near = browse(recommender, "meat", "no_such", "onion", "onion")
    assert r.selected == ("onion",)
    assert "pork_stew" not in ok and "pork_stew" not in near


def test_allergy_is_warning_not_exclusion_and_matches_recommend_filter(recommender):
    """조회에서는 레시피가 남고 경고가 붙는다. 경고 근거는 추천 필터 제외 근거와 같다."""
    _, ok, near = browse(recommender, "onion", "pork_belly", allergens=("egg", "milk"))
    egg = ok["onion_egg_garnish"]  # 고명(계란)도 경고 대상
    assert [(e.reason, e.ingredient_id, e.target) for e in egg.allergy] == [(ExclusionReason.ALLERGEN, "egg", "egg")]
    assert near["belly_three"].allergy[0].target == "milk"
    assert [e.reason for e in near["onion_unmapped"].allergy] == [ExclusionReason.UNMAPPED_INGREDIENT]
    assert ok["belly_onion"].allergy == ()
    # 추천에서는 같은 레시피가 같은 사유로 제외된다(추천 규칙은 그대로)
    rec = recommender.recommend(UserContext(allergen_groups=frozenset({"egg", "milk"}), pantry=frozenset({"onion"})),
                                RecommendRequest(limit=100))
    assert "onion_egg_garnish" not in {i.recipe_id for i in rec.items}
    excluded = {(e.recipe_id, e.reason, e.target) for e in rec.exclusions}
    assert ("onion_egg_garnish", ExclusionReason.ALLERGEN, "egg") in excluded


def test_no_allergy_means_no_warning_even_for_unmapped(recommender):
    _, _, near = browse(recommender, "onion")
    assert near["onion_unmapped"].allergy == ()


def test_safe_recipes_sorted_first(recommender):
    r, _, _ = browse(recommender, "onion", allergens=("egg",))
    flags = [i.has_allergy_warning for i in r.cookable]
    assert flags == sorted(flags)


def test_unknown_allergen_group_rejected(recommender):
    with pytest.raises(ValueError):
        recommender.browse(["onion"], ["no_group"])
