"""시나리오 11: 제외 기록에 사유 코드와 근거 경로가 남는다."""

from __future__ import annotations

from engine.model import ExclusionReason
from tests.allergy import fixtures as fx
from tests.allergy.checks import exclusions


def only(found):
    assert len(found) == 1, found
    return found[0]


def evidence(e):
    return (e.ingredient_id, e.target, e.certainty, e.via)


def test_kimchi_path_for_shrimp_allergy(recommend):
    e = only(exclusions(recommend(fx.user("shrimp")), "kimchi_fried_rice", ExclusionReason.ALLERGEN))
    assert evidence(e) == ("kimchi", "shrimp", "possible", ("kimchi", "saeujeot", "shrimp_raw"))


def test_saeujeot_path_is_definite(recommend):
    e = only(exclusions(recommend(fx.user("shrimp")), "cabbage_saeujeot_soup", ExclusionReason.ALLERGEN))
    assert evidence(e) == ("saeujeot", "shrimp", "definite", ("saeujeot", "shrimp_raw"))


def test_gochujang_wheat_is_possible(recommend):
    e = only(exclusions(recommend(fx.user("wheat")), "gochujang_potato", ExclusionReason.ALLERGEN))
    assert evidence(e) == ("gochujang", "wheat", "possible", ("gochujang", "wheat_flour"))


def test_intermediate_node_path(recommend):
    e = only(exclusions(recommend(fx.user("shrimp")), "jeotgal_cabbage_salad", ExclusionReason.ALLERGEN))
    assert evidence(e) == ("jeotgal", "shrimp", "possible", ("jeotgal", "saeujeot", "shrimp_raw"))


def test_three_step_derivation_path(recommend):
    e = only(exclusions(recommend(fx.user("shrimp")), "kimchi_sauce_potato", ExclusionReason.ALLERGEN))
    assert evidence(e) == ("kimchi_sauce", "shrimp", "possible", ("kimchi_sauce", "kimchi", "saeujeot", "shrimp_raw"))


def test_possible_on_source_itself(recommend):
    e = only(exclusions(recommend(fx.user("milk")), "seasoning_blend_mushroom", ExclusionReason.ALLERGEN))
    assert evidence(e) == ("seasoning_blend", "milk", "possible", ("seasoning_blend",))


def test_is_a_inheritance_path(recommend):
    e = only(exclusions(recommend(fx.user("shellfish")), "manila_clam_soup", ExclusionReason.ALLERGEN))
    assert evidence(e) == ("manila_clam", "shellfish", "definite", ("manila_clam", "clam"))


def test_hard_dislike_path(recommend):
    result = recommend(fx.user(preferences=(fx.hard_dislike("shrimp_raw"),)))
    e = only(exclusions(result, "kimchi_fried_rice", ExclusionReason.HARD_DISLIKE_INGREDIENT))
    assert evidence(e) == ("kimchi", "shrimp_raw", "possible", ("kimchi", "saeujeot", "shrimp_raw"))


def test_unmapped_exclusion_names_raw_text(recommend):
    e = only(exclusions(recommend(fx.user("egg")), "mushroom_secret_sauce", ExclusionReason.UNMAPPED_INGREDIENT))
    assert e.ingredient_id is None
    assert "비법 소스" in e.detail


def test_every_exclusion_is_well_formed(recommend):
    result = recommend(fx.user("egg", "milk", "shrimp", "wheat", "nuts_bundle", "shellfish"))
    assert result.exclusions
    for e in result.exclusions:
        assert e.recipe_id in fx.RECIPE_IDS
        assert isinstance(e.reason, ExclusionReason)
        if e.reason == ExclusionReason.ALLERGEN:
            assert e.ingredient_id and e.target and e.certainty in ("definite", "possible")
            assert e.via and e.via[0] == e.ingredient_id
