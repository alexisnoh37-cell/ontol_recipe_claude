"""후보 생성 단위 테스트 (docs/plan.md 4-2, 7-2): 상위 개념 매칭 방향, 대체재 context, 부족 재료."""

from __future__ import annotations

import pytest

from engine.model import RecommendRequest, SubstitutionNote, UserContext
from tests.logic.engine_kb import compile_logic_kb, recipe
from tests.support.engine_fixtures import build_recommender

RECIPES = [
    recipe("pork_stew", ("pork", "main"), ("salt", "seasoning")),
    recipe("belly_onion", ("pork_belly", "main"), ("onion", "sub")),
    recipe("belly_only", ("pork_belly", "main")),
    recipe("tofu_onion", ("onion", "main"), ("tofu", "sub"), ("egg", "garnish", True)),
    recipe("salt_only", ("salt", "main")),
    recipe("onion_stirfry", ("onion", "main"), ("cooking_oil", "sub"), techniques=("볶음",)),
    recipe("onion_grill", ("onion", "main"), ("cooking_oil", "sub"), techniques=("구이",)),
]
REQ = RecommendRequest(limit=100)


@pytest.fixture(scope="module")
def recommender():
    return build_recommender(compile_logic_kb(), RECIPES)


def run(recommender, *pantry: str):
    return {i.recipe_id: i for i in recommender.recommend(UserContext(pantry=frozenset(pantry)), REQ).items}


# --- 상위 개념 매칭 방향 -------------------------------------------------------------------------


def test_owned_child_matches_parent_recipe(recommender):
    # 삼겹살 보유 → "돼지고기" 레시피가 후보이고 돼지고기는 부족 재료가 아니다
    items = run(recommender, "pork_belly")
    assert "pork_stew" in items
    assert items["pork_stew"].missing == ()


def test_owned_parent_does_not_match_child_recipe(recommender):
    # 돼지고기 보유 → "삼겹살"만 필요한 레시피는 후보가 아니다
    items = run(recommender, "pork", "onion")
    assert "belly_only" not in items
    # 다른 재료(양파)로 후보가 된 레시피에서는 삼겹살이 부족 재료로 표시된다
    assert items["belly_onion"].missing == ("pork_belly",)


def test_concept_in_pantry_is_ignored(recommender):
    # concept(육류)는 보유 재료로 쓸 수 없다(A1). 육류 보유로 돼지고기 레시피가 매칭되지 않는다
    assert "pork_stew" not in run(recommender, "meat")


# --- 부족 재료와 기본 양념 ------------------------------------------------------------------------


def test_missing_lists_unowned_required_but_not_optional_or_staples(recommender):
    items = run(recommender, "onion")
    tofu = items["tofu_onion"]
    assert tofu.missing == ("tofu",)  # 선택 재료 계란은 missing이 아님
    assert any("선택 재료" in n for n in tofu.notes)
    assert run(recommender, "pork")["pork_stew"].missing == ()  # 소금은 기본 양념이라 보유로 간주


def test_staple_alone_makes_candidate(recommender):
    # 기본 양념은 보유로 간주하므로 main이 기본 양념인 레시피는 보유 재료가 없어도 후보다
    assert "salt_only" in run(recommender)


# --- 대체재: technique context -------------------------------------------------------------------


def test_substitute_applies_only_in_matching_context(recommender):
    items = run(recommender, "onion", "butter")
    assert items["onion_stirfry"].substitutions == (SubstitutionNote("cooking_oil", "butter"),)
    assert items["onion_stirfry"].missing == ()
    # 구이 레시피에는 "식용유 → 버터(볶음)" 대체가 성립하지 않는다
    assert items["onion_grill"].substitutions == ()
    assert items["onion_grill"].missing == ("cooking_oil",)


def test_substitute_not_offered_to_allergic_user(recommender):
    user = UserContext(pantry=frozenset({"onion", "butter"}), allergen_groups=frozenset({"milk"}))
    items = {i.recipe_id: i for i in recommender.recommend(user, REQ).items}
    assert items["onion_stirfry"].substitutions == ()
    assert items["onion_stirfry"].missing == ("cooking_oil",)
