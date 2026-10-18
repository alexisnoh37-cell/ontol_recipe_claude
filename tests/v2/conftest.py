"""v2 단위 테스트 공통: 알레르기 fixture 지식·레시피를 그대로 쓴다(컴파일러 통과)."""

from __future__ import annotations

import pytest

from kb import KnowledgeSources, compile
from tests.allergy import fixtures as fx


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
