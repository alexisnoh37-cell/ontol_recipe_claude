"""레시피·사용자 데이터 검증 (docs/plan.md 5-4, A1)."""

from __future__ import annotations

import pytest

from kb.datacheck import check_pantry, check_preferences, check_recipes
from tests.support.kb_builders import compile_basics


@pytest.fixture(scope="module")
def ck():
    return compile_basics()


def recipe(**overrides):
    base = {
        "id": "kimchi_stew",
        "title": "김치찌개",
        "cuisine": "한식",
        "difficulty": 1,
        "cook_time_min": 20,
        "source": "agent_draft",
        "status": "published",
        "ingredients": [
            {"ingredient": "kimchi", "raw_text": "김치 1/4포기", "role": "main"},
            {"ingredient": "salt", "raw_text": "소금 약간", "role": "seasoning"},
        ],
        "taste": {"spicy": 3, "salty": 3, "sweet": 0, "sour": 2, "umami": 3, "savory": 2},
        "equipment": ["냄비"],
        "steps": [{"text": "끓인다", "technique": "끓이기"}],
    }
    base.update(overrides)
    return base


def codes(issues):
    return [i.code for i in issues]


def test_valid_recipe_passes(ck):
    assert check_recipes(ck, [("r.yaml", recipe())]) == []


def test_concept_node_as_recipe_ingredient_fails(ck):
    bad = recipe(ingredients=[{"ingredient": "seafood", "raw_text": "해산물 200g", "role": "main"}])
    issues = check_recipes(ck, [("r.yaml", bad)])
    assert codes(issues) == ["concept_usage"]
    assert "seafood" in issues[0].message


def test_intermediate_node_is_allowed_as_recipe_ingredient(ck):
    ok = recipe(ingredients=[{"ingredient": "jeotgal", "raw_text": "젓갈 1큰술", "role": "seasoning"}])
    assert check_recipes(ck, [("r.yaml", ok)]) == []


def test_unmapped_ingredient_fails(ck):
    bad = recipe(ingredients=[{"ingredient": None, "raw_text": "비법 소스", "role": "sub"}])
    assert codes(check_recipes(ck, [("r.yaml", bad)])) == ["unmapped"]


def test_unknown_ingredient_fails(ck):
    bad = recipe(ingredients=[{"ingredient": "dragon_fruit", "raw_text": "용과", "role": "main"}])
    assert codes(check_recipes(ck, [("r.yaml", bad)])) == ["bad_ref"]


def test_vocab_checked(ck):
    bad = recipe(cuisine="멕시코식", equipment=["훈연기"], steps=[{"text": "x", "technique": "훈연"}])
    assert codes(check_recipes(ck, [("r.yaml", bad)])) == ["bad_vocab"] * 3


def test_published_requires_taste_and_difficulty(ck):
    bad = recipe(taste=None, difficulty=None)
    assert codes(check_recipes(ck, [("r.yaml", bad)])) == ["published_incomplete"] * 2
    draft = recipe(taste=None, difficulty=None, status="draft")
    assert check_recipes(ck, [("r.yaml", draft)]) == []


def test_unknown_recipe_key_fails(ck):
    assert codes(check_recipes(ck, [("r.yaml", recipe(calories=500))])) == ["unknown_key"]


def test_duplicate_recipe_id_fails(ck):
    assert codes(check_recipes(ck, [("a.yaml", recipe()), ("b.yaml", recipe())])) == ["duplicate_id"]


def test_concept_in_user_pantry_fails(ck):
    assert codes(check_pantry(ck, [(1, "seafood"), (1, "kimchi"), (2, "ghost")])) == ["concept_usage", "bad_ref"]


def test_preference_targets_must_exist(ck):
    rows = [
        (1, "ingredient", "seafood"),  # 선호는 concept에도 가능
        (1, "cuisine", "한식"),
        (1, "allergen_group", "crustacean_bundle"),
        (1, "ingredient", "ghost"),
        (1, "cuisine", "멕시코식"),
        (1, "allergen_group", "sesame"),
    ]
    assert codes(check_preferences(ck, rows)) == ["bad_ref"] * 3
