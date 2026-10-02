"""실제 knowledge/ 파일 스모크 테스트. 데이터를 고친 뒤에도 핵심 불변식이 유지되는지 본다."""

from __future__ import annotations

from pathlib import Path

import pytest

from kb import compile_paths

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def ck():
    return compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")


def test_real_knowledge_compiles(ck):
    assert len(ck.ingredients) > 0


def test_hidden_allergens(ck):
    shrimp = ck.closure_of("shrimp")
    assert shrimp["saeujeot"].certainty == "definite"
    assert shrimp["kimchi"].certainty == "possible"
    assert ck.closure_of("soybean")["doenjang"].certainty == "definite"
    assert ck.closure_of("wheat")["doenjang"].certainty == "possible"
    assert ck.closure_of("wheat")["soy_sauce"].certainty == "definite"
    assert ck.closure_of("egg")["mayonnaise"].certainty == "definite"
    assert ck.closure_of("peanut")["peanut_butter"].certainty == "definite"
    assert ck.closure_of("milk")["butter"].certainty == "definite"


def test_pantry_staples_resolve_and_garlic_renamed(ck):
    assert "garlic" in ck.pantry_staples
    assert "garlic_minced" not in ck.ingredient_ids
    staples = {i.id for i in ck.ingredients if i.is_pantry_staple}
    assert staples == set(ck.pantry_staples)


def test_garlic_minced_is_form_alias(ck):
    by_norm = {a.alias_norm: a for a in ck.aliases}
    assert by_norm["다진마늘"].ingredient_id == "garlic"
    assert by_norm["다진마늘"].form == "minced"


def test_ambiguous_alias_removed_and_soybean_oil_separate(ck):
    assert "파" not in {a.alias_norm for a in ck.aliases}
    by_norm = {a.alias_norm: a.ingredient_id for a in ck.aliases}
    assert by_norm["콩기름"] == "soybean_oil"
    assert ck.closure_of("soybean")["soybean_oil"].certainty == "possible"


def test_all_knowledge_is_draft(ck):
    assert all(i.status == "draft" for i in ck.ingredients)
    assert all(g.status == "draft" for g in ck.allergen_groups)
