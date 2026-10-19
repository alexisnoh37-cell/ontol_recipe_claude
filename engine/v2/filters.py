"""v2 필터 (docs/plan.md 부록 G-2, decisions D8).

v1 UserConstraints.check() 결과를 그대로 쓰되, 절대 불선호 재료 사유 중 certainty가 possible인 것만
제외 사유에서 뺀다(note로만 남긴다). 맛 정보가 없어 생긴 매운맛 한도 사유는 레시피가 '맵지 않음'으로
추정되면(engine/v2/spicy.py, D9) 뺀다(추정 매운맛 0은 어떤 한도도 넘지 않는다). 알레르기(possible 포함)·미매칭(알레르기 사용자)·불선호 음식 종류·
매운맛 한도·조리기구·시간은 v1과 같다. 대체재 안전성(is_unsafe_ingredient)은 v1 그대로(possible 불선호도 피함).
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.filters import UserConstraints
from engine.model import Exclusion, ExclusionReason, Recipe


@dataclass(frozen=True)
class V2Check:
    exclusions: tuple[Exclusion, ...]  # 비어 있으면 통과
    relaxed: tuple[Exclusion, ...]  # v2에서 제외하지 않기로 한 불선호 possible 사유(note용)


def is_relaxed(e: Exclusion) -> bool:
    return e.reason == ExclusionReason.HARD_DISLIKE_INGREDIENT and e.certainty == "possible"


def check_v2(constraints: UserConstraints, recipe: Recipe, *, not_spicy: bool = False) -> V2Check:
    found = constraints.check(recipe)
    if not_spicy and recipe.taste is None:
        found = [e for e in found if e.reason != ExclusionReason.SPICY_LIMIT]
    return V2Check(tuple(e for e in found if not is_relaxed(e)), tuple(e for e in found if is_relaxed(e)))
