"""v2 요청·결과 (docs/plan.md 부록 G-6). v1 RecommendItem·Exclusion을 그대로 담는다."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from engine.model import Exclusion, RecommendItem

Mode = Literal["random", "pantry", "dish"]
Group = Literal["ready", "near"]

# 응답 note 코드(표시 문구는 API 표시 계층이 붙인다)
NOTE_RERANK_UNAVAILABLE = "rerank_unavailable"  # Jev 실패·시간 초과 → 규칙 순위
NOTE_RERANK_OFF = "rerank_off"  # 요청·설정에서 껐거나 Jev가 주입되지 않음
NOTE_DISH_NO_MATCH = "dish_no_match"  # 질의와 비슷한 레시피를 찾지 못함
NOTE_DISH_EXCLUDED = "dish_excluded"  # 질의와 가장 비슷한 레시피가 못 먹는 재료 때문에 제외됨
NOTE_DISLIKE_POSSIBLE = "dislike_possible"  # 불선호 재료가 '포함 가능'이라 제외하지 않음(D8)
NOTE_SPICY_INFERRED = "spicy_inferred"  # 맛 정보는 없지만 매운 재료가 없어 맵지 않다고 봄(D9)


@dataclass(frozen=True)
class V2Request:
    mode: Mode
    query: str | None = None  # dish에서 필수
    pantry: frozenset[str] | None = None  # 주면 UserContext.pantry 대신
    seed: int | None = None  # random. 없으면 엔진이 정해 결과에 담는다
    rerank: bool | None = None  # None이면 config/v2.yaml rerank.enabled
    max_time_min: int | None = None
    time_is_hard: bool = False
    limit: int | None = None  # None이면 random은 random.default_limit, 나머지는 10


@dataclass(frozen=True)
class V2Item:
    item: RecommendItem  # v1 설명(점수·breakdown·부족 재료·대체 안내·notes). breakdown에 S·J·J_conf가 더해질 수 있다
    group: Group | None = None  # pantry만
    required_missing: int = 0  # 꼭 필요한 재료 중 부족한 줄 수(pantry 묶음 기준)
    notes: tuple[str, ...] = ()  # v2 note 코드(dislike_possible 등)


@dataclass(frozen=True)
class V2Result:
    mode: Mode
    items: tuple[V2Item, ...]
    exclusions: tuple[Exclusion, ...] = ()
    exclusion_summary: Mapping[str, int] = field(default_factory=dict)
    seed: int | None = None
    rerank_used: bool = False
    rerank_model: str | None = None
    notes: tuple[str, ...] = ()
