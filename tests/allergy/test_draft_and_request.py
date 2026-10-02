"""추가6: draft 레시피를 제공해도 알레르기 필터는 그대로다.
추가7: 보유 재료를 요청 파라미터로 넘겨도 판정이 같다.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from engine.model import ExclusionReason, RecommendRequest
from tests.allergy import fixtures as fx
from tests.allergy.checks import assert_excluded, assert_recommended
from tests.allergy.conftest import REQUEST
from tests.support.engine_fixtures import build_recommender

DRAFT = replace(
    fx._recipe("draft_saeujeot_cabbage", "배추 새우젓무침(검수 전)", ("cabbage", "main"), ("saeujeot", "seasoning")),
    status="draft",
)


@pytest.fixture(scope="module")
def draft_recommender(compiled):
    return build_recommender(compiled, [*fx.RECIPES, DRAFT], serve_draft_recipes=True)


def test_draft_recipe_still_allergy_filtered(draft_recommender):
    result = draft_recommender.recommend(fx.user("shrimp"), REQUEST)
    assert_excluded(result, "draft_saeujeot_cabbage", ExclusionReason.ALLERGEN, "saeujeot")
    assert_recommended(result, "potato_salt")


def test_control_draft_recipe_served_without_allergy(draft_recommender):
    # 대조군: serve_draft_recipes가 켜져 있으면 draft 레시피가 실제로 추천 대상이다
    assert_recommended(draft_recommender.recommend(fx.NO_ALLERGY, REQUEST), "draft_saeujeot_cabbage")


REQUEST_WITH_PANTRY = RecommendRequest(limit=REQUEST.limit, pantry=fx.PANTRY)


def test_request_pantry_same_allergy_result(recommend):
    result = recommend(fx.user("shrimp", pantry=frozenset()), REQUEST_WITH_PANTRY)
    assert_excluded(result, "kimchi_fried_rice", ExclusionReason.ALLERGEN, "kimchi")
    assert_excluded(result, "cabbage_saeujeot_soup", ExclusionReason.ALLERGEN, "saeujeot")
    assert_recommended(result, "potato_salt")


def test_request_pantry_containing_allergen_does_not_bypass(recommend):
    # 사용자가 요청에 새우젓을 보유 재료로 넣어도 새우 알레르기 판정은 그대로다
    req = RecommendRequest(limit=REQUEST.limit, pantry=fx.PANTRY | {"saeujeot", "kimchi"})
    result = recommend(fx.user("shrimp", pantry=frozenset()), req)
    assert_excluded(result, "cabbage_saeujeot_soup", ExclusionReason.ALLERGEN, "saeujeot")
    assert_excluded(result, "kimchi_fried_rice", ExclusionReason.ALLERGEN, "kimchi")


def test_control_request_pantry_without_allergy(recommend):
    assert_recommended(recommend(fx.user(pantry=frozenset()), REQUEST_WITH_PANTRY), "kimchi_fried_rice")
