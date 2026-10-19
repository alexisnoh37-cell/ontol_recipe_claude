"""간단 프로필(6가지 입력) → 엔진 UserContext 변환 (docs/plan.md 부록 G-11).

다른 앱이 저장하는 사용자 정보를 그대로 받는 형태다.
  못 먹는 것   allergens(알레르기 그룹 id: '들어 있을 수도 있는' 재료까지 제외)
               never_eat(재료 id: '확실히 들어간' 재료만 제외, D8)
  좋아하는 것  likes(재료 id) → 점수 가산(P)
  싫어하는 것  dislikes(재료 id) → 점수 감산(P). 제외하지 않는다
  매운맛 정도  spicy_level 0~4 → 한도(넘으면 제외)이자 선호 강도(T·Jev 취향 질문).
               5는 '한도 없음'으로만 본다(제외도 취향도 없음, D10 보완). None은 모름(맵기 무관)
  음식 종류    cuisine_likes / cuisine_dislikes → 점수(K). 제외하지 않는다
  요리 실력    skill_level 1~3 → 난이도 점수(D). None이면 2(보통)

같은 재료가 likes와 dislikes에 모두 있으면 ValueError(입력 오류). 못 먹는 것과 좋아하는 것이 겹치면
제외가 이긴다(안전 쪽, 따로 오류를 내지 않는다). 조리기구는 6가지 입력에 없으므로 호출자가 넘긴다.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from engine.model import Preference, TastePreference, UserContext

DEFAULT_SKILL = 2
NO_LIMIT_SPICY = 5


@dataclass(frozen=True)
class SimpleProfile:
    allergens: frozenset[str] = frozenset()
    never_eat: frozenset[str] = frozenset()
    likes: frozenset[str] = frozenset()
    dislikes: frozenset[str] = frozenset()
    spicy_level: int | None = None
    cuisine_likes: frozenset[str] = frozenset()
    cuisine_dislikes: frozenset[str] = frozenset()
    skill_level: int | None = None

    def validate(self) -> None:
        both = sorted(self.likes & self.dislikes)
        if both:
            raise ValueError(f"좋아하는 재료와 싫어하는 재료에 같은 재료가 있습니다: {both}")
        both = sorted(self.cuisine_likes & self.cuisine_dislikes)
        if both:
            raise ValueError(f"좋아하는 음식 종류와 싫어하는 음식 종류가 겹칩니다: {both}")
        if self.spicy_level is not None and not 0 <= self.spicy_level <= 5:
            raise ValueError(f"매운맛 정도는 0~5입니다: {self.spicy_level}")
        if self.skill_level is not None and self.skill_level not in (1, 2, 3):
            raise ValueError(f"요리 실력은 1~3입니다: {self.skill_level}")

    def to_user_context(self, *, pantry: Iterable[str] = (), equipment: Iterable[str] = ()) -> UserContext:
        self.validate()
        prefs: list[Preference] = [Preference("ingredient", i, -1, 1.0, is_hard=True) for i in sorted(self.never_eat)]
        prefs += [Preference("ingredient", i, 1, 1.0) for i in sorted(self.likes)]
        prefs += [Preference("ingredient", i, -1, 1.0) for i in sorted(self.dislikes)]
        prefs += [Preference("cuisine", c, 1, 1.0) for c in sorted(self.cuisine_likes)]
        prefs += [Preference("cuisine", c, -1, 1.0) for c in sorted(self.cuisine_dislikes)]
        tastes: tuple[TastePreference, ...] = ()
        if self.spicy_level is not None and self.spicy_level < NO_LIMIT_SPICY:
            tastes = (TastePreference("spicy", preferred_level=self.spicy_level, max_level=self.spicy_level),)
        return UserContext(
            skill_level=self.skill_level if self.skill_level is not None else DEFAULT_SKILL,
            allergen_groups=frozenset(self.allergens),
            preferences=tuple(prefs),
            tastes=tastes,
            pantry=frozenset(pantry),
            equipment=frozenset(equipment),
        )
