"""제약 필터 (docs/plan.md 4-3).

먹을 수 없는 레시피를 제외하고 사유를 Exclusion으로 남긴다. 판정은 컴파일된 allergen_closure와
ingredient_contains를 조회만 한다(요청 처리 중 그래프 탐색 금지).

  - 알레르기: 레시피의 모든 재료(선택·고명·기본 양념 포함)가 closure에 걸리면 제외. possible도 제외.
  - 미매칭 재료: 알레르기가 있는 사용자에게만 제외. 지식에 없는 id도 미매칭으로 본다.
  - 절대 불선호 재료: 재료 자신이거나 contains(is_a 상위, derived_from 원천)에 있으면 제외.
  - 절대 불선호 음식 종류, 매운맛 한도, 필수 조리기구, 시간(time_is_hard일 때만).
"""

from __future__ import annotations

from engine.model import (
    AllergenHit,
    ContainsHit,
    Exclusion,
    ExclusionReason,
    KnowledgeSnapshot,
    Recipe,
    RecommendRequest,
    UserContext,
)


class UserConstraints:
    """요청 한 번 동안의 사용자 제약. 레시피 필터와 대체재 안전성 판정이 같은 기준을 쓴다."""

    def __init__(self, snapshot: KnowledgeSnapshot, user: UserContext, req: RecommendRequest):
        self._snapshot = snapshot
        hard = [p for p in user.preferences if p.is_hard]
        # 알레르기는 UserContext.allergen_groups와 is_hard allergen_group 선호를 합친다(어느 쪽으로 와도 제외).
        groups = set(user.allergen_groups) | {p.target_id for p in hard if p.target_type == "allergen_group"}
        unknown = sorted(g for g in groups if g not in snapshot.allergen_closure)
        if unknown:
            # 모르는 그룹을 무시하면 알레르기 필터가 조용히 꺼진다. 요청을 거부한다.
            raise ValueError(f"알 수 없는 알레르기 그룹: {unknown}")
        self.allergen_groups: tuple[str, ...] = tuple(sorted(groups))

        self.hard_ingredients: tuple[str, ...] = tuple(
            sorted({p.target_id for p in hard if p.target_type == "ingredient"})
        )
        unknown = [i for i in self.hard_ingredients if i not in snapshot.ingredient_names]
        if unknown:
            raise ValueError(f"알 수 없는 절대 불선호 재료: {unknown}")
        self.hard_cuisines: frozenset[str] = frozenset(p.target_id for p in hard if p.target_type == "cuisine")

        spicy_limits = [t.max_level for t in user.tastes if t.dimension == "spicy" and t.max_level is not None]
        self.spicy_max: int | None = min(spicy_limits) if spicy_limits else None
        self.equipment: frozenset[str] = user.equipment
        self.max_time_min: int | None = req.max_time_min if req.time_is_hard else None

    @property
    def has_allergy(self) -> bool:
        return bool(self.allergen_groups)

    def allergen_hits(self, ingredient_id: str) -> list[tuple[str, AllergenHit]]:
        closure = self._snapshot.allergen_closure
        return [(g, closure[g][ingredient_id]) for g in self.allergen_groups if ingredient_id in closure[g]]

    def dislike_hits(self, ingredient_id: str) -> list[tuple[str, ContainsHit]]:
        contains = self._snapshot.contains.get(ingredient_id, {})
        hits = []
        for target in self.hard_ingredients:
            if target == ingredient_id:
                hits.append((target, ContainsHit("definite", (ingredient_id,))))
            elif target in contains:
                hits.append((target, contains[target]))
        return hits

    def is_unsafe_ingredient(self, ingredient_id: str) -> bool:
        """알레르기 closure나 절대 불선호에 걸리는 재료. 대체 안내·대체재 매칭에서 쓰지 않는다(A2)."""
        if ingredient_id not in self._snapshot.ingredient_names:
            return True
        return bool(self.allergen_hits(ingredient_id) or self.dislike_hits(ingredient_id))

    def check(self, recipe: Recipe) -> list[Exclusion]:
        """제외 사유 목록. 비어 있으면 통과. 사유가 여러 개면 모두 남긴다."""
        out: list[Exclusion] = []
        known = self._snapshot.ingredient_names
        seen: set[tuple[ExclusionReason, str | None, str | None]] = set()

        def add(e: Exclusion) -> None:
            key = (e.reason, e.ingredient_id, e.target)
            if e.reason == ExclusionReason.UNMAPPED_INGREDIENT or key not in seen:
                seen.add(key)
                out.append(e)

        for line in recipe.ingredients:
            ingredient_id = line.ingredient_id
            if ingredient_id is None or ingredient_id not in known:
                if self.has_allergy:
                    add(Exclusion(recipe.id, ExclusionReason.UNMAPPED_INGREDIENT, ingredient_id,
                                  detail=f"미매칭 재료: {line.raw_text or ingredient_id}"))
                continue
            for group, hit in self.allergen_hits(ingredient_id):
                add(Exclusion(recipe.id, ExclusionReason.ALLERGEN, ingredient_id, group, hit.certainty, hit.via,
                              detail=_line_detail(line.role, line.optional)))
            for target, hit in self.dislike_hits(ingredient_id):
                add(Exclusion(recipe.id, ExclusionReason.HARD_DISLIKE_INGREDIENT, ingredient_id, target,
                              hit.certainty, hit.via, detail=_line_detail(line.role, line.optional)))

        if recipe.cuisine in self.hard_cuisines:
            add(Exclusion(recipe.id, ExclusionReason.HARD_DISLIKE_CUISINE, target=recipe.cuisine))
        if self.spicy_max is not None and recipe.taste.spicy > self.spicy_max:
            add(Exclusion(recipe.id, ExclusionReason.SPICY_LIMIT, target="spicy",
                          detail=f"매운맛 {recipe.taste.spicy} > 한도 {self.spicy_max}"))
        for equipment in sorted(recipe.required_equipment - self.equipment):
            add(Exclusion(recipe.id, ExclusionReason.EQUIPMENT, target=equipment, detail=f"필수 조리기구 없음: {equipment}"))
        if self.max_time_min is not None and recipe.cook_time_min > self.max_time_min:
            add(Exclusion(recipe.id, ExclusionReason.TIME,
                          detail=f"조리시간 {recipe.cook_time_min}분 > 제한 {self.max_time_min}분"))
        return out


def _line_detail(role: str, optional: bool) -> str:
    return f"role={role}" + (", 선택 재료" if optional else "")
