"""추천 v2 안전성(docs/plan.md 부록 G-8, decisions D7·D8). 신규 — 사람 승인 대상.

세 형태(random·pantry·dish) 모두 알레르기(possible·선택·고명·기본 양념 포함), 알레르기 사용자의 미매칭,
definite 절대 불선호 레시피를 내지 않는다. 불선호가 possible로만 걸린 레시피는 v2에서 통과한다(D8).
v1(tests/allergy/ 기존 테스트)의 동작은 바꾸지 않는다.
"""

from __future__ import annotations

import pytest

from engine.model import ExclusionReason, UserContext
from engine.v2.config import load_v2_config
from engine.v2.model import V2Request, V2Result
from engine.v2.recommend import RecommenderV2
from tests.allergy import fixtures as fx
from tests.support.engine_fixtures import CONFIG_DIR, build_recommender

LIMIT = len(fx.RECIPES) + 10
NO_SHRIMP = fx.user(preferences=(fx.hard_dislike("shrimp_raw"),))


@pytest.fixture(scope="module")
def v2(compiled):
    return RecommenderV2.from_v1(build_recommender(compiled, fx.RECIPES), load_v2_config(CONFIG_DIR))


def ids(result: V2Result) -> set[str]:
    return {i.item.recipe_id for i in result.items}


def run_all_modes(v2, user: UserContext) -> dict[str, set[str]]:
    """형태별 추천 id. dish는 레시피 제목마다 질의해 모든 레시피가 후보가 될 기회를 준다."""
    out = {
        "random": ids(v2.recommend(user, V2Request("random", seed=1, limit=LIMIT, rerank=False))),
        "pantry": ids(v2.recommend(user, V2Request("pantry", limit=LIMIT, rerank=False))),
    }
    dish: set[str] = set()
    for r in fx.RECIPES:
        dish |= ids(v2.recommend(user, V2Request("dish", query=r.title, limit=LIMIT, rerank=False)))
    out["dish"] = dish
    return out


def v1_unsafe(recommend, user: UserContext) -> set[str]:
    """v1이 알레르기·미매칭으로 제외하는 레시피(v1 판정 = 기준)."""
    result = recommend(user)
    return {e.recipe_id for e in result.exclusions
            if e.reason in (ExclusionReason.ALLERGEN, ExclusionReason.UNMAPPED_INGREDIENT)}


ALLERGY_CASES = [("shrimp",), ("egg",), ("milk",), ("wheat",), ("soybean",), ("shellfish",), ("peanut", "walnut"),
                 ("crustacean_bundle",), ("seafood_bundle",)]


@pytest.mark.parametrize("groups", ALLERGY_CASES, ids=["+".join(g) for g in ALLERGY_CASES])
def test_v2_never_returns_allergen_or_unmapped(v2, recommend, groups):
    user = fx.user(*groups)
    unsafe = v1_unsafe(recommend, user)
    assert unsafe, "대조: 이 알레르기로 제외되는 레시피가 fixture에 있어야 한다"
    for mode, got in run_all_modes(v2, user).items():
        assert not got & unsafe, f"{mode}에서 알레르기·미매칭 레시피가 나왔습니다: {sorted(got & unsafe)}"


@pytest.mark.parametrize(("recipe_id", "group"), [
    ("kimchi_fried_rice", "shrimp"),  # 김치 → 새우젓(possible) → 새우: 알레르기는 possible도 제외
    ("cucumber_soup_egg_garnish", "egg"),  # 고명
    ("mushroom_rice_optional_egg", "egg"),  # 선택 재료
    ("soy_braised_potato", "wheat"),  # 기본 양념(간장)
    ("seasoning_blend_mushroom", "milk"),  # 원천 재료 자체가 possible
    ("mushroom_secret_sauce", "egg"),  # 미매칭 재료(알레르기 사용자)
])
def test_v2_specific_unsafe_recipes_excluded_everywhere(v2, recipe_id, group):
    for mode, got in run_all_modes(v2, fx.user(group)).items():
        assert recipe_id not in got, f"{mode}: {recipe_id}가 {group} 알레르기 사용자에게 나왔습니다"


def test_v2_excluded_recipe_has_reason_logged(v2):
    result = v2.recommend(fx.user("shrimp"), V2Request("dish", query="김치볶음밥", limit=LIMIT, rerank=False))
    assert "kimchi_fried_rice" not in ids(result)
    assert any(e.recipe_id == "kimchi_fried_rice" and e.reason == ExclusionReason.ALLERGEN for e in result.exclusions)


@pytest.mark.parametrize("recipe_id", ["shrimp_stirfry", "cabbage_saeujeot_soup"])
def test_v2_definite_hard_dislike_excluded(v2, recipe_id):
    for mode, got in run_all_modes(v2, NO_SHRIMP).items():
        assert recipe_id not in got, f"{mode}: definite 불선호 레시피 {recipe_id}가 나왔습니다"


def test_v2_possible_hard_dislike_not_excluded(v2):
    # D8: 김치 → 새우젓(possible) → 새우. v2에서는 불선호 possible만으로 제외하지 않고 note를 단다
    for mode, got in run_all_modes(v2, NO_SHRIMP).items():
        assert "kimchi_fried_rice" in got, f"{mode}: possible 불선호만 걸린 김치볶음밥이 빠졌습니다"
    result = v2.recommend(NO_SHRIMP, V2Request("dish", query="김치볶음밥", limit=LIMIT, rerank=False))
    item = next(i for i in result.items if i.item.recipe_id == "kimchi_fried_rice")
    assert "dislike_possible" in item.notes
    assert not [e for e in result.exclusions if e.recipe_id == "kimchi_fried_rice"]


def test_v2_substitute_never_uses_unsafe_ingredient(v2):
    # 낙지 → 새우 대체(볶음)는 새우 알레르기·새우 불선호 사용자에게 쓰지 않는다(v1 is_unsafe 그대로)
    for user in (fx.user("shrimp"), NO_SHRIMP):
        result = v2.recommend(user, V2Request("pantry", limit=LIMIT, rerank=False))
        for it in result.items:
            assert all(s.use_id != "shrimp_raw" for s in it.item.substitutions), it.item.recipe_id


def test_v2_control_no_allergy_returns_everything_random(v2):
    got = ids(v2.recommend(fx.NO_ALLERGY, V2Request("random", seed=3, limit=LIMIT, rerank=False)))
    assert got == fx.RECIPE_IDS
