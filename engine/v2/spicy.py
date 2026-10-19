"""맛 정보가 없는 레시피의 매운맛 추정 (decisions D9, docs/plan.md 부록 G-11 제안 1(가)).

맛 정보가 없는(taste None) 레시피 중 다음을 모두 만족하면 매운맛 0으로 본다. 하나라도 어기면 계속 '모름'.
  - 재료 줄이 하나 이상 있고, 모든 줄이 지식에 있는 정규 id에 매핑되어 있다(미매칭 줄은 무엇인지 모르므로).
    선택 재료·고명·기본 양념도 본다(알레르기 판정과 같은 범위).
  - 어떤 줄도 매운 재료 목록(config/v2.yaml spicy_inference.markers)에 없고, 그 재료의 is_a 상위나
    포함(가능) 재료(컴파일된 ingredient_contains)에 목록 재료가 없다.
  - 제목에 매운 말(spicy_inference.title_markers: 고추·매콤·얼큰 등)이 없다(원본 재료 목록에서 양념이 빠진 경우 대비).
추정은 매운맛 차원에만 쓴다. 다른 맛은 계속 모른다. 컴파일된 조회만 하고 요청 중 그래프 탐색은 하지 않는다.
"""

from __future__ import annotations

from collections.abc import Iterable

from engine.model import KnowledgeSnapshot, Recipe


def inferred_not_spicy(snapshot: KnowledgeSnapshot, recipe: Recipe, markers: frozenset[str],
                       title_markers: Iterable[str] = ()) -> bool:
    if recipe.taste is not None or not recipe.ingredients or not markers:
        return False
    if any(w in recipe.title for w in title_markers):
        return False
    for line in recipe.ingredients:
        iid = line.ingredient_id
        if iid is None or iid not in snapshot.ingredient_names:
            return False
        if iid in markers:
            return False
        if any(m in markers for m in snapshot.ancestors.get(iid, {})):
            return False
        if any(m in markers for m in snapshot.contains.get(iid, {})):
            return False
    return True


def not_spicy_ids(snapshot: KnowledgeSnapshot, recipes: Iterable[Recipe], markers: frozenset[str],
                  title_markers: Iterable[str] = ()) -> frozenset[str]:
    words = tuple(title_markers)
    return frozenset(r.id for r in recipes if inferred_not_spicy(snapshot, r, markers, words))
