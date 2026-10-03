"""추천 파이프라인 진입점: 후보 → 제약 필터 → 점수 → 다양성 → 설명 (docs/plan.md 4장)."""

from __future__ import annotations

from collections.abc import Mapping

from engine.candidates import generate_candidates
from engine.config import EngineConfig, ScoringConfig
from engine.explain import build_item
from engine.filters import UserConstraints
from engine.model import Exclusion, RecommendRequest, RecommendResult, UserContext
from engine.normalize import clean_pantry
from engine.ports import KnowledgeRepository, RecipeRepository
from engine.scoring import UserScorer, diversify, rank
from engine.trace import RecommendTrace


class Recommender:
    def __init__(self, knowledge: KnowledgeRepository, recipes: RecipeRepository, config: EngineConfig):
        self.knowledge = knowledge
        self.recipes = recipes
        self.config = config
        self.scoring = ScoringConfig.from_mapping(config.weights)  # 가중치가 없거나 형식이 틀리면 ValueError

    def recommend(self, user: UserContext, req: RecommendRequest) -> RecommendResult:
        """추천 결과(items)와 제외 목록(exclusions), 사유별 제외 수(exclusion_summary)를 돌려준다.

        약속(tests/allergy/가 검증):
          - 알레르기 closure에 걸리는 재료가 하나라도 있으면 제외한다. 선택 재료, 고명, 기본 양념도 포함.
            certainty가 possible이어도 제외한다.
          - 알레르기가 있는 사용자에게 미매칭 재료가 있는 레시피는 제외한다.
          - 절대 불선호 재료는 contains(is_a 하위, derived_from 파생)까지 제외한다.
          - 대체 안내는 사용자의 알레르기 closure와 절대 불선호로 거른다.
          - 제외할 때마다 Exclusion(사유 코드, 걸린 재료, 대상, certainty, 근거 경로)을 남긴다.
        점수는 필터를 통과한 후보에만 매긴다. 제외된 레시피는 점수와 관계없이 복귀하지 않는다.

        모르는 알레르기 그룹, 절대 불선호 재료, 선호 재료 id가 오면 ValueError(설정이 조용히 꺼지지 않게).
        """
        return self._run(user, req, collect=False)[0]

    def trace(self, user: UserContext, req: RecommendRequest) -> tuple[RecommendResult, RecommendTrace]:
        """recommend()와 같은 결과 + 단계별 중간 결과(시각화용, 부록 D-4). 같은 코드 경로를 쓴다."""
        result, trace = self._run(user, req, collect=True)
        assert trace is not None
        return result, trace

    def _run(self, user: UserContext, req: RecommendRequest, *,
             collect: bool) -> tuple[RecommendResult, RecommendTrace | None]:
        snapshot = self.knowledge.snapshot()
        constraints = UserConstraints(snapshot, user, req)
        scorer = UserScorer(snapshot, self.scoring, user, req)
        pantry = clean_pantry(snapshot, req.pantry if req.pantry is not None else user.pantry)

        candidates = generate_candidates(
            snapshot, self.recipes, pantry, constraints.is_unsafe_ingredient,
            default_ratio=self.scoring.substitute_credit,
            serve_draft_recipes=self.config.serve_draft_recipes,
        )
        passed = []
        exclusions: list[Exclusion] = []
        for candidate in candidates:
            found = constraints.check(candidate.recipe)
            if found:
                exclusions.extend(found)
            else:
                passed.append(candidate)

        ranked = rank([scorer.score(c) for c in passed])
        ordered = diversify(ranked, self.scoring)
        items = tuple(build_item(snapshot, s.candidate, s.score, s.breakdown) for s in ordered[: req.limit])
        result = RecommendResult(items=items, exclusions=tuple(exclusions), exclusion_summary=_summary(exclusions))
        if not collect:
            return result, None
        return result, RecommendTrace(
            pantry=pantry,
            pantry_staples=snapshot.pantry_staples,
            owned_from=_owned_from(snapshot.ancestors, pantry | snapshot.pantry_staples),
            allergen_groups=constraints.allergen_groups,
            hard_ingredients=constraints.hard_ingredients,
            spicy_max=constraints.spicy_max,
            max_time_min=constraints.max_time_min,
            candidates=tuple(candidates),
            ranked=tuple(ranked),
            ordered=tuple(ordered),
        )


def _owned_from(ancestors: Mapping[str, Mapping[str, int]], base: frozenset[str]) -> dict[str, tuple[str, ...]]:
    """컴파일된 ancestors 조회만(재귀 탐색 없음)."""
    out: dict[str, list[str]] = {}
    for ingredient_id in sorted(base):
        for ancestor in ancestors.get(ingredient_id, {}):
            out.setdefault(ancestor, []).append(ingredient_id)
    return {k: tuple(v) for k, v in sorted(out.items())}


def _summary(exclusions: list[Exclusion]) -> dict[str, int]:
    pairs = {(e.reason.value, e.recipe_id) for e in exclusions}
    out: dict[str, int] = {}
    for reason, _ in sorted(pairs):
        out[reason] = out.get(reason, 0) + 1
    return out
