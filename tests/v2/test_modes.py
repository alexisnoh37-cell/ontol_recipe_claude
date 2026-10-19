"""추천 v2 형태별 동작(docs/plan.md 부록 G-3·G-4). 안전성은 tests/allergy/test_v2_*.py가 따로 본다."""

from __future__ import annotations

from dataclasses import replace

import pytest

from engine.model import UserContext
from engine.v2.config import load_v2_config
from engine.v2.model import V2Request
from engine.v2.ports import RerankAnswer, RerankError
from engine.v2.recommend import RecommenderV2
from tests.allergy import fixtures as fx
from tests.support.engine_fixtures import CONFIG_DIR, build_recommender

LIMIT = 50


def make(compiled, reranker=None, **overrides):
    cfg = replace(load_v2_config(CONFIG_DIR), **overrides)
    return RecommenderV2.from_v1(build_recommender(compiled, fx.RECIPES), cfg, reranker)


def by_id(result):
    return {i.item.recipe_id: i for i in result.items}


# --- pantry --------------------------------------------------------------------------------------------


def test_pantry_groups_ready_and_near(compiled):
    result = make(compiled).recommend(UserContext(pantry=frozenset({"potato"})), V2Request("pantry", limit=LIMIT))
    got = by_id(result)
    for rid in ("potato_salt", "soy_braised_potato", "gochujang_potato"):  # 소금·간장·고추장 = 기본 양념
        assert got[rid].group == "ready" and got[rid].required_missing == 0
    assert got["butter_potato"].group == "near" and got["butter_potato"].required_missing == 1
    assert got["kimchi_sauce_potato"].group == "near"
    groups = [i.group for i in result.items]
    assert groups.index("near") > max(i for i, g in enumerate(groups) if g == "ready")


def test_pantry_garnish_and_optional_not_required(compiled):
    v2 = make(compiled)
    got = by_id(v2.recommend(UserContext(pantry=frozenset({"cucumber"})), V2Request("pantry", limit=LIMIT)))
    assert got["cucumber_soup_egg_garnish"].group == "ready"  # 계란은 고명
    got = by_id(v2.recommend(UserContext(pantry=frozenset({"rice", "mushroom"})), V2Request("pantry", limit=LIMIT)))
    assert got["mushroom_rice_optional_egg"].group == "ready"  # 계란은 선택 재료


def test_pantry_unmapped_required_line_counts_missing(compiled):
    got = by_id(make(compiled).recommend(UserContext(pantry=frozenset({"mushroom"})), V2Request("pantry", limit=LIMIT)))
    assert got["mushroom_secret_sauce"].group == "near" and got["mushroom_secret_sauce"].required_missing == 1


def test_pantry_substitute_counts_as_owned(compiled):
    got = by_id(make(compiled).recommend(UserContext(pantry=frozenset({"mushroom", "butter"})),
                                         V2Request("pantry", limit=LIMIT)))
    it = got["mushroom_stirfry_oil"]
    assert it.group == "ready"
    assert [(s.need_id, s.use_id) for s in it.item.substitutions] == [("cooking_oil", "butter")]


def test_pantry_near_threshold_from_config(compiled):
    result = make(compiled, near_max_missing=0).recommend(UserContext(pantry=frozenset({"potato"})),
                                                         V2Request("pantry", limit=LIMIT))
    assert {i.group for i in result.items} == {"ready"}


def test_pantry_empty_pantry_returns_nothing(compiled):
    assert make(compiled).recommend(UserContext(), V2Request("pantry")).items == ()


def test_items_carry_breakdown_and_missing(compiled):
    it = by_id(make(compiled).recommend(UserContext(pantry=frozenset({"potato"})),
                                        V2Request("pantry", limit=LIMIT)))["butter_potato"]
    assert set(it.item.breakdown) >= {"I", "K", "T", "P", "D", "M"}
    assert it.item.missing == ("butter",)


# --- random --------------------------------------------------------------------------------------------


def test_random_same_seed_same_result(compiled):
    v2 = make(compiled)
    a = v2.recommend(UserContext(), V2Request("random", seed=42, limit=5))
    b = v2.recommend(UserContext(), V2Request("random", seed=42, limit=5))
    assert [i.item.recipe_id for i in a.items] == [i.item.recipe_id for i in b.items]
    assert a.seed == 42 and len(a.items) == 5 and not a.rerank_used


def test_random_without_seed_reports_seed(compiled):
    v2 = make(compiled)
    first = v2.recommend(UserContext(), V2Request("random"))
    assert first.seed is not None
    assert len(first.items) == v2.config.random_default_limit
    again = v2.recommend(UserContext(), V2Request("random", seed=first.seed))
    assert [i.item.recipe_id for i in again.items] == [i.item.recipe_id for i in first.items]


def test_random_never_calls_reranker(compiled):
    calls = []

    class Spy:
        model = "spy"

        def rerank(self, query, *, timeout_s):
            calls.append(query)
            return {}

    make(compiled, Spy()).recommend(UserContext(), V2Request("random", seed=1, rerank=True))
    assert not calls


