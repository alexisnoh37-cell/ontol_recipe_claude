"""6가지 입력 프로필 변환(engine/v2/profile.py)과 테스트 페르소나 파일(docs/plan.md 부록 G-11)."""

from __future__ import annotations

import pytest

from engine.v2.profile import SimpleProfile
from storage.engine_source import load_files
from storage.personas_v2 import load_v2_personas


def test_mapping_to_user_context():
    u = SimpleProfile(allergens=frozenset({"egg"}), never_eat=frozenset({"cucumber"}), likes=frozenset({"potato"}),
                      dislikes=frozenset({"onion"}), spicy_level=2, cuisine_likes=frozenset({"한식"}),
                      cuisine_dislikes=frozenset({"중식"}), skill_level=3).to_user_context(equipment=["오븐"])
    assert u.allergen_groups == {"egg"} and u.skill_level == 3 and u.equipment == {"오븐"}
    got = {(p.target_type, p.target_id, p.polarity, p.is_hard) for p in u.preferences}
    assert got == {("ingredient", "cucumber", -1, True), ("ingredient", "potato", 1, False),
                   ("ingredient", "onion", -1, False), ("cuisine", "한식", 1, False), ("cuisine", "중식", -1, False)}
    (t,) = u.tastes
    assert (t.dimension, t.preferred_level, t.max_level) == ("spicy", 2, 2)


def test_spicy_five_means_no_limit_only_and_none_means_unknown():
    # 5는 '한도 없음'으로만 본다: 제외도 없고 맛 취향(T 점수·Jev 질문)도 없다(D10 보완)
    assert SimpleProfile(spicy_level=5).to_user_context().tastes == ()
    assert SimpleProfile().to_user_context().tastes == ()
    (t,) = SimpleProfile(spicy_level=4).to_user_context().tastes
    assert (t.preferred_level, t.max_level) == (4, 4)


def test_skill_default_is_middle():
    assert SimpleProfile().to_user_context().skill_level == 2


@pytest.mark.parametrize("profile", [
    SimpleProfile(likes=frozenset({"egg"}), dislikes=frozenset({"egg"})),
    SimpleProfile(cuisine_likes=frozenset({"한식"}), cuisine_dislikes=frozenset({"한식"})),
    SimpleProfile(spicy_level=6),
    SimpleProfile(skill_level=0),
])
def test_invalid_profiles_rejected(profile):
    with pytest.raises(ValueError):
        profile.to_user_context()


def test_test_personas_use_known_ids():
    data = load_files()
    known = {i.id for i in data.knowledge.ingredients}
    groups = {g.id for g in data.knowledge.allergen_groups}
    cuisines = set(data.knowledge.vocab["cuisines"])
    personas = load_v2_personas()
    assert len(personas) == 5 and len({p.id for p in personas}) == 5
    for p in personas:
        pr = p.profile
        assert pr.allergens <= groups, p.id
        assert (pr.never_eat | pr.likes | pr.dislikes | set(p.try_pantry)) <= known, p.id
        assert (pr.cuisine_likes | pr.cuisine_dislikes) <= cuisines, p.id
        assert p.checks and p.try_dish, p.id
