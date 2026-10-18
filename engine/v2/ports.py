"""v2 인터페이스 (docs/plan.md 부록 G-3·G-4). 엔진은 Protocol만 알고, Jev 구현은 integrations/jev/에 있다."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Literal, Protocol

from engine.model import Recipe


class CatalogRepository(Protocol):
    """v1 RecipeRepository + 전체 목록(random·dish). engine.memory.InMemoryRecipeRepository가 이미 만족한다."""

    def by_ingredients(self, ids: Iterable[str]) -> Iterable[Recipe]: ...

    def get(self, recipe_id: str) -> Recipe | None: ...

    def all(self) -> Iterable[Recipe]: ...


@dataclass(frozen=True)
class RerankCandidate:
    """Jev에 보내는 후보 요약. 레시피 id·알레르기 정보는 담지 않는다(D7)."""

    key: str  # 요청 안에서만 쓰는 키(c0, c1, ...)
    title: str
    cuisine: str
    taste: Mapping[str, int] | None  # 모르면 None
    main_ingredients: tuple[str, ...]  # 재료 이름


@dataclass(frozen=True)
class RerankQuery:
    """Jev에 보내는 사용자 정보는 요리 실력·맛 선호·질의 문장뿐이다. 알레르기·건강 정보·사용자 id·보유 재료는 없다(D7)."""

    kind: Literal["pantry", "dish"]
    candidates: tuple[RerankCandidate, ...]
    query: str | None = None  # dish
    skill_level: int | None = None
    taste_preferences: Mapping[str, Mapping[str, int]] = field(default_factory=dict)  # 차원 → {preferred, max}


@dataclass(frozen=True)
class RerankAnswer:
    score: float  # 0~1
    confidence: float  # 0~1


class RerankError(Exception):
    """재정렬 실패(네트워크·시간 초과·응답 형식). 엔진은 규칙 순위로 돌아간다."""


class Reranker(Protocol):
    model: str

    def rerank(self, query: RerankQuery, *, timeout_s: float) -> Mapping[str, RerankAnswer]:
        """후보 key → 답. 모르는 key는 엔진이 버리고, 빠진 key는 규칙 점수 그대로 둔다. 실패하면 RerankError."""
        ...
