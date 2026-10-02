"""엔진 입출력 데이터 (docs/plan.md 부록 A). 모두 불변(frozen) dataclass다.

엔진은 이 타입만 주고받는다. 지식은 컴파일 결과를 담은 KnowledgeSnapshot으로,
레시피는 Recipe로, 사용자 데이터는 호출자가 UserContext로 넘긴다.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

Certainty = Literal["definite", "possible"]
Role = Literal["main", "sub", "seasoning", "garnish"]
TargetType = Literal["ingredient", "cuisine", "allergen_group"]
TasteDimension = Literal["spicy", "salty", "sweet", "sour", "umami", "savory"]


# --- 지식 스냅샷 (컴파일 산출물, 요청 처리 중에는 조회만) --------------------


@dataclass(frozen=True)
class AllergenHit:
    """allergen_closure 한 행: 이 재료는 이 그룹 알레르기를 (포함 가능하게) 가진다."""

    certainty: Certainty
    via: tuple[str, ...]  # 재료 → 알레르기를 직접 가진 원천 재료까지의 id 경로


@dataclass(frozen=True)
class ContainsHit:
    """ingredient_contains 한 행: 이 재료는 대상 재료를 포함(가능)한다."""

    certainty: Certainty
    via: tuple[str, ...]


@dataclass(frozen=True)
class Substitute:
    from_id: str
    to_id: str
    context: frozenset[str] = frozenset()  # 비어 있으면 모든 조리 맥락에서 성립
    ratio: float | None = None  # None이면 config의 기본 인정 비율


@dataclass(frozen=True)
class KnowledgeSnapshot:
    ingredient_names: Mapping[str, str]  # id → 대표 이름
    alias_index: Mapping[str, str]  # 정규화된 이름·별칭 → id
    ancestors: Mapping[str, Mapping[str, int]]  # id → {is_a 조상: depth}
    contains: Mapping[str, Mapping[str, ContainsHit]]  # id → {포함 재료: 근거}
    allergen_closure: Mapping[str, Mapping[str, AllergenHit]]  # 그룹(기본·묶음) → {재료: 근거}
    substitutes: Mapping[str, tuple[Substitute, ...]]  # 레시피가 요구하는 재료 → 대체 후보
    pantry_staples: frozenset[str]
    concept_ids: frozenset[str]


# --- 레시피 ------------------------------------------------------------------


@dataclass(frozen=True)
class RecipeIngredient:
    line_no: int
    ingredient_id: str | None  # None = 정규 id에 매핑되지 않은 재료
    role: Role
    optional: bool = False
    raw_text: str = ""


@dataclass(frozen=True)
class Taste:
    spicy: int = 0
    salty: int = 0
    sweet: int = 0
    sour: int = 0
    umami: int = 0
    savory: int = 0


@dataclass(frozen=True)
class Recipe:
    id: str
    title: str
    cuisine: str
    difficulty: int  # 1~3
    cook_time_min: int
    ingredients: tuple[RecipeIngredient, ...]
    taste: Taste = Taste()
    required_equipment: frozenset[str] = frozenset()
    techniques: frozenset[str] = frozenset()  # 조리 단계 technique 집합(대체재 context 판정용)
    status: Literal["draft", "published"] = "published"


# --- 사용자와 요청 -------------------------------------------------------------


@dataclass(frozen=True)
class Preference:
    """user_preference 한 행. is_hard면 감점이 아니라 제외(polarity는 -1만 가능)."""

    target_type: TargetType
    target_id: str
    polarity: Literal[-1, 1]
    strength: float = 1.0  # 0~1
    is_hard: bool = False


@dataclass(frozen=True)
class TastePreference:
    dimension: TasteDimension
    preferred_level: int | None = None  # 좋아하는 정도 0~5
    max_level: int | None = None  # 먹을 수 있는 한도 0~5. 넘으면 제외


@dataclass(frozen=True)
class UserContext:
    """엔진은 사용자 데이터를 조회하지 않는다. 호출자(API)가 이 객체로 넘긴다."""

    skill_level: int = 1  # 1~3
    allergen_groups: frozenset[str] = frozenset()  # 기본 그룹 또는 묶음 그룹 id
    preferences: tuple[Preference, ...] = ()
    tastes: tuple[TastePreference, ...] = ()
    pantry: frozenset[str] = frozenset()  # 보유 재료 id
    equipment: frozenset[str] = frozenset()  # 보유 조리기구


@dataclass(frozen=True)
class RecommendRequest:
    max_time_min: int | None = None
    time_is_hard: bool = False
    pantry: frozenset[str] | None = None  # 주어지면 UserContext.pantry 대신 사용
    limit: int = 10


# --- 결과 ----------------------------------------------------------------------


class ExclusionReason(StrEnum):
    """제외 사유 코드. 제외된 레시피는 이후 어떤 단계에서도 복귀하지 않는다."""

    ALLERGEN = "allergen"  # 알레르기 closure에 걸리는 재료(선택·고명 포함)
    UNMAPPED_INGREDIENT = "unmapped_ingredient"  # 알레르기 사용자 + 미매칭 재료
    HARD_DISLIKE_INGREDIENT = "hard_dislike_ingredient"  # 절대 불선호 재료(contains 포함)
    HARD_DISLIKE_CUISINE = "hard_dislike_cuisine"
    SPICY_LIMIT = "spicy_limit"
    EQUIPMENT = "equipment"
    TIME = "time"


@dataclass(frozen=True)
class Exclusion:
    """제외 기록. 한 레시피에 사유가 여러 개면 여러 행이 나올 수 있다."""

    recipe_id: str
    reason: ExclusionReason
    ingredient_id: str | None = None  # 제외를 일으킨 레시피 재료
    target: str | None = None  # 알레르기 그룹, 불선호 재료·음식 종류 등
    certainty: Certainty | None = None
    via: tuple[str, ...] = ()  # 근거 경로(예: kimchi → saeujeot → shrimp_raw)
    detail: str = ""


@dataclass(frozen=True)
class SubstitutionNote:
    need_id: str  # 레시피가 요구하는(사용자에게 없는) 재료
    use_id: str  # 대신 쓸 재료


@dataclass(frozen=True)
class RecommendItem:
    recipe_id: str
    title: str
    score: float
    breakdown: Mapping[str, float]  # I, K, T, P, D, M
    missing: tuple[str, ...] = ()
    substitutions: tuple[SubstitutionNote, ...] = ()
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecommendResult:
    items: tuple[RecommendItem, ...]
    exclusions: tuple[Exclusion, ...] = field(default=())
    # 사유 코드별 제외된 레시피 수(한 레시피가 사유 여러 개면 사유마다 1). 응답에는 이 요약만 담는다(4-3)
    exclusion_summary: Mapping[str, int] = field(default_factory=dict)
