"""점수 엔진 단위 테스트 (docs/plan.md 4-4~4-7, 7-2).

구체성 우선, 매운맛 감점, 동의어·상위 개념·기본 양념과 커버리지, 난이도, 음식 종류, 시간, 대체재 인정 비율,
다양성 보정, breakdown 포함, 가중치를 config에서 읽는지 확인한다.
"""

from __future__ import annotations

import copy

import pytest

from engine.config import COMPONENTS, EngineConfig, ScoringConfig, load_engine_config
from engine.memory import InMemoryKnowledgeRepository, InMemoryRecipeRepository
from engine.model import (
    Preference,
    Recipe,
    RecipeIngredient,
    RecommendRequest,
    Taste,
    TastePreference,
    UserContext,
)
from engine.normalize import resolve_terms
from engine.recommend import Recommender
from kb import compile
from tests.support.engine_fixtures import CONFIG_DIR, snapshot_from_compiled
from tests.support.kb_builders import ing, sources

INGREDIENTS = [
    ing("seafood", name="해산물", kind="concept"),
    ing("shrimp_raw", name="새우", is_a=["seafood"], allergens=[{"group": "shrimp", "certainty": "definite"}]),
    ing("squid", name="오징어", is_a=["seafood"], allergens=[{"group": "squid", "certainty": "definite"}]),
    ing("meat", name="육류", kind="concept"),
    ing("pork", name="돼지고기", is_a=["meat"]),
    ing("pork_belly", name="삼겹살", is_a=["pork"]),
    ing("egg", name="계란", aliases=["달걀"], allergens=[{"group": "egg", "certainty": "definite"}]),
    ing("onion", name="양파"),
    ing("carrot", name="당근"),
    ing("tofu", name="두부"),
    ing("rice", name="밥"),
    ing("scallion", name="쪽파"),
    ing("green_onion", name="대파"),
    ing("leek", name="부추"),
    ing("salt", name="소금"),
    ing("soy_sauce", name="간장"),
    ing("garlic", name="마늘"),
    ing("oyster_sauce", name="굴소스"),
]
SUBSTITUTES = [
    {"from": "scallion", "to": "green_onion", "context": [], "status": "draft"},
    {"from": "scallion", "to": "leek", "context": [], "ratio": 0.9, "status": "draft"},
    {"from": "carrot", "to": "onion", "context": [], "ratio": 0.5, "status": "draft"},
]
STAPLES = ["salt", "soy_sauce", "garlic"]
REQ = RecommendRequest(limit=100)


def recipe(id: str, *lines: tuple, cuisine: str = "한식", difficulty: int = 1, cook_time_min: int = 20,
           taste: Taste = Taste()) -> Recipe:
    """lines: (재료 id 또는 None, role[, optional])"""
    ingredients = tuple(
        RecipeIngredient(n, line[0], line[1], line[2] if len(line) > 2 else False, line[0] or "미상 재료")
        for n, line in enumerate(lines, start=1)
    )
    return Recipe(id=id, title=id, cuisine=cuisine, difficulty=difficulty, cook_time_min=cook_time_min,
                  ingredients=ingredients, taste=taste)


@pytest.fixture(scope="module")
def snapshot():
    return snapshot_from_compiled(compile(sources(INGREDIENTS, substitutes=SUBSTITUTES, staples=STAPLES)))


@pytest.fixture(scope="module")
def weights():
    return load_engine_config(CONFIG_DIR).weights


def make(snapshot, recipes, weights) -> Recommender:
    return Recommender(InMemoryKnowledgeRepository(snapshot), InMemoryRecipeRepository(recipes),
                       EngineConfig(weights=weights))


def by_id(result) -> dict:
    return {i.recipe_id: i for i in result.items}


def order(result) -> list[str]:
    return [i.recipe_id for i in result.items]


# --- 구체성 우선 (4-5) --------------------------------------------------------------------------


