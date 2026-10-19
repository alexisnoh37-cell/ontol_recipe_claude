"""추천 v2 과정 기록 (docs/plan.md 부록 H-2). 3D 화면이 단계별로 재생할 중간 결과를 담는다.

RecommenderV2.trace()만 만든다. recommend()와 같은 코드 경로(_execute)에서 이미 계산된 값을 모을 뿐이고
판정·점수·정렬을 다시 하지 않는다. 기록 위치는 engine/v2/recommend.py의 `if self.t is not None` 줄이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.v2.ports import JudgeCandidate, JudgeProfile
from engine.v2.similarity import DishQuery


@dataclass
class JudgeCall:
    """Jev 판단 요청 한 번(보낸 것과 받은 것). key는 요청 안에서만 쓰는 c0, c1, …"""

    profile: JudgeProfile
    candidates: tuple[JudgeCandidate, ...]
    recipe_of: dict[str, str]  # key → 레시피 id
    aspects: tuple[str, ...]
    weights: dict[str, float]
    answers: dict[str, dict[str, tuple[float, float]]] = field(default_factory=dict)  # key → 항목 → (점수, 확신도)
    failed: bool = False


@dataclass
class V2Trace:
    mode: str
    pantry: frozenset[str] = frozenset()  # 정리된 보유 재료
    owned: frozenset[str] = frozenset()  # 보유로 보는 재료(기본 양념·is_a 상위 포함)
    from_pantry: frozenset[str] = frozenset()  # 기본 양념을 뺀 보유(is_a 상위 포함)
    checked: list[tuple[str, bool]] = field(default_factory=list)  # passes()에 걸린 순서: (레시피 id, 통과)
    seed: int | None = None
    # pantry: 묶음 → 레시피 id(필터 통과, 묶음 규칙), 가진 재료로 채운 줄 수, 꼭 필요한 재료 부족 수
    groups: dict[str, list[str]] = field(default_factory=dict)
    uses_pantry: dict[str, int] = field(default_factory=dict)
    missing: dict[str, int] = field(default_factory=dict)
    # dish: 질의 해석과 유사도 S(S > 0인 레시피 전부, 항목별 값)
    query: DishQuery | None = None
    active: tuple[str, ...] = ()
    similarity: dict[str, tuple[float, dict[str, float]]] = field(default_factory=dict)
    best_excluded: float = 0.0
    screened: dict[str, float] = field(default_factory=dict)  # Jev 걸러내기로 보충한 레시피 → 점수
    pool: list[str] = field(default_factory=list)  # 순위 단계에 들어간 후보(순서대로)
    judge: JudgeCall | None = None
    ranking: str = "rules"
    ranked: list[tuple[str, float, dict[str, float]]] = field(default_factory=list)  # 순위 단계 출력(limit 전)
    jev_failed: bool = False  # Jev 경로가 실패해 규칙 경로로 다시 계산했는가
    failed_judge: JudgeCall | None = None  # 실패한 Jev 요청(보낸 것)


__all__ = ["JudgeCall", "V2Trace"]
