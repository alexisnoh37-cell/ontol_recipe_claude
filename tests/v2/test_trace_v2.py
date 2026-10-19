"""v2 추천 과정 기록(docs/plan.md 부록 H-2). trace()는 recommend()와 같은 경로이고, 기록은 결과와 맞아야 한다."""

from __future__ import annotations

from dataclasses import replace

import pytest

from engine.model import Preference, TastePreference, UserContext
from engine.v2.config import load_v2_config
from engine.v2.model import V2Request
from engine.v2.ports import RerankAnswer, RerankError
from engine.v2.recommend import RecommenderV2
from engine.v2.similarity import DishScorer, combine, parse_query
from tests.allergy import fixtures as fx
from tests.support.engine_fixtures import CONFIG_DIR, build_recommender


class Table:
    model = "table-judge"

    def __init__(self, scores=None):
        self.scores = scores or {}

    def screen(self, profile, candidates, *, timeout_s):
        return {c.key: self.scores.get(c.title, 0.3) for c in candidates}

    def judge(self, profile, candidates, aspects, *, timeout_s):
        return {c.key: {a: RerankAnswer(self.scores.get(c.title, 0.5), 0.8) for a in aspects} for c in candidates}


class Failing(Table):
    model = "failing-judge"

    def judge(self, profile, candidates, aspects, *, timeout_s):
        raise RerankError("down")


def make(compiled, judge):
    cfg = load_v2_config(CONFIG_DIR)
    return RecommenderV2.from_v1(build_recommender(compiled, fx.RECIPES), cfg, judge=judge)


USERS = {
    "plain": UserContext(skill_level=1),
    "crustacean": UserContext(allergen_groups=frozenset({"crustacean_bundle"}), skill_level=2,
                              preferences=(Preference("ingredient", "mushroom", 1),),
                              tastes=(TastePreference("spicy", preferred_level=1, max_level=2),)),
    "hard_kimchi": UserContext(preferences=(Preference("ingredient", "kimchi", -1, is_hard=True),)),
}
REQUESTS = {
    "random": V2Request("random", seed=7, limit=6),
    "pantry": V2Request("pantry", pantry=frozenset({"potato", "mushroom", "rice", "cucumber"}), limit=8),
    "dish": V2Request("dish", query="감자 조림", limit=5),
}
JUDGES = {"rules": None, "jev": Table({"감자조림": 0.9, "버섯볶음": 0.7}), "fail": Failing()}


def same(a, b):
    assert [(i.item.recipe_id, i.group, i.item.score, dict(i.item.breakdown)) for i in a.items] == \
           [(i.item.recipe_id, i.group, i.item.score, dict(i.item.breakdown)) for i in b.items]
    assert a.exclusions == b.exclusions and a.exclusion_summary == b.exclusion_summary
    assert (a.ranking, a.notes, a.seed, a.rerank_model) == (b.ranking, b.notes, b.seed, b.rerank_model)


@pytest.mark.parametrize("judge_name", JUDGES)
@pytest.mark.parametrize("mode", REQUESTS)
@pytest.mark.parametrize("user_name", USERS)
def test_trace_matches_recommend_and_is_consistent(compiled, judge_name, mode, user_name):
    v2 = make(compiled, JUDGES[judge_name])
    user, req = USERS[user_name], REQUESTS[mode]
    plain = v2.recommend(user, req)
    result, t = v2.trace(user, req)
    same(plain, result)

    passed = [rid for rid, ok in t.checked if ok]
    assert {rid for rid, ok in t.checked if not ok} == {e.recipe_id for e in result.exclusions}
    assert len({rid for rid, _ in t.checked}) == len(t.checked)  # 한 경로에서 한 번씩만 확인
    shown = [i.item.recipe_id for i in result.items]
    ranked = [rid for rid, _, _ in t.ranked]
    assert set(shown) <= set(ranked) <= set(t.pool) <= set(passed)
    assert t.ranking == result.ranking and t.mode == mode

    if judge_name == "jev":
        assert t.ranking == "jev" and t.judge is not None and not t.judge.failed and not t.jev_failed
        assert [t.judge.recipe_of[c.key] for c in t.judge.candidates] == t.pool
        for rid, score, breakdown in t.ranked:  # 순위 단계 출력 = Jev 답의 가중 평균
            key = next(k for k, r in t.judge.recipe_of.items() if r == rid)
            ans = t.judge.answers[key]
            w = t.judge.weights
            assert score == pytest.approx(sum(w[a] * s for a, (s, _) in ans.items()) / sum(w[a] for a in ans))
            assert breakdown["J_conf"] == pytest.approx(min(c for _, c in ans.values()))
    elif judge_name == "fail":
        assert t.jev_failed and t.ranking == "rules" and t.failed_judge is not None and t.failed_judge.failed
        assert t.judge is None
    else:
        assert not t.jev_failed and t.judge is None and t.ranking == "rules"

    if mode == "random":
        assert t.seed == result.seed == 7
    if mode == "pantry":
        assert t.pantry == req.pantry and req.pantry <= t.from_pantry <= t.owned
        assert set(t.groups["ready"]) | set(t.groups["near"]) >= set(t.pool)
        for i in result.items:
            assert i.item.recipe_id in t.groups[i.group]
            assert t.missing[i.item.recipe_id] == i.required_missing


def test_judge_profile_never_carries_allergy_or_hard_dislike(compiled):
    v2 = make(compiled, Table())
    user = replace(USERS["crustacean"], preferences=(Preference("ingredient", "kimchi", -1, is_hard=True),),
                   pantry=frozenset({"potato", "shrimp_raw"}))
    _, t = v2.trace(user, V2Request("pantry"))
    sent = repr(t.judge.profile) + repr(t.judge.candidates)
    for word in ("shrimp", "crustacean", "kimchi", "새우", "갑각류", "김치"):
        assert word not in sent


def test_dish_similarity_matches_scorer(compiled):
    v2 = make(compiled, None)
    _, t = v2.trace(UserContext(), REQUESTS["dish"])
    recipes, titles = v2.catalog()
    snap = v2.knowledge.snapshot()
    q = parse_query(snap, v2.config, "감자 조림", recipes, titles)
    assert t.query == q and t.active
    scorer = DishScorer(snap, v2.config, q, titles, v2.not_spicy())
    for r in recipes:
        comps = scorer.components(r)
        s = combine(comps, v2.config.dish_similarity, t.active)
        if s > 0:
            got_s, parts = t.similarity[r.id]
            assert got_s == pytest.approx(s) and parts == {k: comps[k] for k in t.active if k in comps}
        else:
            assert r.id not in t.similarity


def test_recommend_does_not_collect(compiled, monkeypatch):
    v2 = make(compiled, Table())
    calls = []
    original = RecommenderV2._execute
    monkeypatch.setattr(RecommenderV2, "_execute",
                        lambda self, u, r, c: calls.append(c) or original(self, u, r, c))
    v2.recommend(UserContext(), REQUESTS["dish"])
    assert calls == [None]