def test_specificity_most_specific_preference_wins(snapshot, weights):
    recipes = [recipe("shrimp_dish", ("shrimp_raw", "main"), ("onion", "sub")),
               recipe("squid_dish", ("squid", "main"), ("onion", "sub"))]
    user = UserContext(pantry=frozenset({"onion", "shrimp_raw", "squid"}), preferences=(
        Preference("ingredient", "seafood", 1, 0.6), Preference("ingredient", "shrimp_raw", -1, 0.9)))
    result = make(snapshot, recipes, weights).recommend(user, REQ)
    items = by_id(result)
    # 새우는 자기 선호 -0.9 → 0.05, 오징어는 해산물 +0.6 → 0.8. 양파는 중립 0.5. 역할 가중 main 1.0, sub 0.6
    assert items["shrimp_dish"].breakdown["P"] == pytest.approx((1.0 * 0.05 + 0.6 * 0.5) / 1.6, abs=1e-3)
    assert items["squid_dish"].breakdown["P"] == pytest.approx((1.0 * 0.8 + 0.6 * 0.5) / 1.6, abs=1e-3)
    assert items["shrimp_dish"].breakdown["P"] < 0.5 < items["squid_dish"].breakdown["P"]
    assert order(result) == ["squid_dish", "shrimp_dish"]


def test_specificity_same_depth_uses_lowest(snapshot, weights):
    recipes = [recipe("belly", ("pork_belly", "main"))]
    user = UserContext(pantry=frozenset({"pork_belly"}), preferences=(
        Preference("ingredient", "pork_belly", 1, 1.0), Preference("ingredient", "pork_belly", -1, 0.4)))
    item = by_id(make(snapshot, recipes, weights).recommend(user, REQ))["belly"]
    assert item.breakdown["P"] == pytest.approx(0.5 - 0.5 * 0.4)


def test_specificity_nearer_ancestor_beats_farther(snapshot, weights):
    recipes = [recipe("belly", ("pork_belly", "main"))]
    user = UserContext(pantry=frozenset({"pork_belly"}), preferences=(
        Preference("ingredient", "meat", -1, 1.0), Preference("ingredient", "pork", 1, 1.0)))
    item = by_id(make(snapshot, recipes, weights).recommend(user, REQ))["belly"]
    assert item.breakdown["P"] == pytest.approx(1.0)  # depth 1(돼지고기)이 depth 2(육류)보다 우선


def test_preference_role_weights_optional_and_seasoning(snapshot, weights):
    # 선택 재료는 optional 가중치(0.2), seasoning은 역할 가중치가 없어 P에서 빠진다
    recipes = [recipe("r", ("onion", "main"), ("carrot", "sub", True), ("oyster_sauce", "seasoning"))]
    user = UserContext(pantry=frozenset({"onion"}), preferences=(
        Preference("ingredient", "carrot", -1, 1.0), Preference("ingredient", "oyster_sauce", -1, 1.0)))
    item = by_id(make(snapshot, recipes, weights).recommend(user, REQ))["r"]
    assert item.breakdown["P"] == pytest.approx((1.0 * 0.5 + 0.2 * 0.0) / 1.2, abs=1e-3)


def test_no_ingredient_preference_is_neutral(snapshot, weights):
    item = by_id(make(snapshot, [recipe("r", ("onion", "main"))], weights).recommend(
        UserContext(pantry=frozenset({"onion"})), REQ))["r"]
    assert item.breakdown["P"] == 0.5


def test_unknown_soft_preference_ingredient_raises(snapshot, weights):
    user = UserContext(pantry=frozenset({"onion"}), preferences=(Preference("ingredient", "no_such", 1, 1.0),))
    with pytest.raises(ValueError):
        make(snapshot, [recipe("r", ("onion", "main"))], weights).recommend(user, REQ)


# --- 맛 (T) ------------------------------------------------------------------------------------


