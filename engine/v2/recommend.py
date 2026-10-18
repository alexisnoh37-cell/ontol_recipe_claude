"""추천 v2 진입점 (docs/plan.md 부록 G-3·G-4).

순서는 항상 v2 규칙 필터 → 형태별 후보·점수 → (Jev 재정렬)이다. 재정렬은 필터를 통과한 목록 안에서 순서만 바꾸고,
목록에 없는 후보를 더하거나 제외된 레시피를 되살리지 않는다. Jev가 실패하면 규칙 순위로 돌아간다.

  random  필터를 통과한 전체에서 seed로 균등 추출(Jev 없음)
  pantry  v1 후보 생성 → 필터 → 꼭 필요한 재료 부족 수로 ready(0)·near(1~near_max_missing) 묶음, 묶음 안 v1 점수 순
  dish    필터를 통과한 전체 → 유사도 S 상위 pool_size → s_weight·S + (1 − s_weight)·v1 점수
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from engine.browse import REQUIRED_ROLES
from engine.candidates import Candidate, candidate_roles, generate_candidates, match_lines, owned_ingredients
from engine.config import EngineConfig, ScoringConfig
from engine.explain import build_item
from engine.filters import UserConstraints
from engine.model import Exclusion, Recipe, RecommendRequest, UserContext
from engine.normalize import clean_pantry, normalize_term
from engine.ports import KnowledgeRepository
from engine.scoring import UserScorer, diversify, rank
from engine.v2.config import TASTE_DIMENSIONS, V2Config
from engine.v2.filters import check_v2
from engine.v2.model import (
    NOTE_DISH_NO_MATCH,
    NOTE_DISLIKE_POSSIBLE,
    NOTE_RERANK_OFF,
    NOTE_RERANK_UNAVAILABLE,
    Group,
    V2Item,
    V2Request,
    V2Result,
)
from engine.v2.ports import CatalogRepository, RerankCandidate, Reranker, RerankError, RerankQuery
from engine.v2.similarity import DishScorer, combine, parse_query

DEFAULT_LIMIT = 10
MAX_MAIN_NAMES = 8  # Jev에 보내는 후보 요약의 주재료 이름 수


@dataclass
class _Ranked:
    candidate: Candidate
    score: float
    breakdown: dict[str, float]


class RecommenderV2:
    def __init__(self, knowledge: KnowledgeRepository, recipes: CatalogRepository, engine_config: EngineConfig,
                 config: V2Config, reranker: Reranker | None = None):
        self.knowledge = knowledge
        self.recipes = recipes
        self.engine_config = engine_config
        self.config = config
        self.reranker = reranker
        self.scoring = ScoringConfig.from_mapping(engine_config.weights)
        self._catalog: tuple[tuple[Recipe, ...], dict[str, str]] | None = None

    def catalog(self) -> tuple[tuple[Recipe, ...], dict[str, str]]:
        """추천할 수 있는 레시피(id 순)와 정규화한 제목. 레시피 공급원은 인스턴스 동안 바뀌지 않으므로 한 번만 만든다."""
        if self._catalog is None:
            serve_draft = self.engine_config.serve_draft_recipes
            recipes = tuple(sorted((r for r in self.recipes.all() if r.status == "published" or serve_draft),
                                   key=lambda r: r.id))
            self._catalog = (recipes, {r.id: normalize_term(r.title) for r in recipes})
        return self._catalog

    @classmethod
    def from_v1(cls, v1, config: V2Config, reranker: Reranker | None = None) -> RecommenderV2:
        """v1 Recommender와 같은 지식·레시피·설정을 쓴다(v1 공급원 InMemoryRecipeRepository는 all()이 있다)."""
        return cls(v1.knowledge, v1.recipes, v1.config, config, reranker)

    def recommend(self, user: UserContext, req: V2Request) -> V2Result:
        """모르는 알레르기 그룹·재료 id, dish의 빈 질의면 ValueError(v1과 같이 조용히 꺼지지 않게)."""
        if req.mode == "dish" and not (req.query and req.query.strip()):
            raise ValueError("요리 찾기(dish)에는 질의(query)가 필요합니다")
        run = _Run(self, user, req)
        if req.mode == "random":
            return run.run_random()
        if req.mode == "pantry":
            return run.run_pantry()
        if req.mode == "dish":
            return run.run_dish()
        raise ValueError(f"모르는 추천 형태: {req.mode}")


class _Run:
    """요청 한 번의 상태."""

    def __init__(self, owner: RecommenderV2, user: UserContext, req: V2Request):
        self.o = owner
        self.cfg = owner.config
        self.user = user
        self.req = req
        self.snapshot = owner.knowledge.snapshot()
        v1req = RecommendRequest(max_time_min=req.max_time_min, time_is_hard=req.time_is_hard, pantry=req.pantry)
        self.constraints = UserConstraints(self.snapshot, user, v1req)
        self.scorer = UserScorer(self.snapshot, owner.scoring, user, v1req)
        self.pantry = clean_pantry(self.snapshot, req.pantry if req.pantry is not None else user.pantry)
        self.owned = owned_ingredients(self.snapshot, self.pantry)
        self.exclusions: list[Exclusion] = []
        self.relaxed: dict[str, bool] = {}
        default = self.cfg.random_default_limit if req.mode == "random" else DEFAULT_LIMIT
        self.limit = req.limit if req.limit is not None else default

    # --- 공용 -----------------------------------------------------------------------------------------

    def passes(self, recipe: Recipe) -> bool:
        found = check_v2(self.constraints, recipe)
        if found.exclusions:
            self.exclusions.extend(found.exclusions)
            return False
        if found.relaxed:
            self.relaxed[recipe.id] = True
        return True

    def candidate(self, recipe: Recipe) -> Candidate:
        lines = match_lines(self.snapshot, recipe, self.pantry, self.owned, self.constraints.is_unsafe_ingredient,
                            self.o.scoring.substitute_credit)
        return Candidate(recipe, lines)

    def scored(self, candidate: Candidate) -> _Ranked:
        s = self.scorer.score(candidate)
        return _Ranked(candidate, s.score, dict(s.breakdown))

    def item(self, r: _Ranked, group: Group | None = None) -> V2Item:
        base = build_item(self.snapshot, r.candidate, r.score, r.breakdown)
        notes = (NOTE_DISLIKE_POSSIBLE,) if self.relaxed.get(r.candidate.recipe.id) else ()
        return V2Item(base, group, required_missing(r.candidate), notes)

    def result(self, items: Sequence[V2Item], *, seed: int | None = None, rerank_used: bool = False,
               notes: Sequence[str] = ()) -> V2Result:
        return V2Result(
            mode=self.req.mode, items=tuple(items), exclusions=tuple(self.exclusions),
            exclusion_summary=_summary(self.exclusions), seed=seed, rerank_used=rerank_used,
            rerank_model=self.o.reranker.model if rerank_used and self.o.reranker else None,
            notes=tuple(dict.fromkeys(notes)),
        )

    # --- 형태 -----------------------------------------------------------------------------------------

    def run_random(self) -> V2Result:
        """seed로 섞은 순서대로 필터에 걸어 limit개를 채우면 멈춘다(통과한 레시피 중 균등 추출과 같다).
        제외 기록은 확인한 레시피에 대해서만 남는다."""
        seed = self.req.seed if self.req.seed is not None else random.SystemRandom().randrange(2**31)
        order = list(self.o.catalog()[0])
        random.Random(seed).shuffle(order)
        chosen: list[Recipe] = []
        for recipe in order:
            if len(chosen) >= self.limit:
                break
            if self.passes(recipe):
                chosen.append(recipe)
        return self.result([self.item(self.scored(self.candidate(r))) for r in chosen], seed=seed)

    def run_pantry(self) -> V2Result:
        candidates = generate_candidates(
            self.snapshot, self.o.recipes, self.pantry, self.constraints.is_unsafe_ingredient,
            default_ratio=self.o.scoring.substitute_credit, serve_draft_recipes=self.o.engine_config.serve_draft_recipes,
        )
        groups: dict[Group, list[Candidate]] = {"ready": [], "near": []}
        for c in sorted(candidates, key=lambda c: c.recipe.id):
            if not self.passes(c.recipe):
                continue
            missing = required_missing(c)
            if missing == 0:
                groups["ready"].append(c)
            elif missing <= self.cfg.near_max_missing:
                groups["near"].append(c)
        names: tuple[Group, Group] = ("ready", "near")
        ordered = [[_Ranked(s.candidate, s.score, dict(s.breakdown))
                    for s in diversify(rank([self.scorer.score(c) for c in groups[g]]), self.o.scoring)]
                   for g in names]
        # limit 밖으로 밀려날 near는 Jev에 보내지 않는다(ready가 limit을 채우면 near 재정렬은 결과에 영향이 없다)
        room = max(0, self.limit - len(ordered[0]))
        ordered[1], rest = ordered[1][:room], ordered[1][room:]
        ordered, used, note = self.rerank("pantry", ordered)
        ordered[1] += rest
        items = [self.item(r, g) for g, rs in zip(names, ordered, strict=True) for r in rs]
        return self.result(items[: self.limit], rerank_used=used, notes=[note] if note else [])

    def run_dish(self) -> V2Result:
        """유사도 S를 먼저 계산하고, S가 높은 순으로 필터에 걸어 pool_size개를 채운다.
        제외 기록은 확인한 레시피(S > 0, pool을 채울 때까지)에 대해서만 남는다."""
        query_text = (self.req.query or "").strip()
        all_recipes, titles = self.o.catalog()
        query = parse_query(self.snapshot, self.cfg, query_text, all_recipes, titles)
        scorer = DishScorer(self.snapshot, self.cfg, query, titles)
        comps = [(r, scorer.components(r)) for r in all_recipes]
        active = [k for k in ("ingredient", "keyword", "anchor") if comps and k in comps[0][1]]
        if any(c["title"] > 0 for _, c in comps):
            active.insert(0, "title")
        if not active:
            return self.result([], notes=[NOTE_DISH_NO_MATCH])
        weights = self.cfg.dish_similarity
        scored = [(combine(c, weights, active), r) for r, c in comps]
        pool: list[tuple[float, Recipe]] = []
        for s, recipe in sorted((x for x in scored if x[0] > 0), key=lambda x: (-x[0], x[1].id)):
            if len(pool) >= self.cfg.dish_pool_size:
                break
            if self.passes(recipe):
                pool.append((s, recipe))
        if not pool:
            return self.result([], notes=[NOTE_DISH_NO_MATCH])
        sw = self.cfg.dish_s_weight
        ranked: list[_Ranked] = []
        for s, recipe in pool:
            r = self.scored(self.candidate(recipe))
            r.breakdown["S"] = s
            r.score = sw * s + (1 - sw) * r.score
            ranked.append(r)
        ranked.sort(key=lambda r: (-round(r.score, 6), r.candidate.recipe.id))
        (ordered,), used, note = self.rerank("dish", [ranked])
        items = [self.item(r) for r in ordered[: self.limit]]
        return self.result(items, rerank_used=used, notes=[note] if note else [])

    # --- Jev 재정렬 -----------------------------------------------------------------------------------

    def rerank(self, kind: str, groups: list[list[_Ranked]]) -> tuple[list[list[_Ranked]], bool, str | None]:
        """묶음마다 상위 top_n을 한 번의 Jev 요청으로 보내고, 묶음 안에서만 Jev 점수(J)를 섞어 다시 정렬한다.
        목록 구성과 묶음 경계는 바꾸지 않는다."""
        if not any(groups):
            return groups, False, None
        enabled = self.cfg.rerank_enabled if self.req.rerank is None else self.req.rerank
        reranker = self.o.reranker
        if not enabled or reranker is None:
            return groups, False, NOTE_RERANK_OFF
        top_n = self.cfg.rerank_top_n
        keyed: list[list[tuple[str, _Ranked]]] = []
        n = 0
        for g in groups:
            keyed.append([(f"c{n + i}", r) for i, r in enumerate(g[:top_n])])
            n += len(keyed[-1])
        query = RerankQuery(
            kind=kind,  # type: ignore[arg-type]
            candidates=tuple(self.summary(k, r.candidate.recipe) for head in keyed for k, r in head),
            query=(self.req.query or "").strip() or None if kind == "dish" else None,
            skill_level=self.user.skill_level,
            taste_preferences=_taste_preferences(self.user),
        )
        try:
            answers = reranker.rerank(query, timeout_s=self.cfg.rerank_timeout_ms / 1000)
        except RerankError:
            return groups, False, NOTE_RERANK_UNAVAILABLE
        except Exception:  # noqa: BLE001  구현 결함이어도 추천은 규칙 순위로 계속한다(안전 쪽)
            return groups, False, NOTE_RERANK_UNAVAILABLE
        if not isinstance(answers, Mapping):
            return groups, False, NOTE_RERANK_UNAVAILABLE
        w = self.cfg.rerank_jev_weight
        out: list[list[_Ranked]] = []
        for g, head in zip(groups, keyed, strict=True):
            mixed: list[tuple[float, int, _Ranked]] = []
            for i, (key, r) in enumerate(head):
                ans = answers.get(key)
                if ans is not None and _finite01(getattr(ans, "score", None))                         and _finite01(getattr(ans, "confidence", None))                         and ans.confidence >= self.cfg.rerank_min_confidence:
                    r = replace(r, breakdown={**r.breakdown, "J": ans.score, "J_conf": ans.confidence},
                                score=(1 - w) * r.score + w * ans.score)
                mixed.append((r.score, i, r))
            mixed.sort(key=lambda x: (-round(x[0], 6), x[1]))
            out.append([r for _, _, r in mixed] + g[top_n:])
        return out, True, None

    def summary(self, key: str, recipe: Recipe) -> RerankCandidate:
        names = self.snapshot.ingredient_names
        roles = candidate_roles(recipe)
        mains = tuple(dict.fromkeys(names[line.ingredient_id] for line in recipe.ingredients
                                    if line.role in roles and line.ingredient_id in names))[:MAX_MAIN_NAMES]
        taste = None if recipe.taste is None else {d: getattr(recipe.taste, d) for d in TASTE_DIMENSIONS}
        return RerankCandidate(key, recipe.title, recipe.cuisine, taste, mains)


def required_missing(candidate: Candidate) -> int:
    """꼭 필요한 줄(선택이 아닌 main·sub·seasoning) 중 보유·기본 양념·대체재로 채우지 못한 줄 수(미매칭 포함)."""
    return sum(1 for m in candidate.lines
               if m.status == "missing" and m.line.role in REQUIRED_ROLES and not m.line.optional)


def _taste_preferences(user: UserContext) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for t in user.tastes:
        entry = out.setdefault(t.dimension, {})
        if t.preferred_level is not None:
            entry.setdefault("preferred", t.preferred_level)
        if t.max_level is not None:
            entry["max"] = min(t.max_level, entry.get("max", t.max_level))
    return {d: v for d, v in out.items() if v}


def _finite01(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and 0.0 <= float(x) <= 1.0


def _summary(exclusions: list[Exclusion]) -> dict[str, int]:
    pairs = {(e.reason.value, e.recipe_id) for e in exclusions}
    out: dict[str, int] = {}
    for reason, _ in sorted(pairs):
        out[reason] = out.get(reason, 0) + 1
    return out


__all__ = ["RecommenderV2", "required_missing"]
