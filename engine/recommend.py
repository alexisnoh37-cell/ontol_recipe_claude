"""추천 파이프라인 진입점: 후보 → 제약 필터 → 점수 → 다양성 → 설명 (docs/plan.md 4장).

Phase 1-1은 후보와 필터까지 구현한다. 점수(1-2) 전까지 정렬은 레시피 id 순이고,
score는 0, breakdown은 빈 값이다.
"""

from __future__ import annotations

from engine.candidates import generate_candidates
from engine.config import EngineConfig
from engine.explain import build_item
from engine.filters import UserConstraints
from engine.model import Exclusion, RecommendRequest, RecommendResult, UserContext
from engine.normalize import clean_pantry
from engine.ports import KnowledgeRepository, RecipeRepository


class Recommender:
    def __init__(self, knowledge: KnowledgeRepository, recipes: RecipeRepository, config: EngineConfig):
        self.knowledge = knowledge
        self.recipes = recipes
        self.config = config

    def recommend(self, user: UserContext, req: RecommendRequest) -> RecommendResult:
        """추천 결과(items)와 제외 목록(exclusions)을 돌려준다.

        약속(tests/allergy/가 검증):
          - 알레르기 closure에 걸리는 재료가 하나라도 있으면 제외한다. 선택 재료, 고명, 기본 양념도 포함.
            certainty가 possible이어도 제외한다.
          - 알레르기가 있는 사용자에게 미매칭 재료가 있는 레시피는 제외한다.
          - 절대 불선호 재료는 contains(is_a 하위, derived_from 파생)까지 제외한다.
          - 대체 안내는 사용자의 알레르기 closure와 절대 불선호로 거른다.
          - 제외할 때마다 Exclusion(사유 코드, 걸린 재료, 대상, certainty, 근거 경로)을 남긴다.

        모르는 알레르기 그룹이나 절대 불선호 재료가 오면 ValueError(필터가 조용히 꺼지지 않게).
        """
        snapshot = self.knowledge.snapshot()
        constraints = UserConstraints(snapshot, user, req)
        pantry = clean_pantry(snapshot, req.pantry if req.pantry is not None else user.pantry)

        candidates = generate_candidates(
            snapshot, self.recipes, pantry, constraints.is_unsafe_ingredient,
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

        # 임시 정렬: 점수 엔진(1-2) 전까지 레시피 id 순
        passed.sort(key=lambda c: c.recipe.id)
        items = tuple(build_item(snapshot, c, score=0.0, breakdown={}) for c in passed[: req.limit])
        return RecommendResult(items=items, exclusions=tuple(exclusions))
