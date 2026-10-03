"""API 요청·응답 형식. 모양 검증(타입·범위)은 여기서(422), 지식 참조 검증은 main.py에서(400)."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Level = Annotated[int, Field(ge=0, le=5)]
Skill = Annotated[int, Field(ge=1, le=3)]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PreferenceIn(Strict):
    target_type: Literal["ingredient", "cuisine", "allergen_group"]
    target_id: str
    polarity: Literal[-1, 1] = -1
    strength: Annotated[float, Field(ge=0, le=1)] = 1.0
    is_hard: bool = False

    @model_validator(mode="after")
    def _rules(self) -> PreferenceIn:
        if self.target_type == "allergen_group":  # 알레르기는 항상 절대 제외(부록 B CHECK)
            self.polarity, self.is_hard = -1, True
        if self.is_hard and self.polarity != -1:
            raise ValueError("절대(is_hard) 선호는 불선호(polarity -1)만 가능합니다")
        return self


class TasteIn(Strict):
    dimension: Literal["spicy", "salty", "sweet", "sour", "umami", "savory"]
    preferred_level: Level | None = None
    max_level: Level | None = None

    @model_validator(mode="after")
    def _order(self) -> TasteIn:
        if self.preferred_level is not None and self.max_level is not None and self.preferred_level > self.max_level:
            raise ValueError("preferred_level은 max_level보다 클 수 없습니다")
        return self


class ProfileCreate(Strict):
    display_name: Annotated[str, Field(min_length=1, max_length=50)]
    skill_level: Skill = 1
    household_size: Annotated[int, Field(gt=0)] = 1


class ProfileUpdate(Strict):
    """보내지 않은 필드는 그대로 둔다. 목록 필드는 보내면 통째로 바꾼다."""

    display_name: Annotated[str, Field(min_length=1, max_length=50)] | None = None
    skill_level: Skill | None = None
    household_size: Annotated[int, Field(gt=0)] | None = None
    tastes: list[TasteIn] | None = None
    pantry: list[str] | None = None
    equipment: list[str] | None = None


class PreferencesIn(Strict):
    """선호 저장: 음식 종류·재료 선호와 알레르기를 통째로 바꾼다."""

    preferences: list[PreferenceIn]


class NamedId(BaseModel):
    id: str
    name: str


class ProfileOut(BaseModel):
    id: int
    display_name: str
    skill_level: int
    household_size: int
    preferences: list[dict[str, Any]]
    allergen_groups: list[NamedId]
    tastes: list[dict[str, Any]]
    pantry: list[NamedId]
    equipment: list[str]


class RecommendIn(Strict):
    profile_id: int
    pantry: list[str] | None = None  # 주면 프로필의 보유 재료 대신 사용
    max_time_min: Annotated[int, Field(gt=0)] | None = None
    time_is_hard: bool = False
    limit: Annotated[int, Field(ge=1, le=50)] = 10
