"""결과 확인 도우미."""

from __future__ import annotations

from engine.model import Exclusion, ExclusionReason, RecommendItem, RecommendResult


def recommended_ids(result: RecommendResult) -> set[str]:
    return {item.recipe_id for item in result.items}


def excluded_ids(result: RecommendResult) -> set[str]:
    return {e.recipe_id for e in result.exclusions}


def item(result: RecommendResult, recipe_id: str) -> RecommendItem:
    found = [i for i in result.items if i.recipe_id == recipe_id]
    assert found, f"{recipe_id}가 추천 결과에 없습니다"
    return found[0]


def exclusions(result: RecommendResult, recipe_id: str, reason: ExclusionReason | None = None) -> list[Exclusion]:
    return [e for e in result.exclusions if e.recipe_id == recipe_id and (reason is None or e.reason == reason)]


def assert_excluded(result: RecommendResult, recipe_id: str, reason: ExclusionReason, ingredient_id: str | None = None):
    """추천 결과에 없고, 지정한 사유(와 걸린 재료)로 제외 기록이 남아야 한다."""
    assert recipe_id not in recommended_ids(result), f"{recipe_id}가 추천되었습니다"
    found = exclusions(result, recipe_id, reason)
    assert found, f"{recipe_id}의 제외 사유 {reason}가 없습니다: {exclusions(result, recipe_id)}"
    if ingredient_id is not None:
        assert ingredient_id in {e.ingredient_id for e in found}, (
            f"{recipe_id}의 {reason} 제외가 {ingredient_id} 때문이 아닙니다: {found}"
        )
    return found


def assert_recommended(result: RecommendResult, recipe_id: str):
    assert recipe_id in recommended_ids(result), (
        f"{recipe_id}가 추천되지 않았습니다. 제외 기록: {exclusions(result, recipe_id)}"
    )
    assert not exclusions(result, recipe_id), f"{recipe_id}가 추천되었는데 제외 기록도 있습니다"
