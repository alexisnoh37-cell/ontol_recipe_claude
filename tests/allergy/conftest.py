"""알레르기 회귀 테스트 공통 준비. 지식은 kb.compile을 통과시켜 만든다."""

from __future__ import annotations

import pytest

from engine.model import RecommendRequest, RecommendResult, UserContext
from kb import KnowledgeSources, compile
from tests.allergy import fixtures as fx
from tests.support.engine_fixtures import build_recommender

# 모든 레시피가 결과에 들어갈 수 있도록 넉넉하게 요청한다(순위·개수 제한 때문에 빠지지 않게).
REQUEST = RecommendRequest(limit=len(fx.RECIPES) + 10)


@pytest.fixture(scope="session")
def compiled():
    return compile(
        KnowledgeSources(
            allergens={"groups": fx.GROUPS, "bundles": fx.BUNDLES},
            vocab=fx.VOCAB,
            ingredients=(("allergy_fixture", fx.INGREDIENTS),),
            substitutes=fx.SUBSTITUTES,
            pantry_staples={"staples": fx.STAPLES},
        )
    )


@pytest.fixture(scope="session")
def recommend(compiled):
    recommender = build_recommender(compiled, fx.RECIPES)

    def run(user: UserContext, req: RecommendRequest = REQUEST) -> RecommendResult:
        return recommender.recommend(user, req)

    return run
