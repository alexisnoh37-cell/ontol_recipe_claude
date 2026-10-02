"""그래프 확장 불변식 (docs/plan.md 부록 C 마지막 줄)."""

from __future__ import annotations

import pytest

from kb import compile
from tests.support.kb_builders import compile_basics, ing, korean_basics, sources


@pytest.fixture(scope="module")
def ck():
    return compile_basics()


def test_saeujeot_in_shrimp_closure_definite(ck):
    row = ck.closure_of("shrimp")["saeujeot"]
    assert row.certainty == "definite"
    assert row.via == ("saeujeot", "shrimp_raw")


def test_kimchi_in_shrimp_closure_possible(ck):
    row = ck.closure_of("shrimp")["kimchi"]
    assert row.certainty == "possible"
    assert row.via == ("kimchi", "saeujeot", "shrimp_raw")


def test_doenjang_soybean_definite_wheat_possible(ck):
    assert ck.closure_of("soybean")["doenjang"].certainty == "definite"
    assert ck.closure_of("wheat")["doenjang"].certainty == "possible"


def test_shrimp_does_not_contain_squid(ck):
    assert "squid_raw" not in ck.contains_of("shrimp_raw")
    assert "shrimp_raw" not in ck.closure_of("squid")
    assert "squid_raw" not in ck.closure_of("shrimp")


def test_siblings_do_not_leak_through_parent(ck):
    # 새우젓 → 젓갈류 → 해산물까지 올라가도 오징어로 내려가지 않는다
    assert "squid_raw" not in ck.contains_of("saeujeot")
    assert "saeujeot" not in ck.closure_of("squid")
    assert "kimchi" not in ck.closure_of("squid")


def test_intermediate_node_gets_descendant_allergen_as_possible(ck):
    # 레시피가 "젓갈류"를 쓰면 새우젓의 새우 알레르기가 새지 않아야 한다(A1)
    row = ck.closure_of("shrimp")["jeotgal"]
    assert row.certainty == "possible"
    assert row.via == ("jeotgal", "saeujeot", "shrimp_raw")


def test_source_itself_in_closure(ck):
    assert ck.closure_of("shrimp")["shrimp_raw"].certainty == "definite"
    assert ck.closure_of("shrimp")["shrimp_raw"].via == ("shrimp_raw",)


def test_unrelated_ingredient_not_in_any_closure(ck):
    assert all(r.ingredient_id != "salt" for r in ck.allergen_closure)


def test_bundle_is_union_of_members(ck):
    bundle = ck.closure_of("crustacean_bundle")
    assert set(bundle) == set(ck.closure_of("shrimp")) | set(ck.closure_of("crab"))
    assert bundle["kimchi"].certainty == "possible"


def test_contains_follows_is_a_up_and_derived_from(ck):
    kimchi = ck.contains_of("kimchi")
    assert kimchi["saeujeot"].certainty == "possible"
    assert kimchi["shrimp_raw"].certainty == "possible"
    assert kimchi["jeotgal"].certainty == "possible"  # 새우젓 is_a 젓갈류
    saeujeot = ck.contains_of("saeujeot")
    assert saeujeot["jeotgal"].certainty == "definite"
    assert saeujeot["seafood"].certainty == "definite"


def test_ancestors_with_min_depth(ck):
    anc = {(a.ingredient_id, a.ancestor_id): a.depth for a in ck.ancestors}
    assert anc[("saeujeot", "jeotgal")] == 1
    assert anc[("saeujeot", "seafood")] == 2
    assert ("shrimp_raw", "jeotgal") not in anc


def test_definite_path_beats_possible_path():
    items = korean_basics() + [
        # 김치2는 새우젓(possible)과 새우(definite)를 둘 다 원천으로 가진다
        ing("kimchi2", derived_from=[{"id": "saeujeot", "certainty": "possible"}, "shrimp_raw"], is_processed=True),
    ]
    ck = compile(sources(items))
    row = ck.closure_of("shrimp")["kimchi2"]
    assert row.certainty == "definite"
    assert row.via == ("kimchi2", "shrimp_raw")


def test_possible_allergen_on_source_propagates_as_possible():
    items = korean_basics() + [
        ing("mystery_sauce", allergens=[{"group": "egg", "certainty": "possible"}]),
        ing("dressing", derived_from=["mystery_sauce"], is_processed=True),
    ]
    ck = compile(sources(items))
    assert ck.closure_of("egg")["dressing"].certainty == "possible"


def test_descendant_of_derived_source_is_possible():
    # 소스가 "젓갈류"(넓은 재료)로 만들어지면 그 하위 새우젓의 새우도 possible로 따라간다
    items = korean_basics() + [
        ing("jeotgal_sauce", derived_from=["jeotgal"], is_processed=True),
    ]
    ck = compile(sources(items))
    row = ck.closure_of("shrimp")["jeotgal_sauce"]
    assert row.certainty == "possible"
    assert row.via == ("jeotgal_sauce", "jeotgal", "saeujeot", "shrimp_raw")


def test_compile_is_deterministic_regardless_of_input_order():
    a = compile(sources(korean_basics()))
    b = compile(sources(list(reversed(korean_basics()))))
    strip = lambda d: {k: v for k, v in d.items() if k != "source_hash"}  # noqa: E731
    assert strip(a.to_dict()) == strip(b.to_dict())


def test_pantry_staple_flag_from_config():
    ck = compile_basics(staples=["salt", "doenjang"])
    flags = {i.id: i.is_pantry_staple for i in ck.ingredients}
    assert flags["salt"] and flags["doenjang"] and not flags["kimchi"]


def test_aliases_include_primary_name_and_forms():
    items = korean_basics() + [ing("garlic", name="마늘", aliases=["깐마늘", {"text": "다진 마늘", "form": "minced"}])]
    ck = compile(sources(items))
    by_norm = {a.alias_norm: a for a in ck.aliases}
    assert by_norm["마늘"].is_primary and by_norm["마늘"].ingredient_id == "garlic"
    assert by_norm["다진마늘"].form == "minced" and by_norm["다진마늘"].alias == "다진 마늘"
    assert by_norm["김치"].ingredient_id == "kimchi"
