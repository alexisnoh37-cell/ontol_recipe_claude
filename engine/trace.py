"""추천 과정 기록 (docs/plan.md 부록 D-4). 시각화가 단계별로 재생할 중간 결과를 담는다.

Recommender.trace()만 만든다. recommend()와 같은 코드 경로(Recommender._run)에서 이미 계산된 값을 모을 뿐이고
판정·점수·정렬을 다시 하지 않는다. 추가 계산은 보유 재료의 is_a 조상 사전 조회(owned_from)뿐이다.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from engine.candidates import Candidate
from engine.scoring import Scored


@dataclass(frozen=True)
class RecommendTrace:
    pantry: frozenset[str]  # 정리된 보유 재료(concept·모르는 id 제거 후)
    pantry_staples: frozenset[str]
    owned_from: Mapping[str, tuple[str, ...]]  # is_a 조상 → 그 조상을 보유로 만든 재료(보유 재료·기본 양념)
    allergen_groups: tuple[str, ...]  # 필터가 실제로 쓴 알레르기 그룹(UserContext + is_hard 선호)
    hard_ingredients: tuple[str, ...]
    spicy_max: int | None
    max_time_min: int | None  # 시간 필터(time_is_hard일 때만 값)
    candidates: tuple[Candidate, ...]
    ranked: tuple[Scored, ...]  # 필터 통과 후보, 점수 순(다양성 보정 전)
    ordered: tuple[Scored, ...]  # 다양성 보정 후 최종 순서(limit 밖 포함)
