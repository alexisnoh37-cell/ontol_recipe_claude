"""시나리오 8(A2): 대체 안내가 알레르기·절대 불선호 재료를 제안하지 않는다.

버섯볶음은 식용유가 필요하고(볶음), 사용자에게는 식용유가 없고 버터가 있다.
지식에는 "식용유 → 버터(볶음)" 대체가 있다.
"""

from __future__ import annotations

import pytest

from engine.model import ExclusionReason
from tests.allergy import fixtures as fx
from tests.allergy.checks import assert_excluded, item, recommended_ids

RECIPE = "mushroom_stirfry_oil"


def suggested(result, recipe_id=RECIPE) -> set[tuple[str, str]]:
    return {(s.need_id, s.use_id) for s in item(result, recipe_id).substitutions}


def test_control_butter_suggested_without_allergy(recommend):
    # 대조군: 알레르기가 없으면 "식용유 대신 버터" 안내가 실제로 나온다
    assert ("cooking_oil", "butter") in suggested(recommend(fx.NO_ALLERGY))


def test_butter_not_suggested_to_milk_allergy(recommend):
    result = recommend(fx.user("milk"))
    assert "butter" not in {use for _, use in suggested(result)}


def test_butter_not_suggested_to_hard_dislike_milk(recommend):
    result = recommend(fx.user(preferences=(fx.hard_dislike("milk"),)))
    assert "butter" not in {use for _, use in suggested(result)}
    # 버터는 우유를 포함하므로 버터 레시피 자체도 제외된다(A4)
    assert_excluded(result, "butter_potato", ExclusionReason.HARD_DISLIKE_INGREDIENT, "butter")


def test_no_substitution_anywhere_hits_user_allergy(recommend, compiled):
    # 모든 추천 항목의 모든 대체 안내가 사용자 알레르기 closure 밖에 있어야 한다
    for groups in [("milk",), ("egg", "milk"), ("shrimp", "wheat", "milk")]:
        result = recommend(fx.user(*groups))
        assert result.items
        unsafe = set().union(*(compiled.closure_of(g).keys() for g in groups))
        for it in result.items:
            for s in it.substitutions:
                assert s.use_id not in unsafe, f"{groups} 사용자에게 {it.recipe_id}에서 {s.use_id}를 안내했습니다"


# --- 추가5: 대체재로만 후보가 되는 레시피 -------------------------------------
# 낙지볶음은 낙지가 필요한데 사용자에게 낙지가 없고 새우가 있다(낙지 → 새우, 볶음).


def test_control_substitute_only_match_without_allergy(recommend):
    # 대조군: 알레르기가 없으면 새우를 대체재로 써서 낙지볶음이 후보가 되고 안내도 나온다
    assert ("octopus", "shrimp_raw") in suggested(recommend(fx.NO_ALLERGY), "octopus_stirfry")


@pytest.mark.parametrize(
    "who",
    [fx.user("shrimp"), fx.user("crustacean_bundle"), fx.user(preferences=(fx.hard_dislike("shrimp_raw"),))],
    ids=["새우 알레르기", "갑각류 알레르기", "새우 절대 불선호"],
)
def test_unsafe_substitute_neither_matches_nor_is_suggested(recommend, who):
    result = recommend(who)
    # 낙지볶음을 후보로 만든 유일한 근거가 새우였으므로 추천되면 안 된다
    assert "octopus_stirfry" not in recommended_ids(result)
    for it in result.items:
        assert "shrimp_raw" not in {s.use_id for s in it.substitutions}
