"""시나리오 9(A4): "새우 못 먹음"(알레르기가 아닌 절대 불선호)은 파생·포함 재료까지 제외한다."""

from __future__ import annotations

import pytest

from engine.model import ExclusionReason
from tests.allergy import fixtures as fx
from tests.allergy.checks import assert_excluded, assert_recommended

NO_SHRIMP = fx.user(preferences=(fx.hard_dislike("shrimp_raw"),))

CASES = [
    ("shrimp_stirfry", "shrimp_raw"),
    ("cabbage_saeujeot_soup", "saeujeot"),
    ("kimchi_fried_rice", "kimchi"),
]


@pytest.mark.parametrize(("recipe_id", "trigger"), CASES, ids=[c[0] for c in CASES])
def test_hard_dislike_excludes_derived(recommend, recipe_id, trigger):
    assert_excluded(recommend(NO_SHRIMP), recipe_id, ExclusionReason.HARD_DISLIKE_INGREDIENT, trigger)


def test_hard_dislike_is_not_treated_as_allergy(recommend):
    # 알레르기가 없으므로 ALLERGEN 사유도, 미매칭 재료 제외도 없어야 한다
    result = recommend(NO_SHRIMP)
    assert not [e for e in result.exclusions if e.reason == ExclusionReason.ALLERGEN]


def test_control_hard_dislike_keeps_siblings_and_safe(recommend):
    result = recommend(NO_SHRIMP)
    assert_recommended(result, "squid_stirfry")  # 같은 해산물이지만 새우가 아님
    assert_recommended(result, "potato_salt")


@pytest.mark.parametrize(("recipe_id", "trigger"), CASES, ids=[c[0] for c in CASES])
def test_control_recommended_without_dislike(recommend, recipe_id, trigger):
    assert_recommended(recommend(fx.NO_ALLERGY), recipe_id)
