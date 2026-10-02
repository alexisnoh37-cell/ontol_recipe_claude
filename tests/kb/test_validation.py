"""컴파일 실패 조건 (docs/plan.md 부록 C-2). 실패 시 오류를 모두 모아 보고한다."""

from __future__ import annotations

import pytest

from kb import KnowledgeError, compile
from tests.support.kb_builders import ing, korean_basics, sources


def compile_error(src) -> KnowledgeError:
    with pytest.raises(KnowledgeError) as exc:
        compile(src)
    return exc.value


def codes(err: KnowledgeError) -> list[str]:
    return [e.code for e in err.errors]


# --- 순환 -------------------------------------------------------------------


def test_is_a_cycle_fails():
    err = compile_error(sources([ing("a", is_a=["b"]), ing("b", is_a=["c"]), ing("c", is_a=["a"])]))
    cycle = [e for e in err.errors if e.code == "cycle"]
    assert len(cycle) == 1 and cycle[0].where == "is_a"
    assert "a → b → c → a" in cycle[0].message


def test_derived_from_cycle_fails():
    err = compile_error(sources([
        ing("a", derived_from=["b"], is_processed=True),
        ing("b", derived_from=["a"], is_processed=True),
    ]))
    assert [e.where for e in err.errors if e.code == "cycle"] == ["derived_from"]


def test_cycle_only_in_union_fails():
    # is_a만, derived_from만 보면 순환이 없지만 합치면 a → b → a
    err = compile_error(sources([ing("a", is_a=["b"]), ing("b", derived_from=["a"], is_processed=True)]))
    assert [e.where for e in err.errors if e.code == "cycle"] == ["is_a ∪ derived_from"]


def test_self_loop_fails():
    err = compile_error(sources([ing("a", is_a=["a"])]))
    assert "cycle" in codes(err)


# --- 알 수 없는 키 -----------------------------------------------------------


def test_unknown_key_in_ingredient_fails():
    err = compile_error(sources([ing("salt", is_pantry_staple=True)]))  # 확정 형식에서 삭제된 키
    assert codes(err) == ["unknown_key"]
    assert "is_pantry_staple" in err.errors[0].message


def test_old_derived_certainty_key_fails():
    err = compile_error(sources(korean_basics() + [ing("x", derived_from=["soybean"], is_processed=True, derived_certainty="possible")]))
    assert codes(err) == ["unknown_key"]


def test_unknown_key_in_nested_object_fails():
    err = compile_error(sources([ing("a", allergens=[{"group": "egg", "certainty": "definite", "amount": 1}])]))
    assert codes(err) == ["unknown_key"]


def test_unknown_key_in_other_files_fails():
    vocab = {"cuisines": [], "equipment": [], "techniques": [], "categories": [], "diets": []}
    subs = [{"from": "a", "to": "b", "status": "draft", "contxt": []}]
    src = sources([ing("a"), ing("b")], vocab=vocab, substitutes=subs,
                  groups=[{"id": "egg", "display_name": "계란", "status": "draft", "label": "x"}], bundles=[])
    err = compile_error(src)
    assert codes(err).count("unknown_key") == 3


# --- 별칭 충돌 ---------------------------------------------------------------


def test_alias_collision_between_ingredients_fails():
    err = compile_error(sources([ing("green_onion", name="대파", aliases=["파"]), ing("scallion", name="쪽파", aliases=["파"])]))
    assert codes(err) == ["alias_conflict"]
    assert "green_onion" in err.errors[0].message and "scallion" in err.errors[0].message


def test_alias_collision_after_normalization_fails():
    # 공백 제거 후 같은 문자열: "다진 마늘" vs 이름 "다진마늘"
    err = compile_error(sources([ing("garlic", name="마늘", aliases=["다진 마늘"]), ing("garlic_minced", name="다진마늘")]))
    assert codes(err) == ["alias_conflict"]


def test_alias_collision_with_name_case_insensitive_fails():
    err = compile_error(sources([ing("a", name="Olive Oil"), ing("b", name="b", aliases=["oliveoil"])]))
    assert codes(err) == ["alias_conflict"]


# --- 참조·의미 규칙 ----------------------------------------------------------


def test_missing_reference_fails():
    err = compile_error(sources([ing("a", is_a=["nope"], derived_from=["ghost"], is_processed=True)]))
    assert codes(err).count("bad_ref") == 2


def test_processed_without_source_fails():
    err = compile_error(sources([ing("a", is_processed=True)]))
    assert codes(err) == ["processed_without_source"]


def test_concept_with_allergens_fails():
    err = compile_error(sources([ing("seafood", kind="concept", allergens=[{"group": "shrimp", "certainty": "definite"}])]))
    assert codes(err) == ["concept_allergen"]


def test_allergen_must_be_base_group():
    err = compile_error(sources([ing("a", allergens=[{"group": "crustacean_bundle", "certainty": "definite"}])]))
    assert codes(err) == ["bad_ref"]


def test_concept_as_pantry_staple_fails():
    err = compile_error(sources(korean_basics(), staples=["seafood"]))
    assert codes(err) == ["concept_usage"]


def test_unknown_pantry_staple_fails():
    # garlic_minced → garlic 변경을 config에 반영하지 않으면 여기서 잡힌다
    err = compile_error(sources(korean_basics(), staples=["garlic_minced"]))
    assert codes(err) == ["bad_ref"]


def test_substitute_context_must_be_technique():
    subs = [{"from": "salt", "to": "doenjang", "context": ["훈연"], "status": "draft"}]
    err = compile_error(sources(korean_basics(), substitutes=subs))
    assert codes(err) == ["bad_vocab"]


def test_duplicate_id_fails():
    err = compile_error(sources([ing("a"), ing("a", name="에이")]))
    assert codes(err) == ["duplicate_id"]


def test_bad_id_format_fails():
    err = compile_error(sources([ing("Garlic-1")]))
    assert codes(err) == ["bad_id"]


def test_all_errors_reported_at_once():
    err = compile_error(sources([
        ing("a", unknown_field=1),
        ing("b", is_processed=True),
        ing("c", name="중복"),
        ing("d", name="중복"),
    ], staples=["zzz"]))
    assert set(codes(err)) == {"unknown_key", "processed_without_source", "alias_conflict", "bad_ref"}


def test_derived_without_processed_is_warning_not_error():
    from kb import compile as kb_compile

    ck = kb_compile(sources(korean_basics() + [ing("x", derived_from=["soybean"])]))
    assert any(w.code == "derived_not_processed" for w in ck.warnings)


def test_deep_is_a_is_warning():
    items = [ing("l1", kind="concept"), ing("l2", is_a=["l1"]), ing("l3", is_a=["l2"]), ing("l4", is_a=["l3"])]
    ck = compile(sources(items))
    assert [w.where for w in ck.warnings if w.code == "deep_is_a"] == ["test_ingredients#4 (l4)"]
