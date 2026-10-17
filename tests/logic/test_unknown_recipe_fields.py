"""ar-1: 조리시간·난이도·맛을 모르는 레시피(식품안전나라 원본)를 엔진이 '모름'으로 다루는지.

- 매운맛 한도를 정한 사용자에게는 맛을 모르는 레시피를 제외한다(보수적).
- 시간 필터는 조리시간을 모르면 빼지 않는다.
- 점수는 config/weights.yaml의 unknown 값(중간값)으로 계산하고, 설명에 정보가 없다고 적는다.
"""

from __future__ import annotations

import pytest

from engine.model import ExclusionReason, RecommendRequest, Taste, TastePreference, UserContext
from tests.logic.test_scoring import by_id, make, recipe  # noqa: F401  (fixture snapshot·weights 재사용)
from tests.logic.test_scoring import snapshot, weights  # noqa: F401

PANTRY = frozenset({"onion", "pork"})


def unknown(id_):
    r = recipe(id_, ("pork", "main"), ("onion", "sub"))
    return r.__class__(**{**r.__dict__, "difficulty": None, "cook_time_min": None, "taste": None})


def test_unknown_taste_is_excluded_for_spicy_limit_users(snapshot, weights):
    eng = make(snapshot, [unknown("fs_x"), recipe("known", ("pork", "main"), taste=Taste(spicy=1))], weights)
    user = UserContext(pantry=PANTRY, tastes=(TastePreference("spicy", max_level=2),))
    result = eng.recommend(user, RecommendRequest(limit=10))
    assert "fs_x" not in by_id(result) and "known" in by_id(result)
    reasons = [e for e in result.exclusions if e.recipe_id == "fs_x"]
    assert [e.reason for e in reasons] == [ExclusionReason.SPICY_LIMIT] and "매운맛 정보 없음" in reasons[0].detail


def test_spicy_limit_at_max_is_not_a_limit_for_unknown_taste(snapshot, weights):
    # 한도 5(최대치)는 어떤 레시피도 넘지 않으므로 맛을 모르는 레시피도 제외하지 않는다
    eng = make(snapshot, [unknown("fs_x")], weights)
    user = UserContext(pantry=PANTRY, tastes=(TastePreference("spicy", max_level=5),))
    assert "fs_x" in by_id(eng.recommend(user, RecommendRequest(limit=10)))


def test_unknown_taste_is_kept_without_spicy_limit(snapshot, weights):
    eng = make(snapshot, [unknown("fs_x")], weights)
    assert "fs_x" in by_id(eng.recommend(UserContext(pantry=PANTRY), RecommendRequest(limit=10)))


def test_unknown_time_is_not_excluded_by_hard_time_limit(snapshot, weights):
    eng = make(snapshot, [unknown("fs_x"), recipe("slow", ("pork", "main"), cook_time_min=90)], weights)
    result = eng.recommend(UserContext(pantry=PANTRY), RecommendRequest(max_time_min=30, time_is_hard=True, limit=10))
    assert "fs_x" in by_id(result) and "slow" not in by_id(result)


@pytest.mark.parametrize("request_kw, taste_pref, expect_m, expect_t", [
    ({}, (), 1.0, 0.5),  # 희망 시간·맛 선호가 없으면 다른 레시피와 같다
    ({"max_time_min": 30}, (TastePreference("salty", preferred_level=3),), 0.5, 0.5),  # 있으면 unknown 값
])
def test_unknown_fields_score_neutral(snapshot, weights, request_kw, taste_pref, expect_m, expect_t):
    eng = make(snapshot, [unknown("fs_x")], weights)
    item = by_id(eng.recommend(UserContext(pantry=PANTRY, skill_level=3, tastes=taste_pref),
                               RecommendRequest(limit=10, **request_kw)))["fs_x"]
    assert item.breakdown["D"] == 0.5  # config/weights.yaml difficulty.unknown
    assert item.breakdown["M"] == expect_m and item.breakdown["T"] == expect_t
    assert any("조리시간, 난이도, 맛 정보가 없는 레시피입니다" in n for n in item.notes)
    assert not any("희망 시간보다 오래" in n for n in item.notes)


def test_rank_tiebreak_puts_unknown_time_last():
    from engine.scoring import _time_key

    assert sorted([None, 30, 10], key=_time_key) == [10, 30, None]
