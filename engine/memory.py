"""in-memory 리포지토리. 구현체는 이것 하나이고 공급원(컴파일 결과, YAML, DB, 합성 데이터)만 다르다."""

from __future__ import annotations

from collections.abc import Iterable

from engine.candidates import CANDIDATE_ROLES
from engine.model import KnowledgeSnapshot, Recipe


class InMemoryKnowledgeRepository:
    def __init__(self, snapshot: KnowledgeSnapshot):
        self._snapshot = snapshot

    def snapshot(self) -> KnowledgeSnapshot:
        return self._snapshot


class InMemoryRecipeRepository:
    def __init__(self, recipes: Iterable[Recipe]):
        self._by_id: dict[str, Recipe] = {}
        self._index: dict[str, list[str]] = {}  # 재료 id → main·sub로 쓰는 레시피 id
        for recipe in recipes:
            if recipe.id in self._by_id:
                raise ValueError(f"레시피 id 중복: {recipe.id}")
            self._by_id[recipe.id] = recipe
            for line in recipe.ingredients:
                if line.ingredient_id is not None and line.role in CANDIDATE_ROLES:
                    ids = self._index.setdefault(line.ingredient_id, [])
                    if recipe.id not in ids:
                        ids.append(recipe.id)

    def by_ingredients(self, ids: Iterable[str]) -> list[Recipe]:
        seen: set[str] = set()
        out: list[Recipe] = []
        for ingredient_id in sorted(set(ids)):
            for recipe_id in self._index.get(ingredient_id, ()):
                if recipe_id not in seen:
                    seen.add(recipe_id)
                    out.append(self._by_id[recipe_id])
        return out

    def get(self, recipe_id: str) -> Recipe | None:
        return self._by_id.get(recipe_id)

    def all(self) -> list[Recipe]:
        return list(self._by_id.values())
