"""추천 v2 진입점 (docs/plan.md 부록 G-3·G-4·G-12).

순위 방식(config/v2.yaml ranking.mode, D10)
  jev    제외(규칙) → 관련 후보만 규칙으로 고름(순위에 쓰지 않음) → 순위·항목별 점수는 Jev가 정함.
         요리 찾기에서 관련 후보가 min_pool보다 적으면 Jev가 제외를 통과한 레시피 전체를 걸러 보충한다.
         Jev가 주입되지 않았거나, 요청에서 껐거나(rerank=False), 실패하면 아래 rules로 돌아간다.
  rules  아래 설명대로 규칙 점수(+ Reranker 재정렬).

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
from engine.scoring import Scored, UserScorer, diversify, rank
from engine.v2.config import TASTE_DIMENSIONS, V2Config
from engine.v2.filters import check_v2
from engine.v2.model import (
    NOTE_DISH_EXCLUDED,
    NOTE_JEV_SCREENED,
    NOTE_JEV_UNAVAILABLE,
    NOTE_DISH_NO_MATCH,
    NOTE_DISLIKE_POSSIBLE,
    NOTE_RERANK_OFF,
    NOTE_RERANK_UNAVAILABLE,
    NOTE_SPICY_INFERRED,
    Group,
    V2Item,
    V2Request,
    V2Result,
)
from engine.v2.ports import (
    Aspect,
    CatalogRepository,
    Judge,
    JudgeCandidate,
    JudgeProfile,
    RerankCandidate,
    Reranker,
    RerankError,
    RerankQuery,
)
from engine.v2.similarity import DishScorer, combine, parse_query
from engine.v2.spicy import not_spicy_ids

DEFAULT_LIMIT = 10
MAX_MAIN_NAMES = 8  # Jev에 보내는 후보 요약의 주재료 이름 수


@dataclass
class _Ranked:
    candidate: Candidate
    score: float
    breakdown: dict[str, float]


class RecommenderV2:
    def __init__(self, knowledge: KnowledgeRepository, recipes: CatalogRepository, engine_config: EngineConfig,
                 config: V2Config, reranker: Reranker | None = None, judge: Judge | None = None):
        self.knowledge = knowledge
        self.judge = judge
        self.recipes = recipes
        self.engine_config = engine_config
        self.config = config
        self.reranker = reranker
        self.scoring = ScoringConfig.from_mapping(engine_config.weights)
        self._catalog: tuple[tuple[Recipe, ...], dict[str, str]] | None = None
        self._not_spicy: frozenset[str] | None = None

    def not_spicy(self) -> frozenset[str]:
        """맛 정보는 없지만 매운맛 0으로 추정한 레시피 id(D9). 설정에서 끄면 비어 있다. 인스턴스마다 한 번 계산."""
        if self._not_spicy is None:
            cfg = self.config
            self._not_spicy = (not_spicy_ids(self.knowledge.snapshot(), self.recipes.all(), cfg.spicy_markers,
                                             cfg.spicy_title_markers)
                               if cfg.spicy_inference_enabled else frozenset())
        return self._not_spicy

    def catalog(self) -> tuple[tuple[Recipe, ...], dict[str, str]]:
        """추천할 수 있는 레시피(id 순)와 정규화한 제목. 레시피 공급원은 인스턴스 동안 바뀌지 않으므로 한 번만 만든다."""
        if self._catalog is None:
            serve_draft = self.engine_config.serve_draft_recipes
            recipes = tuple(sorted((r for r in self.recipes.all() if r.status == "published" or serve_draft),
                                   key=lambda r: r.id))
            self._catalog = (recipes, {r.id: normalize_term(r.title) for r in recipes})
        return self._catalog

    @classmethod
    def from_v1(cls, v1, config: V2Config, reranker: Reranker | None = None,
                judge: Judge | None = None) -> RecommenderV2:
        """v1 Recommender와 같은 지식·레시피·설정을 쓴다(v1 공급원 InMemoryRecipeRepository는 all()이 있다)."""
        return cls(v1.knowledge, v1.recipes, v1.config, config, reranker, judge)

    def recommend(self, user: UserContext, req: V2Request) -> V2Result:
        """모르는 알레르기 그룹·재료 id, dish의 빈 질의면 ValueError(v1과 같이 조용히 꺼지지 않게)."""
        if req.mode == "dish" and not (req.query and req.query.strip()):
            raise ValueError("요리 찾기(dish)에는 질의(query)가 필요합니다")
        if req.mode not in ("random", "pantry", "dish"):
            raise ValueError(f"모르는 추천 형태: {req.mode}")
        run = _Run(self, user, req)
        if run.use_jev:
            result = getattr(run, f"jev_{req.mode}")()
            if result is not None:
                return result
            run = _Run(self, user, req)  # Jev 실패: 규칙 경로로 처음부터(제외 기록이 겹치지 않게)
            run.fallback_note = NOTE_JEV_UNAVAILABLE
        return getattr(run, f"run_{req.mode}")()


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
        self.from_pantry = owned_ingredients(self.snapshot, self.pantry, include_staples=False)
        self.exclusions: list[Exclusion] = []
        self.relaxed: dict[str, bool] = {}
        self.not_spicy = owner.not_spicy()
        self.spicy_pref = next((t.preferred_level for t in user.tastes
                                if t.dimension == "spicy" and t.preferred_level is not None), None)
        # Jev 취향 질문에 쓰는 매운맛 선호. 5(최대)는 '한도 없음'으로만 보고 취향으로 묻지 않는다(D10 보완)
        self.jev_spicy_pref = self.spicy_pref if self.spicy_pref is not None and self.spicy_pref < 5 else None
        self.taste_dims = {t.dimension for t in user.tastes if t.preferred_level is not None}
        self.cares_spicy = any(t.dimension == "spicy" for t in user.tastes)
        default = self.cfg.random_default_limit if req.mode == "random" else DEFAULT_LIMIT
        self.limit = req.limit if req.limit is not None else default
        self.use_jev = self.cfg.ranking_mode == "jev" and owner.judge is not None and req.rerank is not False
        self.fallback_note: str | None = None

    # --- 공용 -----------------------------------------------------------------------------------------

    def passes(self, recipe: Recipe) -> bool:
        found = check_v2(self.constraints, recipe, not_spicy=recipe.id in self.not_spicy)
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
        return self.adjust_taste(_Ranked(candidate, s.score, dict(s.breakdown)))

    def adjust_taste(self, r: _Ranked) -> _Ranked:
        """맛 선호가 매운맛 하나뿐이고 레시피를 매운맛 0으로 추정했으면, '모름'(중간값) 대신 T를 계산한다(D9)."""
        if (r.candidate.recipe.id in self.not_spicy and self.spicy_pref is not None
                and self.taste_dims == {"spicy"}):
            new_t = max(0.0, 1.0 - self.spicy_pref / 5.0)
            r.score += self.o.scoring.weights["T"] * (new_t - r.breakdown["T"])
            r.breakdown["T"] = new_t
        return r

    def item(self, r: _Ranked, group: Group | None = None) -> V2Item:
        base = build_item(self.snapshot, r.candidate, r.score, r.breakdown)
        rid = r.candidate.recipe.id
        notes = ((NOTE_DISLIKE_POSSIBLE,) if self.relaxed.get(rid) else ()) +                 ((NOTE_SPICY_INFERRED,) if self.cares_spicy and rid in self.not_spicy else ())
        return V2Item(base, group, required_missing(r.candidate), notes)

    def result(self, items: Sequence[V2Item], *, seed: int | None = None, rerank_used: bool = False,
               notes: Sequence[str] = (), ranking: str = "rules") -> V2Result:
        if ranking == "jev":
            model = self.o.judge.model if self.o.judge else None
        else:
            model = self.o.reranker.model if rerank_used and self.o.reranker else None
        if self.fallback_note:
            notes = [self.fallback_note, *notes]
        return V2Result(
            mode=self.req.mode, items=tuple(items), exclusions=tuple(self.exclusions),
            exclusion_summary=_summary(self.exclusions), seed=seed, rerank_used=rerank_used,
            rerank_model=model, notes=tuple(dict.fromkeys(notes)), ranking=ranking,
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

    def pantry_groups(self) -> dict[Group, list[Candidate]]:
        """v1 후보 생성 → 필터 → 꼭 필요한 재료 부족 수로 ready(0)·near(1~near_max_missing). 더 부족하면 버린다."""
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
        return groups

    def run_pantry(self) -> V2Result:
        groups = self.pantry_groups()
        names: tuple[Group, Group] = ("ready", "near")
        ordered: list[list[_Ranked]] = []
        for g in names:
            adjusted = [self.scored(c) for c in groups[g]]  # 매운맛 추정 T 보정을 정렬 전에 반영
            ranked = rank([Scored(r.candidate, r.score, r.breakdown) for r in adjusted])
            ordered.append([_Ranked(s.candidate, s.score, dict(s.breakdown))
                            for s in diversify(ranked, self.o.scoring)])
        # limit 밖으로 밀려날 near는 Jev에 보내지 않는다(ready가 limit을 채우면 near 재정렬은 결과에 영향이 없다)
        room = max(0, self.limit - len(ordered[0]))
        ordered[1], rest = ordered[1][:room], ordered[1][room:]
        ordered, used, note = self.rerank("pantry", ordered)
        ordered[1] += rest
        items = [self.item(r, g) for g, rs in zip(names, ordered, strict=True) for r in rs]
        return self.result(items[: self.limit], rerank_used=used, notes=[note] if note else [])

    def dish_pool(self) -> tuple[list[tuple[float, Recipe]], float]:
        """유사도 S를 먼저 계산하고, S가 높은 순으로 필터에 걸어 pool_size개를 채운다. 반환: (pool, 제외된 것 중 최고 S).
        제외 기록은 확인한 레시피(S > 0, pool을 채울 때까지)에 대해서만 남는다."""
        query_text = (self.req.query or "").strip()
        all_recipes, titles = self.o.catalog()
        query = parse_query(self.snapshot, self.cfg, query_text, all_recipes, titles)
        scorer = DishScorer(self.snapshot, self.cfg, query, titles, self.not_spicy)
        comps = [(r, scorer.components(r)) for r in all_recipes]
        active = [k for k in ("ingredient", "keyword", "anchor") if comps and k in comps[0][1]]
        if any(c["title"] > 0 for _, c in comps):
            active.insert(0, "title")
        if not active:
            return [], 0.0
        weights = self.cfg.dish_similarity
        scored = [(combine(c, weights, active), r) for r, c in comps]
        pool: list[tuple[float, Recipe]] = []
        best_excluded = 0.0  # 제외된 레시피 중 가장 높은 S(찾는 요리가 못 먹는 재료 때문에 빠졌는지 알리려고)
        for s, recipe in sorted((x for x in scored if x[0] > 0), key=lambda x: (-x[0], x[1].id)):
            if len(pool) >= self.cfg.dish_pool_size:
                break
            if self.passes(recipe):
                pool.append((s, recipe))
            else:
                best_excluded = max(best_excluded, s)
        return pool, best_excluded

    def run_dish(self) -> V2Result:
        pool, best_excluded = self.dish_pool()
        if not pool:
            return self.result([], notes=[NOTE_DISH_EXCLUDED if best_excluded else NOTE_DISH_NO_MATCH])
        excluded_note = [NOTE_DISH_EXCLUDED] if best_excluded > pool[0][0] else []
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
        return self.result(items, rerank_used=used, notes=excluded_note + ([note] if note else []))

    # --- Jev 판단 경로(D10) ---------------------------------------------------------------------------
    # 각 jev_* 는 Jev가 실패하면 None을 돌려준다(호출자가 규칙 경로로 다시 실행한다).

    def jev_random(self) -> V2Result | None:
        """seed로 섞은 순서대로 필터에 걸어 pool_size개를 모으고, Jev가 취향에 맞게 고른다."""
        seed = self.req.seed if self.req.seed is not None else random.SystemRandom().randrange(2**31)
        order = list(self.o.catalog()[0])
        random.Random(seed).shuffle(order)
        pool: list[Recipe] = []
        for recipe in order:
            if len(pool) >= max(self.cfg.ranking_pool_size, self.limit):
                break
            if self.passes(recipe):
                pool.append(recipe)
        judged = self.judged([self.candidate(r) for r in pool])
        if judged is None:
            return None
        return self.result([self.item(r) for r in judged[: self.limit]], seed=seed, rerank_used=bool(judged),
                           ranking="jev")

    def jev_pantry(self) -> V2Result | None:
        """지금 바로·조금만 사면 묶음(사실)은 규칙으로 나누고, 묶음 안 순서만 Jev가 정한다.
        묶음이 크면 가진 재료를 많이 쓰는 순(후보 고르기용, 점수 아님)으로 pool_size개만 Jev에 보낸다."""
        groups = self.pantry_groups()
        size = self.cfg.ranking_pool_size
        pools = {g: sorted(cs, key=lambda c: (-self.uses_pantry(c), c.recipe.id)) for g, cs in groups.items()}
        ready = pools["ready"][:size]
        near = pools["near"][: max(0, min(size, self.limit) - len(ready))]
        judged = self.judged(ready + near)
        if judged is None:
            return None
        in_ready = {c.recipe.id for c in ready}
        items = [self.item(r, "ready") for r in judged if r.candidate.recipe.id in in_ready]
        items += [self.item(r, "near") for r in judged if r.candidate.recipe.id not in in_ready]
        return self.result(items[: self.limit], rerank_used=bool(judged), ranking="jev")

    def jev_dish(self) -> V2Result | None:
        """규칙 유사도로 관련 후보를 고르고(순위에 쓰지 않음), 적으면 Jev 걸러내기로 보충한 뒤 Jev가 순위를 정한다."""
        pool, best_excluded = self.dish_pool()
        notes: list[str] = []
        if len(pool) < self.cfg.ranking_min_pool:
            have = {r.id for _, r in pool}
            rest = [r for r in self.o.catalog()[0] if r.id not in have and self.passes(r)]
            rest = rest[: self.cfg.ranking_screen_max]
            if rest:
                cands = {f"c{i}": r for i, r in enumerate(rest)}
                try:
                    scores = self.o.judge.screen(
                        self.profile(), tuple(self.brief(k, self.candidate(r)) for k, r in cands.items()),
                        timeout_s=self.cfg.ranking_timeout_ms / 1000)
                except Exception:  # noqa: BLE001  걸러내기 실패: 규칙 관련 후보만으로 진행(없으면 규칙 경로)
                    scores = None
                if isinstance(scores, Mapping) and scores:
                    # 점수 내림차순, 같으면 원래 순서(레시피 id 순). key 문자열 순서(c10 < c2)에 기대지 않는다
                    order = {k: i for i, k in enumerate(cands)}
                    picked = sorted((k for k in scores if k in cands and _finite01(scores[k])),
                                    key=lambda k: (-scores[k], order[k]))[: self.cfg.ranking_pool_size - len(pool)]
                    pool += [(0.0, cands[k]) for k in picked]
                    if picked:
                        notes.append(NOTE_JEV_SCREENED)
                elif not pool:
                    return None
        if not pool:
            return self.result([], notes=[NOTE_DISH_EXCLUDED if best_excluded else NOTE_DISH_NO_MATCH],
                               ranking="jev")
        if best_excluded > pool[0][0]:
            notes.insert(0, NOTE_DISH_EXCLUDED)
        judged = self.judged([self.candidate(r) for _, r in pool[: self.cfg.ranking_pool_size]])
        if judged is None:
            return None
        return self.result([self.item(r) for r in judged[: self.limit]], rerank_used=bool(judged), notes=notes,
                           ranking="jev")

    def judged(self, candidates: list[Candidate]) -> list[_Ranked] | None:
        """Jev 항목별 판단 → 가중 평균으로 정렬. breakdown은 J_<항목>, 종합 J, 가장 낮은 확신도 J_conf.
        보낸 후보 밖의 답은 버리고, 답이 빠진 후보는 0점으로 뒤에 둔다(목록 구성은 바꾸지 않는다)."""
        if not candidates:
            return []
        aspects = self.aspects()
        keyed = {f"c{i}": c for i, c in enumerate(candidates)}
        try:
            answers = self.o.judge.judge(self.profile(), tuple(self.brief(k, c) for k, c in keyed.items()), aspects,
                                         timeout_s=self.cfg.ranking_timeout_ms / 1000)
        except Exception:  # noqa: BLE001  실패·구현 결함 모두 규칙 경로로(안전 쪽)
            return None
        if not isinstance(answers, Mapping):
            return None
        weights = self.cfg.aspect_weights
        out: list[tuple[float, int, _Ranked]] = []
        for i, (key, c) in enumerate(keyed.items()):
            got = answers.get(key)
            got = got if isinstance(got, Mapping) else {}
            breakdown: dict[str, float] = {}
            total = wsum = 0.0
            confs: list[float] = []
            for a in aspects:
                ans = got.get(a)
                if ans is None or not _finite01(getattr(ans, "score", None)) \
                        or not _finite01(getattr(ans, "confidence", None)):
                    continue
                breakdown[f"J_{a}"] = ans.score
                total += weights[a] * ans.score
                wsum += weights[a]
                confs.append(ans.confidence)
            score = total / wsum if wsum else 0.0
            breakdown["J"] = score
            breakdown["J_conf"] = min(confs) if confs else 0.0
            out.append((score, i, _Ranked(c, score, breakdown)))
        if not any(len(r.breakdown) > 2 for _, _, r in out):
            return None  # 쓸 수 있는 답이 하나도 없음
        out.sort(key=lambda x: (-round(x[0], 6), x[1]))
        return [r for _, _, r in out]

    def aspects(self) -> tuple[Aspect, ...]:
        """사용자 정보가 있는 항목만 묻는다."""
        p = self.profile()
        out: list[Aspect] = []
        if self.req.mode == "dish":
            out.append("request")
        if p.spicy_preference is not None:
            out.append("taste")
        if p.liked_ingredients or p.disliked_ingredients:
            out.append("ingredients")
        if p.liked_cuisines or p.disliked_cuisines:
            out.append("cuisine")
        out.append("skill")
        if self.req.mode == "pantry":
            out.append("pantry")
        return tuple(out)

    def profile(self) -> JudgeProfile:
        """Jev에 보낼 사용자 정보. 절대 안 먹는 재료(is_hard)와 알레르기는 넣지 않는다."""
        names = self.snapshot.ingredient_names
        soft = [p for p in self.user.preferences if not p.is_hard]

        def ing(pol: int) -> tuple[str, ...]:
            return tuple(sorted(names[p.target_id] for p in soft
                                if p.target_type == "ingredient" and p.polarity == pol and p.target_id in names))

        def cui(pol: int) -> tuple[str, ...]:
            return tuple(sorted(p.target_id for p in soft if p.target_type == "cuisine" and p.polarity == pol))

        request = (self.req.query or "").strip() or None if self.req.mode == "dish" else None
        # 보유 재료 중 못 먹는 것(알레르기·절대 안 먹음에 걸리는 재료)은 보내지 않는다. 그 재료를 쓰는 레시피는 이미 제외됐다
        on_hand = (tuple(sorted(names[i] for i in self.pantry if not self.constraints.is_unsafe_ingredient(i)))
                   if self.req.mode == "pantry" else ())
        return JudgeProfile(
            skill_level=self.user.skill_level, spicy_preference=self.jev_spicy_pref,
            liked_ingredients=ing(1), disliked_ingredients=ing(-1), liked_cuisines=cui(1), disliked_cuisines=cui(-1),
            request=request, ingredients_on_hand=on_hand,
        )

    def brief(self, key: str, c: Candidate) -> JudgeCandidate:
        r = c.recipe
        names = self.snapshot.ingredient_names
        roles = candidate_roles(r)
        mains = tuple(dict.fromkeys(names[line.ingredient_id] for line in r.ingredients
                                    if line.role in roles and line.ingredient_id in names))[:MAX_MAIN_NAMES]
        spicy = r.taste.spicy if r.taste is not None else (0 if r.id in self.not_spicy else None)
        missing: tuple[str, ...] = ()
        if self.req.mode == "pantry":
            missing = tuple(dict.fromkeys(
                names.get(m.line.ingredient_id, m.line.raw_text) if m.line.ingredient_id else m.line.raw_text
                for m in c.lines if m.status == "missing" and m.line.role in REQUIRED_ROLES and not m.line.optional))
        return JudgeCandidate(key, r.title, None if r.cuisine == "미분류" else r.cuisine, spicy, r.difficulty, mains,
                              missing)

    def uses_pantry(self, c: Candidate) -> int:
        """가진 재료(기본 양념 제외)로 채운 줄 수. 후보를 고를 때만 쓴다(점수 아님)."""
        return sum(1 for m in c.lines if m.status == "owned" and m.line.ingredient_id in self.from_pantry)

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