def test_spicy_preferred_level_penalizes_without_excluding(snapshot, weights):
    recipes = [recipe("mild", ("onion", "main"), taste=Taste(spicy=0)),
               recipe("hot", ("onion", "main"), taste=Taste(spicy=4))]
    user = UserContext(pantry=frozenset({"onion"}), tastes=(TastePreference("spicy", preferred_level=0),))
    result = make(snapshot, recipes, weights).recommend(user, REQ)
    items = by_id(result)
    assert set(items) == {"mild", "hot"} and not result.exclusions
    assert items["mild"].breakdown["T"] == 1.0
    assert items["hot"].breakdown["T"] == pytest.approx(1 - 4 / 5)
    assert order(result) == ["mild", "hot"]


def test_taste_averages_only_entered_dimensions(snapshot, weights):
    recipes = [recipe("r", ("onion", "main"), taste=Taste(spicy=2, salty=5, sweet=0))]
    user = UserContext(pantry=frozenset({"onion"}), tastes=(
        TastePreference("spicy", preferred_level=2), TastePreference("sweet", preferred_level=3),
        TastePreference("salty", max_level=5)))  # salty는 preferred_level이 없어 평균에서 뺀다
    item = by_id(make(snapshot, recipes, weights).recommend(user, REQ))["r"]
    assert item.breakdown["T"] == pytest.approx(1 - ((0 + 3) / 2) / 5)


def test_taste_without_any_preference_is_half(snapshot, weights):
    item = by_id(make(snapshot, [recipe("r", ("onion", "main"), taste=Taste(spicy=5))], weights).recommend(
        UserContext(pantry=frozenset({"onion"})), REQ))["r"]
    assert item.breakdown["T"] == 0.5


# --- 커버리지 (I): 동의어, 상위 개념, 기본 양념, 대체재 ------------------------------------------


def test_synonym_input_matches_recipe(snapshot, weights):
    pantry = resolve_terms(snapshot, ["달걀"]).ids
    assert pantry == frozenset({"egg"})
    item = by_id(make(snapshot, [recipe("egg_dish", ("egg", "main"))], weights).recommend(
        UserContext(pantry=pantry), REQ))["egg_dish"]
    assert item.breakdown["I"] == 1.0 and item.missing == ()


def test_broader_concept_matching_counts_as_owned(snapshot, weights):
    item = by_id(make(snapshot, [recipe("pork_dish", ("pork", "main"), ("tofu", "sub"))], weights).recommend(
        UserContext(pantry=frozenset({"pork_belly"})), REQ))["pork_dish"]
    assert item.breakdown["I"] == pytest.approx(3 / 5)  # 돼지고기(main 3) 충족, 두부(sub 2) 부족
    assert item.missing == ("tofu",)


def test_pantry_staples_do_not_reduce_coverage(snapshot, weights):
    # 소금·간장·마늘을 입력하지 않았고, 마늘은 sub로 쓰였어도 보유로 간주
    r = recipe("r", ("onion", "main"), ("garlic", "sub"), ("salt", "seasoning"), ("soy_sauce", "seasoning"))
    item = by_id(make(snapshot, [r], weights).recommend(UserContext(pantry=frozenset({"onion"})), REQ))["r"]
    assert item.breakdown["I"] == 1.0
    assert item.missing == ()


def test_non_staple_seasoning_counts_in_coverage_with_weight_one(snapshot, weights):
    # 1-4: 기본 양념이 아닌 seasoning(굴소스 등)은 가중치 1로 커버리지에 포함한다
    r = recipe("r", ("onion", "main"), ("oyster_sauce", "seasoning"))
    item = by_id(make(snapshot, [r], weights).recommend(UserContext(pantry=frozenset({"onion"})), REQ))["r"]
    assert weights["coverage"]["role_weight"]["seasoning"] == 1
    assert item.breakdown["I"] == pytest.approx(3 / 4)
    assert item.missing == ("oyster_sauce",)
    owned = by_id(make(snapshot, [r], weights).recommend(UserContext(pantry=frozenset({"onion", "oyster_sauce"})), REQ))["r"]
    assert owned.breakdown["I"] == 1.0


