"""제약 필터 단위 테스트 (docs/plan.md 4-3, 7-2): 매운맛 한도, 필수 조리기구, 시간, 음식 종류, 입력 검증."""

from __future__ import annotations

import pytest

from engine.model import (
    ExclusionReason,
    Preference,
    RecommendRequest,
    TastePreference,
    UserContext,
)
from tests.logic.engine_kb import compile_logic_kb, recipe
from tests.support.engine_fixtures import build_recommender

RECIPES = [
    recipe("mild_onion", ("onion", "main")),
    recipe("spicy2_onion", ("onion", "main"), spicy=2),
    recipe("spicy3_onion", ("onion", "main"), spicy=3),
    recipe("spicy5_onion", ("onion", "main"), spicy=5),
    recipe("oven_onion", ("onion", "main"), equipment=("오븐",)),
    recipe("oven_pan_onion", ("onion", "main"), equipment=("오븐", "프라이팬")),
    recipe("long_onion", ("onion", "main"), cook_time_min=90),
    recipe("western_onion", ("onion", "main"), cuisine="양식"),
]
REQ = RecommendRequest(limit=100)
PANTRY = frozenset({"onion"})


@pytest.fixture(scope="module")
def recommender():
    return build_recommender(compile_logic_kb(), RECIPES)


def ids(result) -> set[str]:
    return {i.recipe_id for i in result.items}


def reasons(result, recipe_id) -> list[ExclusionReason]:
    return [e.reason for e in result.exclusions if e.recipe_id == recipe_id]


# --- 매운맛: max_level(hard)은 제외, preferred_level(soft)은 통과 ---------------------------------


def test_spicy_max_level_excludes_above_limit(recommender):
    user = UserContext(pantry=PANTRY, tastes=(TastePreference("spicy", max_level=2),))
    result = recommender.recommend(user, REQ)
    assert {"mild_onion", "spicy2_onion"} <= ids(result)  # 한도와 같으면 통과
    for recipe_id in ("spicy3_onion", "spicy5_onion"):
        assert recipe_id not in ids(result)
        assert reasons(result, recipe_id) == [ExclusionReason.SPICY_LIMIT]


def test_spicy_preferred_level_only_does_not_exclude(recommender):
    user = UserContext(pantry=PANTRY, tastes=(TastePreference("spicy", preferred_level=0),))
    result = recommender.recommend(user, REQ)
    assert {"spicy3_onion", "spicy5_onion"} <= ids(result)
    assert not [e for e in result.exclusions if e.reason == ExclusionReason.SPICY_LIMIT]


def test_spicy_limit_ignores_other_dimensions(recommender):
    user = UserContext(pantry=PANTRY, tastes=(TastePreference("salty", max_level=0),))
    assert "spicy5_onion" in ids(recommender.recommend(user, REQ))


# --- 필수 조리기구 -----------------------------------------------------------------------------


def test_missing_required_equipment_excludes(recommender):
    result = recommender.recommend(UserContext(pantry=PANTRY, equipment=frozenset({"프라이팬"})), REQ)
    assert "oven_onion" not in ids(result)
    oven = [e for e in result.exclusions if e.recipe_id == "oven_onion"]
    assert [(e.reason, e.target) for e in oven] == [(ExclusionReason.EQUIPMENT, "오븐")]
    assert reasons(result, "oven_pan_onion") == [ExclusionReason.EQUIPMENT]
    assert "mild_onion" in ids(result)  # 필수 조리기구가 없는 레시피는 영향 없음


def test_owned_equipment_passes(recommender):
    result = recommender.recommend(UserContext(pantry=PANTRY, equipment=frozenset({"오븐", "프라이팬"})), REQ)
    assert {"oven_onion", "oven_pan_onion"} <= ids(result)


# --- 시간, 음식 종류 ---------------------------------------------------------------------------


def test_time_excluded_only_when_hard(recommender):
    user = UserContext(pantry=PANTRY)
    soft = recommender.recommend(user, RecommendRequest(limit=100, max_time_min=30))
    assert "long_onion" in ids(soft)
    hard = recommender.recommend(user, RecommendRequest(limit=100, max_time_min=30, time_is_hard=True))
    assert reasons(hard, "long_onion") == [ExclusionReason.TIME]
    assert "mild_onion" in ids(hard)


def test_hard_disliked_cuisine_excluded(recommender):
    user = UserContext(pantry=PANTRY, preferences=(Preference("cuisine", "양식", -1, 1.0, is_hard=True),))
    result = recommender.recommend(user, REQ)
    assert reasons(result, "western_onion") == [ExclusionReason.HARD_DISLIKE_CUISINE]
    soft = UserContext(pantry=PANTRY, preferences=(Preference("cuisine", "양식", -1, 1.0),))
    assert "western_onion" in ids(recommender.recommend(soft, REQ))  # soft 불선호는 1-2 점수에서 감점


# --- 입력 검증: 모르는 제약은 조용히 무시하지 않는다 ----------------------------------------------


def test_unknown_allergen_group_rejected(recommender):
    with pytest.raises(ValueError, match="알레르기 그룹"):
        recommender.recommend(UserContext(pantry=PANTRY, allergen_groups=frozenset({"no_such_group"})), REQ)


def test_unknown_hard_dislike_ingredient_rejected(recommender):
    user = UserContext(pantry=PANTRY, preferences=(Preference("ingredient", "no_such", -1, 1.0, is_hard=True),))
    with pytest.raises(ValueError, match="절대 불선호"):
        recommender.recommend(user, REQ)


def test_allergen_group_preference_is_treated_as_allergy():
    # user_preference(target_type=allergen_group)로 와도 UserContext.allergen_groups와 똑같이 제외한다
    rec = build_recommender(compile_logic_kb(), [recipe("egg_onion", ("onion", "main"), ("egg", "garnish"))])
    user = UserContext(pantry=PANTRY, preferences=(Preference("allergen_group", "egg", -1, 1.0, is_hard=True),))
    result = rec.recommend(user, REQ)
    assert reasons(result, "egg_onion") == [ExclusionReason.ALLERGEN]


def test_unknown_recipe_ingredient_id_is_unmapped_for_allergic_user():
    rec = build_recommender(compile_logic_kb(), [recipe("odd_onion", ("onion", "main"), ("not_in_kb", "seasoning"))])
    allergic = rec.recommend(UserContext(pantry=PANTRY, allergen_groups=frozenset({"egg"})), REQ)
    found = [e for e in allergic.exclusions if e.recipe_id == "odd_onion"]
    assert [(e.reason, e.ingredient_id) for e in found] == [(ExclusionReason.UNMAPPED_INGREDIENT, "not_in_kb")]
    assert "odd_onion" in ids(rec.recommend(UserContext(pantry=PANTRY), REQ))
