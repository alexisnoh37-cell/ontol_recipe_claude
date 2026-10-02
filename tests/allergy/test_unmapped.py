"""7-1: 정규 id로 매핑되지 않은 재료가 있는 레시피는 알레르기 사용자에게 나오지 않는다."""

from __future__ import annotations

import pytest

from engine.model import ExclusionReason
from tests.allergy import fixtures as fx
from tests.allergy.checks import assert_excluded, assert_recommended


@pytest.mark.parametrize("allergens", [("egg",), ("shrimp",), ("nuts_bundle",)], ids=["난류", "새우", "견과류"])
def test_unmapped_recipe_excluded_for_allergic_user(recommend, allergens):
    result = recommend(fx.user(*allergens))
    assert_excluded(result, "mushroom_secret_sauce", ExclusionReason.UNMAPPED_INGREDIENT)
    assert_recommended(result, "potato_salt")


def test_control_unmapped_recipe_recommended_without_allergy(recommend):
    assert_recommended(recommend(fx.NO_ALLERGY), "mushroom_secret_sauce")
