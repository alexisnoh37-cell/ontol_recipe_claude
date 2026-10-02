"""레시피 시드(data/recipes/) 검사 (Phase 1-3, 검수 완료): 형식·어휘 검증, 구성, 검수표 최신 여부, 알레르기 스모크."""

from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

import pytest

from engine.model import ExclusionReason, RecommendRequest, UserContext
from kb import compile_paths
from kb.recipes import RecipeSeedError, load_recipe_specs, read_recipe_dir
from tests.support.engine_fixtures import build_recommender, recipe_from_spec

ROOT = Path(__file__).resolve().parents[2]
RECIPES_DIR = ROOT / "data" / "recipes"


@pytest.fixture(scope="module")
def ck():
    return compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")


@pytest.fixture(scope="module")
def specs(ck):
    return load_recipe_specs(ck, RECIPES_DIR, ROOT)


@pytest.fixture(scope="module")
def recommender(ck, specs):
    return build_recommender(ck, [recipe_from_spec(s) for s in specs])


def test_seed_validates_without_issues(specs):
    assert len(specs) == 50


def test_one_recipe_per_file_named_by_id():
    for where, item in read_recipe_dir(RECIPES_DIR, ROOT):
        assert Path(where).stem == item["id"], where


def test_cuisine_mix(specs):
    counts = Counter(s.cuisine for s in specs)
    assert counts["한식"] == 30
    assert sum(counts.values()) - counts["한식"] == 20
    assert {"일식", "양식", "중식"} <= set(counts)


def test_all_recipes_published_after_review(specs):
    # 1-3 사람 검수 완료(2026-10-03). 새 레시피는 draft로 넣고 검수 후 published로 바꾼다.
    assert {s.status for s in specs} == {"published"}
    assert {s.source for s in specs} == {"agent_draft"}


def test_review_fixes_1_3(specs):
    # 1-3 검수에서 선택 재료로 바꾼 것
    optional = {(s.id, i.ingredient) for s in specs for i in s.ingredients if i.optional}
    assert {("gyeranjjim", "saeujeot"), ("gyeran_mari", "carrot"), ("gyeran_mari", "green_onion"),
            ("doenjang_jjigae", "zucchini"), ("doenjang_jjigae", "potato"), ("kimchi_jjigae", "tofu")} <= optional


def test_every_recipe_is_complete(specs):
    for s in specs:
        assert s.taste is not None and s.difficulty is not None, s.id
        assert any(i.role == "main" and not i.optional for i in s.ingredients), f"{s.id}: 필수 주재료 없음"
        assert all(i.ingredient is not None for i in s.ingredients), f"{s.id}: 미매칭 재료"
        assert s.steps, s.id
        assert len({i.ingredient for i in s.ingredients}) == len(s.ingredients), f"{s.id}: 재료 중복"


def test_bad_seed_is_rejected(ck, tmp_path):
    (tmp_path / "bad.yaml").write_text(
        "id: bad\ntitle: 나쁜 예\ncuisine: 태국식\ncook_time_min: 10\nsource: test\n"
        "ingredients:\n  - {ingredient: seafood, raw_text: 해산물, role: main}\n", encoding="utf-8")
    with pytest.raises(RecipeSeedError) as exc:
        load_recipe_specs(ck, tmp_path)
    assert {i.code for i in exc.value.issues} == {"bad_vocab", "concept_usage"}


def test_review_table_is_up_to_date(ck, specs):
    spec = importlib.util.spec_from_file_location("make_recipe_review", ROOT / "scripts" / "make_recipe_review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    committed = (ROOT / "docs" / "review" / "recipes_review.md").read_text(encoding="utf-8")
    assert committed == module.render(ck, specs), "검수표가 최신이 아닙니다: uv run python scripts/make_recipe_review.py"


# --- 실제 시드 + 엔진 알레르기 스모크(기본 설정: published만 제공) ------------------------------------------------


ALL_PANTRY = frozenset({"kimchi", "egg", "pork_belly", "pasta", "tofu", "rice", "potato", "squid", "tomato_sauce"})


def test_kimchi_recipes_excluded_for_shrimp_allergy(recommender, specs):
    kimchi_recipes = {s.id for s in specs if any(i.ingredient == "kimchi" for i in s.ingredients)}
    assert kimchi_recipes == {"kimchi_jjigae", "kimchijeon", "budae_jjigae"}
    result = recommender.recommend(UserContext(allergen_groups=frozenset({"shrimp"}), pantry=ALL_PANTRY),
                                   RecommendRequest(limit=100))
    served = {i.recipe_id for i in result.items}
    assert served and not served & (kimchi_recipes | {"gyeranjjim", "haemul_pajeon"})
    reasons = {(e.recipe_id, e.ingredient_id, e.certainty) for e in result.exclusions if e.reason == ExclusionReason.ALLERGEN}
    assert ("kimchi_jjigae", "kimchi", "possible") in reasons
    assert ("gyeranjjim", "saeujeot", "definite") in reasons
    assert ("haemul_pajeon", "shrimp_raw", "definite") in reasons  # 선택 재료여도 제외


def test_milk_allergy_excludes_optional_cheese(recommender):
    result = recommender.recommend(UserContext(allergen_groups=frozenset({"milk"}), pantry=ALL_PANTRY),
                                   RecommendRequest(limit=100))
    served = {i.recipe_id for i in result.items}
    assert not served & {"tomato_pasta", "cream_pasta", "potato_gratin", "cheese_omelet"}
    assert not any("검수 전 레시피입니다" in i.notes for i in result.items)


def test_published_seed_served_by_default(recommender):
    result = recommender.recommend(UserContext(pantry=ALL_PANTRY), RecommendRequest(limit=100))
    assert len(result.items) >= 30