def test_staples_and_garnish_excluded_from_coverage_any_role(snapshot, weights):
    # 기본 양념은 main이어도 계산에서 빠지고, garnish는 역할 가중치가 없다
    r = recipe("r", ("onion", "main"), ("garlic", "main"), ("salt", "seasoning"), ("tofu", "garnish"))
    item = by_id(make(snapshot, [r], weights).recommend(UserContext(pantry=frozenset({"onion"})), REQ))["r"]
    assert item.breakdown["I"] == 1.0
    assert item.missing == ("tofu",)


# --- 동점 처리(1-4) --------------------------------------------------------------------------------


def test_tie_break_order(snapshot, weights):
    # 모든 항목 점수가 같도록 가중치를 coverage 0으로 두고, 동점에서 I → 부족 재료 수 → 조리시간 → id 순
    w = copy.deepcopy(weights)
    w["weights"] = {k: 0.0 for k in w["weights"]} | {"difficulty": 1.0}
    recipes = [
        recipe("z_full_long", ("onion", "main"), cook_time_min=50),
        recipe("a_low_cov", ("onion", "main"), ("tofu", "sub")),
        recipe("y_full_short", ("onion", "main"), cook_time_min=10),
        recipe("b_full_short", ("onion", "main"), cook_time_min=10),
        recipe("c_low_cov_more_missing", ("onion", "main"), ("tofu", "seasoning"), ("rice", "seasoning")),
    ]
    result = make(snapshot, recipes, w).recommend(UserContext(pantry=frozenset({"onion"})), REQ)
    assert {i.score for i in result.items} == {1.0}
    # I: full 1.0, a_low_cov 3/5=0.6, c 3/5=0.6. a와 c는 I가 같고 부족 재료 수(1 < 2)로 갈린다
    assert order(result) == ["b_full_short", "y_full_short", "z_full_long", "a_low_cov", "c_low_cov_more_missing"]


def test_optional_ingredients_excluded_from_coverage(snapshot, weights):
    r = recipe("r", ("onion", "main"), ("tofu", "sub", True))
    item = by_id(make(snapshot, [r], weights).recommend(UserContext(pantry=frozenset({"onion"})), REQ))["r"]
    assert item.breakdown["I"] == 1.0
    assert item.missing == ()
    assert any("선택 재료" in n for n in item.notes)


def test_substitute_default_credit(snapshot, weights):
    r = recipe("r", ("onion", "main"), ("scallion", "sub"))
    item = by_id(make(snapshot, [r], weights).recommend(
        UserContext(pantry=frozenset({"onion", "green_onion"})), REQ))["r"]
    credit = weights["coverage"]["substitute_credit"]
    assert item.breakdown["I"] == pytest.approx((3 + 2 * credit) / 5, abs=1e-3)
    assert [(s.need_id, s.use_id) for s in item.substitutions] == [("scallion", "green_onion")]


def test_substitute_ratio_overrides_default_and_highest_ratio_chosen(snapshot, weights):
    r = recipe("r", ("onion", "main"), ("scallion", "sub"))
    item = by_id(make(snapshot, [r], weights).recommend(
        UserContext(pantry=frozenset({"onion", "green_onion", "leek"})), REQ))["r"]
    # 대파(기본 0.8)와 부추(ratio 0.9)가 모두 가능하면 인정 비율이 높은 부추
    assert [(s.need_id, s.use_id) for s in item.substitutions] == [("scallion", "leek")]
    assert item.breakdown["I"] == pytest.approx((3 + 2 * 0.9) / 5, abs=1e-3)


def test_substitute_low_ratio(snapshot, weights):
    r = recipe("r", ("carrot", "main"))
    item = by_id(make(snapshot, [r], weights).recommend(UserContext(pantry=frozenset({"onion"})), REQ))["r"]
    assert item.breakdown["I"] == pytest.approx(0.5)


# --- 난이도 (D), 음식 종류 (K), 시간 (M) -----------------------------------------------------------


