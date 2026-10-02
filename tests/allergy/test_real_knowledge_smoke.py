"""실제 knowledge/ 파일로 만든 스냅샷에서도 숨은 알레르기가 걸러진다 (부록 A: 스모크 1개)."""

from __future__ import annotations

from pathlib import Path

from engine.model import ExclusionReason, Recipe, RecipeIngredient, RecommendRequest, UserContext
from kb import compile_paths
from tests.allergy.checks import assert_excluded, assert_recommended
from tests.support.engine_fixtures import build_recommender

ROOT = Path(__file__).resolve().parents[2]

RECIPES = [
    Recipe("kimchi_stew", "김치찌개", "한식", 1, 20, (
        RecipeIngredient(1, "pork_belly", "main"),
        RecipeIngredient(2, "kimchi", "sub"),
        RecipeIngredient(3, "green_onion", "garnish"),
    )),
    Recipe("grilled_pork_belly", "삼겹살구이", "한식", 1, 20, (
        RecipeIngredient(1, "pork_belly", "main"),
        RecipeIngredient(2, "salt", "seasoning"),
    )),
]
PANTRY = frozenset({"pork_belly", "kimchi", "green_onion"})


def test_real_knowledge_kimchi_excluded_for_shrimp_allergy():
    ck = compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")
    rec = build_recommender(ck, RECIPES)
    req = RecommendRequest(limit=10)

    allergic = rec.recommend(UserContext(allergen_groups=frozenset({"shrimp"}), pantry=PANTRY), req)
    assert_excluded(allergic, "kimchi_stew", ExclusionReason.ALLERGEN, "kimchi")
    assert_recommended(allergic, "grilled_pork_belly")

    control = rec.recommend(UserContext(pantry=PANTRY), req)
    assert_recommended(control, "kimchi_stew")
