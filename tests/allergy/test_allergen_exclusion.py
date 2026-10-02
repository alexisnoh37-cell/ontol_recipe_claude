"""알레르기 재료가 든 레시피는 제외된다 (docs/plan.md 7-1, 0-3 추가 시나리오 1~6, 10).

모든 제외 사례에 대조군 두 개를 짝으로 둔다.
  - 같은 레시피가 알레르기 없는 사용자에게는 추천된다(데이터·후보 문제로 빠진 것이 아님을 보장).
  - 같은 알레르기 사용자에게도 안전한 레시피(감자구이)는 추천된다(엔진이 전부 제외해서 통과하는 것을 방지).
"""

from __future__ import annotations

import pytest

from engine.model import ExclusionReason
from tests.allergy import fixtures as fx
from tests.allergy.checks import assert_excluded, assert_recommended

# (시나리오, 사용자 알레르기, 제외되어야 할 레시피, 제외를 일으키는 재료)
CASES = [
    ("7-1 새우 → 새우젓", ("shrimp",), "cabbage_saeujeot_soup", "saeujeot"),
    ("7-1 견과류 → 땅콩버터", ("nuts_bundle",), "peanut_butter_cucumber", "peanut_butter"),
    ("7-1 견과류 → 호두", ("nuts_bundle",), "walnut_roast", "walnut"),
    ("7-1 난류 → 마요네즈", ("egg",), "mayo_cucumber_salad", "mayonnaise"),
    ("7-1 밀 → 간장", ("wheat",), "soy_braised_potato", "soy_sauce"),
    ("7-1 밀 → 부침가루", ("wheat",), "pajeon", "buchimgaru"),
    ("7-1·5 난류 → 선택 재료 계란", ("egg",), "mushroom_rice_optional_egg", "egg"),
    ("5 난류 → 고명 계란", ("egg",), "cucumber_soup_egg_garnish", "egg"),
    ("1 조개류 → 굴소스", ("shellfish",), "oyster_sauce_mushroom", "oyster_sauce"),
    ("2 밀 → 고추장(포함 가능)", ("wheat",), "gochujang_potato", "gochujang"),
    ("3 새우 → 김치(포함 가능)", ("shrimp",), "kimchi_fried_rice", "kimchi"),
    ("4 갑각류 → 새우", ("crustacean_bundle",), "shrimp_stirfry", "shrimp_raw"),
    ("4 갑각류 → 게", ("crustacean_bundle",), "crab_soup", "crab"),
    ("4 갑각류 → 김치(새우 경유)", ("crustacean_bundle",), "kimchi_fried_rice", "kimchi"),
    ("6 대두 → 기본 양념 간장", ("soybean",), "soy_braised_potato", "soy_sauce"),
    ("추가1 새우 → 중간 노드 젓갈류(하위 알레르기 포함 가능)", ("shrimp",), "jeotgal_cabbage_salad", "jeotgal"),
    ("추가2 새우 → 3단계 파생 김치양념소스", ("shrimp",), "kimchi_sauce_potato", "kimchi_sauce"),
    ("추가3 우유 → 원천 재료 자체가 포함 가능", ("milk",), "seasoning_blend_mushroom", "seasoning_blend"),
    ("추가4 조개류 → 상위(조개)에 지정, 하위 바지락", ("shellfish",), "manila_clam_soup", "manila_clam"),
    ("추가8 해산물 전체 → 굴소스", ("seafood_bundle",), "oyster_sauce_mushroom", "oyster_sauce"),
    ("추가8 해산물 전체 → 김치(새우 경유)", ("seafood_bundle",), "kimchi_fried_rice", "kimchi"),
    ("추가8 해산물 전체 → 바지락", ("seafood_bundle",), "manila_clam_soup", "manila_clam"),
    ("추가8 해산물 전체 → 오징어", ("seafood_bundle",), "squid_stirfry", "squid_raw"),
]
IDS = [c[0] for c in CASES]


@pytest.mark.parametrize(("scenario", "allergens", "recipe_id", "trigger"), CASES, ids=IDS)
def test_allergen_recipe_is_excluded(recommend, scenario, allergens, recipe_id, trigger):
    result = recommend(fx.user(*allergens))
    assert_excluded(result, recipe_id, ExclusionReason.ALLERGEN, trigger)


@pytest.mark.parametrize(("scenario", "allergens", "recipe_id", "trigger"), CASES, ids=IDS)
def test_control_same_recipe_recommended_without_allergy(recommend, scenario, allergens, recipe_id, trigger):
    assert_recommended(recommend(fx.NO_ALLERGY), recipe_id)


@pytest.mark.parametrize(("scenario", "allergens", "recipe_id", "trigger"), CASES, ids=IDS)
def test_control_safe_recipe_still_recommended(recommend, scenario, allergens, recipe_id, trigger):
    assert_recommended(recommend(fx.user(*allergens)), "potato_salt")


@pytest.mark.parametrize("allergens", [("shrimp",), ("crustacean_bundle",)], ids=["새우", "갑각류"])
def test_sibling_seafood_not_excluded(recommend, allergens):
    # 새우와 오징어는 둘 다 해산물이지만 새우 알레르기가 오징어로 번지지 않는다
    assert_recommended(recommend(fx.user(*allergens)), "squid_stirfry")


@pytest.mark.parametrize("allergens", [("wheat",), ("soybean",)], ids=["밀", "대두"])
def test_pantry_staple_still_checked_even_if_user_lists_it(recommend, allergens):
    # 시나리오 6: 간장은 기본 양념이라 "보유"로 간주되고, 사용자가 직접 보유 재료로 넣어도 알레르기 판정은 그대로다
    result = recommend(fx.user(*allergens, pantry=fx.PANTRY | {"soy_sauce"}))
    assert_excluded(result, "soy_braised_potato", ExclusionReason.ALLERGEN, "soy_sauce")
    assert_recommended(result, "potato_salt")


def test_no_allergy_user_gets_every_recipe(recommend):
    # 대조군 전체: 알레르기 없는 사용자에게는 픽스처 레시피가 모두 추천 가능하다
    result = recommend(fx.NO_ALLERGY)
    for recipe in fx.RECIPES:
        assert_recommended(result, recipe.id)