def test_beginner_prefers_easy_recipe(snapshot, weights):
    recipes = [recipe("hard", ("onion", "main"), difficulty=3), recipe("easy", ("onion", "main"), difficulty=1)]
    result = make(snapshot, recipes, weights).recommend(UserContext(skill_level=1, pantry=frozenset({"onion"})), REQ)
    assert order(result) == ["easy", "hard"]
    assert by_id(result)["easy"].breakdown["D"] == 1.0
    assert by_id(result)["hard"].breakdown["D"] == weights["difficulty"]["2"]


@pytest.mark.parametrize("skill,difficulty,key", [(3, 1, "-2"), (3, 2, "-1"), (2, 2, "0"), (1, 2, "1"), (1, 3, "2")])
def test_difficulty_table(snapshot, weights, skill, difficulty, key):
    item = by_id(make(snapshot, [recipe("r", ("onion", "main"), difficulty=difficulty)], weights).recommend(
        UserContext(skill_level=skill, pantry=frozenset({"onion"})), REQ))["r"]
    assert item.breakdown["D"] == weights["difficulty"][key]


def test_cuisine_like_neutral_dislike(snapshot, weights):
    recipes = [recipe("ko", ("onion", "main"), cuisine="한식"), recipe("ja", ("onion", "main"), cuisine="일식"),
               recipe("we", ("onion", "main"), cuisine="양식")]
    user = UserContext(pantry=frozenset({"onion"}), preferences=(
        Preference("cuisine", "한식", 1, 1.0), Preference("cuisine", "양식", -1, 1.0)))
    result = make(snapshot, recipes, weights).recommend(user, REQ)
    items = by_id(result)
    assert (items["ko"].breakdown["K"], items["ja"].breakdown["K"], items["we"].breakdown["K"]) == (
        weights["cuisine"]["like"], weights["cuisine"]["neutral"], weights["cuisine"]["dislike"])
    assert order(result) == ["ko", "ja", "we"]  # soft 불선호는 감점일 뿐 제외가 아니다


@pytest.mark.parametrize("wish,t,expected", [(None, 90, 1.0), (30, 30, 1.0), (30, 45, 0.5), (30, 60, 0.0), (30, 120, 0.0)])
def test_time_score(snapshot, weights, wish, t, expected):
    item = by_id(make(snapshot, [recipe("r", ("onion", "main"), cook_time_min=t)], weights).recommend(
        UserContext(pantry=frozenset({"onion"})), RecommendRequest(max_time_min=wish, limit=10)))["r"]
    assert item.breakdown["M"] == pytest.approx(expected)
    assert (expected < 1.0) == any("희망 시간" in n for n in item.notes)


# --- breakdown, 가중합, 설정 ---------------------------------------------------------------------


def test_every_item_has_full_breakdown_and_weighted_score(snapshot, weights):
    recipes = [recipe("a", ("onion", "main"), ("tofu", "sub"), difficulty=2, cook_time_min=50, taste=Taste(spicy=3)),
               recipe("b", ("pork", "main"), cuisine="양식")]
    user = UserContext(skill_level=1, pantry=frozenset({"onion", "pork_belly"}),
                       tastes=(TastePreference("spicy", preferred_level=1),),
                       preferences=(Preference("cuisine", "양식", 1, 1.0),))
    result = make(snapshot, recipes, weights).recommend(user, RecommendRequest(max_time_min=30, limit=10))
    assert len(result.items) == 2
    cfg = ScoringConfig.from_mapping(weights)
    for item in result.items:
        assert set(item.breakdown) == set(COMPONENTS)
        assert all(0.0 <= v <= 1.0 for v in item.breakdown.values())
        expected = sum(cfg.weights[c] * item.breakdown[c] for c in COMPONENTS)
        assert item.score == pytest.approx(expected, abs=2e-3)


