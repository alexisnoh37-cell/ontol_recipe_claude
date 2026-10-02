"""시나리오 7: 알레르기가 여러 개면 모든 그룹이 함께 적용된다."""

from __future__ import annotations

import pytest

from engine.model import ExclusionReason
from tests.allergy import fixtures as fx
from tests.allergy.checks import assert_excluded, assert_recommended

# 그룹별로 제외되어야 할 (레시피, 걸린 재료)
BY_GROUP = {
    "egg": [("mayo_cucumber_salad", "mayonnaise"), ("cucumber_soup_egg_garnish", "egg")],
    "milk": [("butter_potato", "butter")],
    "shrimp": [("kimchi_fried_rice", "kimchi"), ("cabbage_saeujeot_soup", "saeujeot")],
    "wheat": [("pajeon", "buchimgaru"), ("gochujang_potato", "gochujang")],
    "nuts_bundle": [("walnut_roast", "walnut")],
}

COMBOS = [("egg", "milk"), ("shrimp", "wheat"), ("egg", "milk", "shrimp", "wheat", "nuts_bundle")]


@pytest.mark.parametrize("groups", COMBOS, ids=["+".join(c) for c in COMBOS])
def test_every_group_applies(recommend, groups):
    result = recommend(fx.user(*groups))
    for group in groups:
        for recipe_id, trigger in BY_GROUP[group]:
            assert_excluded(result, recipe_id, ExclusionReason.ALLERGEN, trigger)
    assert_recommended(result, "potato_salt")


def test_control_single_allergy_does_not_exclude_other_groups(recommend):
    # 계란 알레르기만 있으면 버터(우유) 레시피는 추천된다 → 조합 테스트가 그룹을 실제로 합쳐서 본다는 근거
    assert_recommended(recommend(fx.user("egg")), "butter_potato")
    assert_recommended(recommend(fx.user("milk")), "mayo_cucumber_salad")
