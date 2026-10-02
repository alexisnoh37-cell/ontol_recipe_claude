"""추가1: 넓은 재료.

  - concept 노드(분류 전용, 예: 해산물)는 레시피 재료로 쓸 수 없다. 적재 전 검증에서 거부된다.
  - 중간 노드(예: 젓갈류)는 레시피에 쓸 수 있고, 하위 개념의 알레르기를 possible로 가져 제외된다.
"""

from __future__ import annotations

from engine.model import Recipe, RecipeIngredient
from tests.allergy import fixtures as fx
from tests.allergy.checks import assert_recommended
from tests.support.engine_fixtures import recipe_load_issue_codes


def _seafood_recipe(ingredient_id: str) -> Recipe:
    return Recipe("seafood_stirfry", "해물볶음", "한식", 1, 20, (
        RecipeIngredient(1, ingredient_id, "main", raw_text="해산물 200g"),
        RecipeIngredient(2, "salt", "seasoning", raw_text="소금 약간"),
    ))


def test_concept_node_recipe_rejected_at_load(compiled):
    assert "seafood" in compiled.concept_ids
    assert "concept_usage" in recipe_load_issue_codes(compiled, _seafood_recipe("seafood"))


def test_control_concrete_ingredient_recipe_accepted_at_load(compiled):
    assert recipe_load_issue_codes(compiled, _seafood_recipe("squid_raw")) == []


def test_control_intermediate_node_accepted_at_load(compiled):
    # 젓갈류는 concept가 아니므로 적재는 허용되고, 알레르기 판정은 엔진 제외로 처리된다
    jeotgal = next(r for r in fx.RECIPES if r.id == "jeotgal_cabbage_salad")
    assert recipe_load_issue_codes(compiled, jeotgal) == []


def test_intermediate_node_does_not_leak_to_unrelated_groups(recommend):
    # 젓갈류의 하위는 새우젓뿐이므로 오징어·조개류 알레르기에는 걸리지 않는다
    assert_recommended(recommend(fx.user("squid")), "jeotgal_cabbage_salad")
    assert_recommended(recommend(fx.user("shellfish")), "jeotgal_cabbage_salad")
