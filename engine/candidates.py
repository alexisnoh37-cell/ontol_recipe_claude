"""후보 생성 (docs/plan.md 4-2).

보유 재료가 main 또는 sub로 쓰인 레시피를 후보로 잡는다. 레시피 재료 X가 "보유"인 경우:
  - X를 직접 보유하거나 기본 양념이다.
  - X의 is_a 하위 재료를 보유한다(삼겹살 보유 → "돼지고기" 충족). 반대 방향은 충족이 아니다(C1).
    컴파일된 ingredient_ancestor만 조회한다.
보유가 아니면 대체재를 찾는다. 대체재 Y는 사용자가 직접 보유하고, context가 비었거나 레시피 technique과
겹치고, 사용자의 알레르기·절대 불선호에 걸리지 않을 때만 쓴다(A2). 대체재로만 충족된 재료는
LineMatch.substitute로 표시해 설명 단계에 넘긴다.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from engine.model import KnowledgeSnapshot, Recipe, RecipeIngredient, Substitute
from engine.ports import RecipeRepository

CANDIDATE_ROLES = ("main", "sub")

LineStatus = Literal["owned", "substitute", "missing"]


@dataclass(frozen=True)
class LineMatch:
    line: RecipeIngredient
    status: LineStatus
    substitute: Substitute | None = None  # status가 substitute일 때 쓴 대체 관계


@dataclass(frozen=True)
class Candidate:
    recipe: Recipe
    lines: tuple[LineMatch, ...]  # recipe.ingredients와 같은 순서


def owned_ingredients(snapshot: KnowledgeSnapshot, pantry: frozenset[str]) -> frozenset[str]:
    """보유로 간주하는 재료: 보유 재료, 기본 양념, 그리고 그들의 is_a 조상."""
    base = pantry | snapshot.pantry_staples
    owned = set(base)
    for ingredient_id in base:
        owned.update(snapshot.ancestors.get(ingredient_id, {}))
    return frozenset(owned)


def substitute_for(
    snapshot: KnowledgeSnapshot,
    recipe: Recipe,
    need_id: str,
    pantry: frozenset[str],
    is_unsafe: Callable[[str], bool],
) -> Substitute | None:
    usable = [
        s for s in snapshot.substitutes.get(need_id, ())
        if s.to_id in pantry
        and (not s.context or s.context & recipe.techniques)
        and not is_unsafe(s.to_id)
    ]
    return min(usable, key=lambda s: s.to_id) if usable else None


def match_lines(
    snapshot: KnowledgeSnapshot,
    recipe: Recipe,
    pantry: frozenset[str],
    owned: frozenset[str],
    is_unsafe: Callable[[str], bool],
) -> tuple[LineMatch, ...]:
    out = []
    for line in recipe.ingredients:
        if line.ingredient_id is None:
            out.append(LineMatch(line, "missing"))
        elif line.ingredient_id in owned:
            out.append(LineMatch(line, "owned"))
        else:
            sub = substitute_for(snapshot, recipe, line.ingredient_id, pantry, is_unsafe)
            out.append(LineMatch(line, "substitute", sub) if sub else LineMatch(line, "missing"))
    return tuple(out)


def generate_candidates(
    snapshot: KnowledgeSnapshot,
    recipes: RecipeRepository,
    pantry: frozenset[str],
    is_unsafe: Callable[[str], bool],
    *,
    serve_draft_recipes: bool = False,
) -> list[Candidate]:
    """후보 레시피와 재료별 충족 상태. 필터는 이 다음 단계에서 적용한다."""
    owned = owned_ingredients(snapshot, pantry)
    lookup = set(owned) | _substitutable_needs(snapshot, pantry, is_unsafe)
    out: list[Candidate] = []
    for recipe in recipes.by_ingredients(lookup):
        if recipe.status != "published" and not serve_draft_recipes:
            continue
        lines = match_lines(snapshot, recipe, pantry, owned, is_unsafe)
        if any(m.status != "missing" and m.line.role in CANDIDATE_ROLES for m in lines):
            out.append(Candidate(recipe, lines))
    return out


def _substitutable_needs(
    snapshot: KnowledgeSnapshot, pantry: frozenset[str], is_unsafe: Callable[[str], bool]
) -> set[str]:
    """보유한 안전한 재료로 대체할 수 있는 레시피 재료(context는 레시피별로 match_lines에서 다시 본다)."""
    return {
        need_id
        for need_id, subs in snapshot.substitutes.items()
        if any(s.to_id in pantry and not is_unsafe(s.to_id) for s in subs)
    }

