"""6가지 입력 프로필로 받은 '못 먹는 것'의 안전성(docs/plan.md 부록 G-11). 신규 — 사람 승인 대상.

알레르기는 들어 있을 수도 있는 재료까지, 절대 안 먹는 재료는 확실히 들어간 재료만 제외한다(D8).
좋아하는 재료가 못 먹는 것과 겹치면 제외가 이긴다. 싫어하는 재료는 제외하지 않는다.
"""

from __future__ import annotations

import pytest

from engine.v2.config import load_v2_config
from engine.v2.model import V2Request
from engine.v2.profile import SimpleProfile
from engine.v2.recommend import RecommenderV2
from tests.allergy import fixtures as fx
from tests.support.engine_fixtures import CONFIG_DIR, build_recommender

LIMIT = len(fx.RECIPES) + 10


@pytest.fixture(scope="module")
def v2(compiled):
    return RecommenderV2.from_v1(build_recommender(compiled, fx.RECIPES), load_v2_config(CONFIG_DIR))


def ids(v2, profile: SimpleProfile, mode="random", **kw):
    user = profile.to_user_context(pantry=fx.PANTRY)
    return {i.item.recipe_id for i in v2.recommend(user, V2Request(mode, seed=1, limit=LIMIT, rerank=False, **kw)).items}


def test_allergy_beats_like(v2):
    # 김치를 좋아해도 새우 알레르기면 김치(새우젓 포함 가능) 레시피는 나오지 않는다
    got = ids(v2, SimpleProfile(allergens=frozenset({"shrimp"}), likes=frozenset({"kimchi"})))
    assert not got & {"kimchi_fried_rice", "kimchi_sauce_potato", "shrimp_stirfry", "cabbage_saeujeot_soup"}


def test_never_eat_beats_like(v2):
    got = ids(v2, SimpleProfile(never_eat=frozenset({"potato"}), likes=frozenset({"butter"})))
    assert not got & {"potato_salt", "butter_potato", "soy_braised_potato", "gochujang_potato"}


def test_never_eat_definite_only(v2):
    got = ids(v2, SimpleProfile(never_eat=frozenset({"shrimp_raw"})))
    assert "shrimp_stirfry" not in got and "cabbage_saeujeot_soup" not in got
    assert "kimchi_fried_rice" in got  # 김치 → 새우젓은 possible: 절대 안 먹음에서는 제외하지 않음(D8)


def test_strict_avoidance_via_allergen_excludes_possible(v2):
    got = ids(v2, SimpleProfile(allergens=frozenset({"shrimp"})))
    assert "kimchi_fried_rice" not in got


def test_dislike_is_not_exclusion(v2):
    assert "potato_salt" in ids(v2, SimpleProfile(dislikes=frozenset({"potato"})))


@pytest.mark.parametrize("mode,kw", [("random", {}), ("pantry", {}), ("dish", {"query": "감자"}),
                                     ("dish", {"query": "김치볶음밥"})])
def test_all_modes_respect_profile_allergy(v2, mode, kw):
    got = ids(v2, SimpleProfile(allergens=frozenset({"shrimp", "egg"})), mode, **kw)
    assert not got & {"kimchi_fried_rice", "shrimp_stirfry", "cucumber_soup_egg_garnish",
                      "mushroom_rice_optional_egg", "mayo_cucumber_salad", "mushroom_secret_sauce"}


def test_dish_excluded_note(v2):
    user = SimpleProfile(allergens=frozenset({"shrimp"})).to_user_context()
    result = v2.recommend(user, V2Request("dish", query="새우볶음", rerank=False))
    assert "shrimp_stirfry" not in {i.item.recipe_id for i in result.items}
    assert "dish_excluded" in result.notes
