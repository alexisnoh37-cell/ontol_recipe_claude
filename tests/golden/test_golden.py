"""골든셋 구조와 평가기 검사 (Phase 1-4).

기대 레시피(expected_top3)는 사람이 채운다. 페르소나가 올바른 데이터인지, 평가기 계산이 맞는지,
결과가 안전 규칙을 지키는지 본다. 1-5부터 상위 3개 적중률 회귀 기준(MIN_HIT_RATE)을 둔다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from engine.model import RecommendItem
from kb import compile_paths
from kb.recipes import load_recipe_specs
from tests.golden.golden import build_engine, evaluate, hit_rate, load_personas, overall, render_draft

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def ck():
    return compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")


@pytest.fixture(scope="module")
def personas():
    return load_personas()


@pytest.fixture(scope="module")
def results(personas):
    recommender, _ = build_engine()
    return evaluate(recommender, personas)


def test_eight_personas_with_unique_ids(personas):
    assert len(personas) == 8
    assert len({p.id for p in personas}) == 8


def test_required_persona_kinds(personas):
    by_id = {p.id: p for p in personas}
    liked = lambda p, c: any(x.target_type == "cuisine" and x.target_id == c and x.polarity > 0 for x in p.user.preferences)  # noqa: E731
    assert liked(by_id["korean_lover"], "한식")
    assert by_id["beginner"].user.skill_level == 1
    assert len(by_id["multi_allergy"].user.allergen_groups) >= 2
    assert any(t.dimension == "spicy" and t.max_level is not None and t.max_level <= 1 for t in by_id["low_spice"].user.tastes)
    assert liked(by_id["western_lover"], "양식") and liked(by_id["japanese_lover"], "일식")
    assert len(by_id["few_ingredients"].user.pantry) == 5


def test_persona_data_is_valid(ck, personas):
    groups = {g.id for g in ck.allergen_groups}
    for p in personas:
        assert 5 <= len(p.user.pantry) <= 8, p.id
        assert p.user.pantry <= ck.ingredient_ids and not p.user.pantry & ck.concept_ids, p.id
        assert p.user.allergen_groups <= groups, p.id
        assert p.user.equipment <= set(ck.vocab["equipment"]), p.id
        for pref in p.user.preferences:
            valid = ck.ingredient_ids if pref.target_type == "ingredient" else set(ck.vocab["cuisines"])
            assert pref.target_id in valid, (p.id, pref.target_id)


def test_expected_recipes_exist_when_filled(ck, personas):
    recipe_ids = {r.id for r in load_recipe_specs(ck, ROOT / "data" / "recipes", ROOT)}
    for p in personas:
        assert len(p.expected_top3) <= 3, p.id
        assert set(p.expected_top3) <= recipe_ids, p.id


def test_every_persona_gets_at_least_five_results(results):
    for r in results:
        assert len(r.result.items) >= 5, r.persona.id
        assert all(set(i.breakdown) == set("IKTPDM") for i in r.result.items)


def test_results_respect_allergies_and_spicy_limit(ck, results):
    closure: dict[str, set[str]] = {}
    for row in ck.allergen_closure:
        closure.setdefault(row.allergen_group_id, set()).add(row.ingredient_id)
    specs = {r.id: r for r in load_recipe_specs(ck, ROOT / "data" / "recipes", ROOT)}
    for r in results:
        unsafe = set().union(*(closure[g] for g in r.persona.user.allergen_groups)) if r.persona.user.allergen_groups else set()
        limits = [t.max_level for t in r.persona.user.tastes if t.dimension == "spicy" and t.max_level is not None]
        for item in r.result.items:
            spec = specs[item.recipe_id]
            assert not {i.ingredient for i in spec.ingredients} & unsafe, (r.persona.id, item.recipe_id)
            if limits:
                assert spec.taste.spicy <= min(limits), (r.persona.id, item.recipe_id)


def _items(*ids: str) -> tuple[RecommendItem, ...]:
    return tuple(RecommendItem(i, i, 0.0, {}) for i in ids)


def test_hit_rate_calculation():
    items = _items("a", "b", "c", "d")
    assert hit_rate((), items) is None
    assert hit_rate(("a",), items) == 1.0
    assert hit_rate(("d",), items) == 0.0  # 4위는 상위 3개 밖
    assert hit_rate(("a", "d"), items) == 0.5
    assert hit_rate(("a", "b", "c"), items) == 1.0


def test_overall_ignores_unfilled(results):
    assert overall(results) is None or 0.0 <= overall(results) <= 1.0
    if all(not r.persona.expected_top3 for r in results):
        assert overall(results) is None


def test_draft_renders_all_personas(results):
    text = render_draft(results, {})
    for r in results:
        assert f"`{r.persona.id}`" in text


# 1-5: 1-4 조정 후 0.88. 남은 불일치 3건은 허용(docs/progress.md "1-4 허용된 불일치").
# 가중치·데이터를 바꿔 이 아래로 떨어지면 실패한다. 기준을 바꾸려면 사람 승인이 필요하다.
MIN_HIT_RATE = 0.85


def test_top3_hit_rate_regression(results):
    rate = overall(results)
    detail = ", ".join(f"{r.persona.id} {r.hit_rate:.2f}" for r in results if r.hit_rate is not None)
    assert rate is not None and rate >= MIN_HIT_RATE, f"골든셋 상위 3개 적중률 {rate} < {MIN_HIT_RATE} ({detail})"
