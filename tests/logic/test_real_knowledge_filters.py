"""실제 knowledge/ 파일 스모크: 새우 알레르기 사용자에게 김치·새우젓 레시피가 제외된다."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.model import ExclusionReason, Recipe, RecipeIngredient, RecommendRequest, UserContext
from kb import compile_paths
from tests.support.engine_fixtures import build_recommender

ROOT = Path(__file__).resolve().parents[2]


def _recipe(id: str, *lines: tuple[str, str]) -> Recipe:
    return Recipe(id, id, "한식", 1, 20, tuple(RecipeIngredient(n, i, r) for n, (i, r) in enumerate(lines, 1)))


RECIPES = [
    _recipe("kimchi_fried_rice", ("rice", "main"), ("kimchi", "sub")),
    _recipe("saeujeot_egg_steam", ("egg", "main"), ("saeujeot", "seasoning")),
    _recipe("pork_belly_grill", ("pork_belly", "main"), ("salt", "seasoning")),
]
PANTRY = frozenset({"rice", "kimchi", "egg", "pork_belly"})


@pytest.fixture(scope="module")
def recommender():
    return build_recommender(compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml"), RECIPES)


def test_shrimp_allergy_excludes_kimchi_and_saeujeot(recommender):
    result = recommender.recommend(UserContext(allergen_groups=frozenset({"shrimp"}), pantry=PANTRY), RecommendRequest())
    assert [i.recipe_id for i in result.items] == ["pork_belly_grill"]
    hits = {(e.recipe_id, e.reason, e.ingredient_id, e.certainty, e.via) for e in result.exclusions}
    assert hits == {
        ("kimchi_fried_rice", ExclusionReason.ALLERGEN, "kimchi", "possible", ("kimchi", "saeujeot", "shrimp_raw")),
        ("saeujeot_egg_steam", ExclusionReason.ALLERGEN, "saeujeot", "definite", ("saeujeot", "shrimp_raw")),
    }


def test_control_no_allergy_gets_all(recommender):
    result = recommender.recommend(UserContext(pantry=PANTRY), RecommendRequest())
    assert {i.recipe_id for i in result.items} == {r.id for r in RECIPES}
