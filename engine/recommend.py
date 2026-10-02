"""추천 파이프라인 진입점: 후보 → 제약 필터 → 점수 → 다양성 → 설명 (docs/plan.md 4장).

Phase 0-3에서는 인터페이스만 정의한다. 구현은 Phase 1-1(필터), 1-2(점수)에서 한다.
"""

from __future__ import annotations

from engine.config import EngineConfig
from engine.model import RecommendRequest, RecommendResult, UserContext
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
        """
        raise NotImplementedError("추천 엔진은 Phase 1-1에서 구현한다")
