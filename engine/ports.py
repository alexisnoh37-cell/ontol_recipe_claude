"""엔진이 데이터를 받는 인터페이스 (docs/plan.md 부록 A)."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from engine.model import KnowledgeSnapshot, Recipe


class KnowledgeRepository(Protocol):
    def snapshot(self) -> KnowledgeSnapshot: ...


class RecipeRepository(Protocol):
    def by_ingredients(self, ids: Iterable[str]) -> Iterable[Recipe]:
        """주어진 재료 중 하나라도 main 또는 sub로 쓰는 레시피."""
        ...

    def get(self, recipe_id: str) -> Recipe | None: ...