def test_weights_come_from_config(snapshot, weights):
    recipes = [recipe("easy", ("onion", "main"), ("tofu", "sub"), difficulty=1),
               recipe("hard", ("onion", "main"), ("carrot", "sub", True), difficulty=3)]
    user = UserContext(skill_level=1, pantry=frozenset({"onion"}))
    assert order(make(snapshot, recipes, weights).recommend(user, REQ))[0] == "hard"  # 커버리지 우세
    only_difficulty = copy.deepcopy(weights)
    only_difficulty["weights"] = {k: 0.0 for k in only_difficulty["weights"]} | {"difficulty": 1.0}
    result = make(snapshot, recipes, only_difficulty).recommend(user, REQ)
    assert order(result) == ["easy", "hard"]
    assert by_id(result)["easy"].score == 1.0


def test_missing_config_key_raises(weights):
    broken = copy.deepcopy(weights)
    del broken["coverage"]
    with pytest.raises(ValueError):
        ScoringConfig.from_mapping(broken)
    with pytest.raises(ValueError):
        ScoringConfig.from_mapping({})


def test_engine_yaml_serve_draft_default_off():
    assert load_engine_config(CONFIG_DIR).serve_draft_recipes is False
    assert load_engine_config(CONFIG_DIR, serve_draft_recipes=True).serve_draft_recipes is True


# --- 다양성 보정 (4-6) ----------------------------------------------------------------------------


def _diversity_weights(weights, top_n=5, max_cuisine=2, max_main=2, max_gap=1.0):
    """max_gap 기본 1.0 = 점수 차 제한 없음(한도 규칙만 보는 테스트용). 1-6 실제 설정은 0.1."""
    w = copy.deepcopy(weights)
    w["diversity"] = {"top_n": top_n, "max_same_cuisine": max_cuisine, "max_same_main_ingredient": max_main,
                      "max_score_gap": max_gap}
    return w


def test_diversity_caps_same_cuisine_in_top_n(snapshot, weights):
    # 한식 4개가 점수 상위(커버리지 1.0), 일식·양식은 커버리지가 낮다
    recipes = [recipe(f"ko{i}", (f"{m}", "main")) for i, m in enumerate(["onion", "tofu", "rice", "egg"])]
    recipes += [recipe("ja", ("onion", "main"), ("carrot", "sub"), cuisine="일식"),
                recipe("we", ("tofu", "main"), ("carrot", "sub"), cuisine="양식")]
    user = UserContext(pantry=frozenset({"onion", "tofu", "rice", "egg"}))
    base = order(make(snapshot, recipes, _diversity_weights(weights, max_cuisine=99, max_main=99)).recommend(user, REQ))
    assert base[:4] == ["ko0", "ko1", "ko2", "ko3"]
    result = order(make(snapshot, recipes, _diversity_weights(weights)).recommend(user, REQ))
    assert result == ["ko0", "ko1", "ja", "we", "ko2", "ko3"]  # 상위 5 안에 한식 2개 한도, 남는 칸은 미룬 항목으로


def test_diversity_counts_each_main_ingredient(snapshot, weights):
    recipes = [recipe("a", ("onion", "main"), ("tofu", "main")),
               recipe("b", ("onion", "main"), cuisine="일식"),
               recipe("c", ("onion", "main"), cuisine="양식"),
               recipe("d", ("tofu", "main"), ("carrot", "sub"), cuisine="중식"),
               recipe("e", ("rice", "main"), ("carrot", "sub"), cuisine="중식")]
    user = UserContext(pantry=frozenset({"onion", "tofu", "rice"}))
    result = order(make(snapshot, recipes, _diversity_weights(weights, top_n=3, max_cuisine=3)).recommend(user, REQ))
    # 양파 main은 a, b로 한도 2 → c는 미룸. d(두부, a와 함께 2번째)는 가능
    assert result[:3] == ["a", "b", "d"]
    assert set(result[3:]) == {"c", "e"}


def test_diversity_never_reintroduces_excluded(snapshot, weights):
    recipes = [recipe("shrimp_dish", ("shrimp_raw", "main"), ("onion", "sub")),
               recipe("ko", ("onion", "main")), recipe("ko2", ("onion", "main"), ("tofu", "sub"))]
    user = UserContext(pantry=frozenset({"onion", "shrimp_raw"}), allergen_groups=frozenset({"shrimp"}))
    result = make(snapshot, recipes, _diversity_weights(weights, top_n=3, max_cuisine=1)).recommend(user, REQ)
    assert "shrimp_dish" not in order(result)
    assert set(order(result)) == {"ko", "ko2"}
    assert result.exclusion_summary == {"allergen": 1}


