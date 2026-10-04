"""순두부(soft_tofu) 관계 (data-1, 2026-10-04 is_a tofu 결정): 실제 knowledge·레시피 시드로 제외 판정을 고정한다.

순두부찌개는 검수 전(draft)이라 draft도 제공하는 엔진으로 검사한다(필터는 published와 똑같이 적용됨).
레시피가 후보가 되도록 순두부·두부를 보유로 넣는다(후보가 아니면 제외 기록이 남지 않음).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.model import ExclusionReason, Preference, RecommendRequest, UserContext
from kb import compile_paths
from kb.recipes import load_recipe_specs
from tests.support.engine_fixtures import build_recommender, recipe_from_spec

ROOT = Path(__file__).resolve().parents[2]
PANTRY = frozenset({"soft_tofu", "tofu"})
TOFU_DISHES = {"doenjang_jjigae", "dubu_jorim", "mapo_tofu"}


@pytest.fixture(scope="module")
def ck():
    return compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")


@pytest.fixture(scope="module")
def engine(ck):
    specs = load_recipe_specs(ck, ROOT / "data" / "recipes", ROOT)
    return build_recommender(ck, [recipe_from_spec(s) for s in specs], serve_draft_recipes=True)


def excluded(engine, user: UserContext, reason: ExclusionReason) -> dict[str, set[tuple[str, str]]]:
    result = engine.recommend(user, RecommendRequest(limit=1000))
    served = {i.recipe_id for i in result.items}
    out: dict[str, set[tuple[str, str]]] = {}
    for e in result.exclusions:
        if e.reason == reason:
            assert e.recipe_id not in served
            out.setdefault(e.recipe_id, set()).add((e.ingredient_id, e.target))
    return out


def test_soft_tofu_is_a_tofu(ck):
    assert ck.contains_of("soft_tofu")["tofu"].certainty == "definite"
    assert ck.contains_of("soft_tofu")["soybean"].certainty == "definite"


def test_hard_dislike_tofu_excludes_sundubu_jjigae(engine):
    user = UserContext(pantry=PANTRY, preferences=(Preference("ingredient", "tofu", -1, 1.0, True),))
    hits = excluded(engine, user, ExclusionReason.HARD_DISLIKE_INGREDIENT)
    assert ("soft_tofu", "tofu") in hits["sundubu_jjigae"]
    assert TOFU_DISHES <= set(hits)


def test_hard_dislike_soft_tofu_excludes_sundubu_jjigae(engine):
    user = UserContext(pantry=PANTRY, preferences=(Preference("ingredient", "soft_tofu", -1, 1.0, True),))
    hits = excluded(engine, user, ExclusionReason.HARD_DISLIKE_INGREDIENT)
    assert ("soft_tofu", "soft_tofu") in hits["sundubu_jjigae"]


def test_hard_dislike_soft_tofu_also_excludes_tofu_dishes(engine):
    # 사람 결정(2026-10-04): 지금 동작 유지. plan.md 부록 C의 contains 규칙 "x 자신에 is_a 하위 개념이 있으면
    # 그 하위 개념도 possible로 포함"에 따라 두부(tofu)는 순두부(soft_tofu)를 포함 가능(경로 tofu → soft_tofu)으로 본다.
    # 그래서 "순두부" 절대 불선호는 순두부찌개뿐 아니라 두부를 쓰는 레시피도 제외한다.
    user = UserContext(pantry=PANTRY, preferences=(Preference("ingredient", "soft_tofu", -1, 1.0, True),))
    hits = excluded(engine, user, ExclusionReason.HARD_DISLIKE_INGREDIENT)
    assert "sundubu_jjigae" in hits
    for recipe_id in TOFU_DISHES:
        assert ("tofu", "soft_tofu") in hits[recipe_id], recipe_id


def test_soybean_allergy_excludes_sundubu_jjigae(engine):
    user = UserContext(pantry=PANTRY, allergen_groups=frozenset({"soybean"}))
    hits = excluded(engine, user, ExclusionReason.ALLERGEN)
    assert ("soft_tofu", "soybean") in hits["sundubu_jjigae"]
