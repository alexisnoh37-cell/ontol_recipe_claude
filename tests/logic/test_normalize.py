"""입력 정규화 단위 테스트 (docs/plan.md 4-1, 7-2): 동의어, 공백, concept, 미매칭."""

from __future__ import annotations

import pytest

from engine.model import RecommendRequest, UserContext
from engine.normalize import normalize_term, resolve_terms
from kb.text import normalize_term as kb_normalize_term
from tests.logic.engine_kb import compile_logic_kb, recipe
from tests.support.engine_fixtures import build_recommender, snapshot_from_compiled


@pytest.fixture(scope="module")
def compiled():
    return compile_logic_kb()


@pytest.fixture(scope="module")
def snapshot(compiled):
    return snapshot_from_compiled(compiled)


@pytest.mark.parametrize("text", ["다진 마늘", "  다진마늘 ", "Olive Oil", "ｅｇｇ", "계란", "\t달걀\n"])
def test_engine_normalization_matches_compiler(text):
    # 컴파일러가 만든 alias_norm과 같은 키를 만들어야 별칭 매핑이 맞는다
    assert normalize_term(text) == kb_normalize_term(text)


def test_synonym_maps_to_canonical_id(snapshot):
    assert resolve_terms(snapshot, ["달걀"]).ids == {"egg"}
    assert resolve_terms(snapshot, ["계란"]).ids == {"egg"}
    assert resolve_terms(snapshot, ["다진마늘"]).ids == {"garlic"}


def test_unmapped_and_concept_terms_are_reported(snapshot):
    result = resolve_terms(snapshot, ["달걀", "용과", "육류", ""])
    assert result.ids == {"egg"}
    assert result.unmapped == ("용과",)
    assert result.concepts == ("육류",)


def test_synonym_input_matches_recipe(compiled, snapshot):
    # "달걀" 입력이 "계란" 레시피와 매칭된다
    rec = build_recommender(compiled, [recipe("egg_roll", ("egg", "main"), ("salt", "seasoning"))])
    pantry = resolve_terms(snapshot, ["달걀"]).ids
    items = rec.recommend(UserContext(pantry=pantry), RecommendRequest()).items
    assert [(i.recipe_id, i.missing) for i in items] == [("egg_roll", ())]