def test_diversity_only_swaps_within_score_gap(snapshot, weights):
    """1-6: 점수 차가 max_score_gap을 넘는 레시피는 한도 때문에 앞으로 올라오지 않는다."""
    recipes = [recipe(f"ko{i}", (f"{m}", "main")) for i, m in enumerate(["onion", "tofu", "rice", "egg"])]
    # 커버리지(부재료 부족)와 난이도(초급자에게 3) 차이로 한식보다 0.1 넘게 낮다
    recipes += [recipe("ja", ("onion", "main"), ("carrot", "sub"), cuisine="일식", difficulty=3),
                recipe("we", ("tofu", "main"), ("carrot", "sub"), cuisine="양식", difficulty=3)]
    user = UserContext(pantry=frozenset({"onion", "tofu", "rice", "egg"}))
    base = make(snapshot, recipes, _diversity_weights(weights, max_cuisine=99, max_main=99)).recommend(user, REQ)
    scores = {i.recipe_id: i.score for i in base.items}
    assert scores["ko2"] - scores["ja"] > 0.1  # 커버리지 차이로 0.1 넘게 벌어지는 상황
    narrow = order(make(snapshot, recipes, _diversity_weights(weights, max_gap=0.1)).recommend(user, REQ))
    assert narrow == order(base)  # 한도를 넘어도 큰 점수 차는 뒤집지 않는다
    wide = order(make(snapshot, recipes, _diversity_weights(weights, max_gap=1.0)).recommend(user, REQ))
    assert wide == ["ko0", "ko1", "ja", "we", "ko2", "ko3"]


def test_diversity_swaps_close_scores_and_never_jumps_more_than_gap(snapshot, weights):
    # 한식 3개와 일식 1개, 모두 커버리지 1.0. 일식만 난이도 2라 0.1 이내로 조금 낮다
    recipes = [recipe(f"ko{i}", (m, "main")) for i, m in enumerate(["onion", "tofu", "rice"])]
    recipes += [recipe("ja", ("egg", "main"), cuisine="일식", difficulty=2)]  # 난이도 차이만큼 조금 낮다
    user = UserContext(pantry=frozenset({"onion", "tofu", "rice", "egg"}))
    w = _diversity_weights(weights, top_n=4, max_cuisine=2, max_gap=0.1)
    result = make(snapshot, recipes, w).recommend(user, REQ)
    scores = {i.recipe_id: i.score for i in result.items}
    assert 0 < scores["ko2"] - scores["ja"] <= 0.1
    assert order(result) == ["ko0", "ko1", "ja", "ko2"]  # 점수 차 0.1 이내라 한도대로 일식이 앞으로
    items = result.items
    for i, a in enumerate(items):  # 앞선 레시피가 뒤 레시피보다 낮으면 그 차이는 gap 이하
        for b in items[i + 1:]:
            assert b.score - a.score <= 0.1 + 1e-9


def test_real_config_has_score_gap():
    from engine.config import ScoringConfig, load_engine_config

    assert ScoringConfig.from_mapping(load_engine_config(CONFIG_DIR).weights).diversity_max_score_gap == 0.1


def test_optional_missing_is_display_only(snapshot, weights):
    """1-6: 선택 재료 미보유 목록(optional_missing)은 표시용. missing·점수에는 들어가지 않는다."""
    recipes = [recipe("a", ("onion", "main"), ("rice", "sub", True), ("tofu", "garnish"))]
    item = make(snapshot, recipes, weights).recommend(UserContext(pantry=frozenset({"onion"})), REQ).items[0]
    assert item.optional_missing == ("rice",)
    assert item.missing == ("tofu",)
    assert item.breakdown["I"] == 1.0