# --- dish ----------------------------------------------------------------------------------------------


def test_dish_exact_title_first(compiled):
    result = make(compiled).recommend(UserContext(), V2Request("dish", query="감자조림", rerank=False))
    assert result.items[0].item.recipe_id == "soy_braised_potato"
    assert result.items[0].item.breakdown["S"] == 1.0


def test_dish_ingredient_mention_keeps_only_matching(compiled):
    result = make(compiled).recommend(UserContext(), V2Request("dish", query="감자로 뭐 해먹지", limit=LIMIT, rerank=False))
    got = {i.item.recipe_id for i in result.items}
    assert {"potato_salt", "butter_potato", "soy_braised_potato", "gochujang_potato"} <= got
    assert "squid_stirfry" not in got


def test_dish_keyword_title_any(compiled):
    result = make(compiled).recommend(UserContext(), V2Request("dish", query="볶음 요리", limit=LIMIT, rerank=False))
    titles = [i.item.title for i in result.items]
    assert titles and all("볶음" in t for t in titles[:3])


def test_dish_no_match(compiled):
    result = make(compiled).recommend(UserContext(), V2Request("dish", query="xyzxyz", rerank=False))
    assert result.items == () and "dish_no_match" in result.notes


def test_dish_requires_query(compiled):
    with pytest.raises(ValueError):
        make(compiled).recommend(UserContext(), V2Request("dish", query="  "))


# --- 재정렬 ---------------------------------------------------------------------------------------------


class Scripted:
    """후보 제목 → (점수, 확신도)."""

    model = "scripted"

    def __init__(self, table, default=(0.0, 1.0)):
        self.table, self.default, self.queries = table, default, []

    def rerank(self, query, *, timeout_s):
        self.queries.append(query)
        return {c.key: RerankAnswer(*self.table.get(c.title, self.default)) for c in query.candidates}


def test_rerank_reorders_with_jev_score(compiled):
    req = V2Request("dish", query="감자", limit=LIMIT, rerank=True)
    base = [i.item.title for i in make(compiled).recommend(UserContext(), replace(req, rerank=False)).items]
    last = base[-1]
    result = make(compiled, Scripted({last: (1.0, 1.0)})).recommend(UserContext(), req)
    assert result.rerank_used and result.rerank_model == "scripted"
    assert result.items[0].item.title == last
    assert result.items[0].item.breakdown["J"] == 1.0 and result.items[0].item.breakdown["J_conf"] == 1.0


def test_rerank_low_confidence_ignored(compiled):
    req = V2Request("dish", query="감자", limit=LIMIT, rerank=True)
    base = make(compiled).recommend(UserContext(), replace(req, rerank=False))
    got = make(compiled, Scripted({}, default=(1.0, 0.0))).recommend(UserContext(), req)
    assert [i.item.recipe_id for i in got.items] == [i.item.recipe_id for i in base.items]
    assert all("J" not in i.item.breakdown for i in got.items)
    assert [i.item.score for i in got.items] == [i.item.score for i in base.items]


def test_rerank_only_top_n_sent(compiled):
    spy = Scripted({})
    make(compiled, spy, rerank_top_n=2).recommend(UserContext(), V2Request("dish", query="감자", limit=LIMIT, rerank=True))
    assert len(spy.queries) == 1 and len(spy.queries[0].candidates) == 2
    assert spy.queries[0].query == "감자" and spy.queries[0].kind == "dish"


def test_rerank_off_by_request_or_missing_reranker(compiled):
    spy = Scripted({})
    r = make(compiled, spy).recommend(UserContext(), V2Request("dish", query="감자", rerank=False))
    assert not spy.queries and not r.rerank_used and "rerank_off" in r.notes
    r = make(compiled, None).recommend(UserContext(), V2Request("dish", query="감자", rerank=True))
    assert not r.rerank_used and "rerank_off" in r.notes


def test_rerank_failure_falls_back(compiled):
    class Down:
        model = "down"

        def rerank(self, query, *, timeout_s):
            raise RerankError("timeout")

    req = V2Request("dish", query="감자", limit=LIMIT, rerank=True)
    base = make(compiled).recommend(UserContext(), replace(req, rerank=False))
    got = make(compiled, Down()).recommend(UserContext(), req)
    assert [i.item.recipe_id for i in got.items] == [i.item.recipe_id for i in base.items]
    assert "rerank_unavailable" in got.notes and not got.rerank_used


def test_rerank_pantry_sends_taste_but_not_pantry(compiled):
    from engine.model import TastePreference

    spy = Scripted({})
    user = UserContext(skill_level=2, pantry=frozenset({"potato"}),
                       tastes=(TastePreference("spicy", preferred_level=1, max_level=3),))
    make(compiled, spy).recommend(user, V2Request("pantry", rerank=True))
    q = spy.queries[0]
    assert q.kind == "pantry" and q.query is None and q.skill_level == 2
    assert q.taste_preferences == {"spicy": {"preferred": 1, "max": 3}}
