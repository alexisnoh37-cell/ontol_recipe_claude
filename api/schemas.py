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
    profile_id: int | None = None
    persona_id: str | None = None  # 골든셋 페르소나(시각화용, 부록 D-3). profile_id와 정확히 하나
    pantry: list[str] | None = None  # 주면 프로필의 보유 재료 대신 사용
    max_time_min: Annotated[int, Field(gt=0)] | None = None  # 페르소나는 비우면 페르소나의 희망 시간
    time_is_hard: bool = False
    limit: Annotated[int, Field(ge=1, le=50)] = 10
    trace: bool = False  # true면 단계별 추천 과정(trace)을 함께 돌려준다

    @model_validator(mode="after")
    def _one_subject(self) -> RecommendIn:
        if (self.profile_id is None) == (self.persona_id is None):
            raise ValueError("profile_id와 persona_id 중 정확히 하나를 주세요")
        return self


IngredientText = Annotated[str, Field(max_length=300)]


class AnalyzeRecipeIn(Strict):
    """외부 레시피 일회성 분석(docs/plan.md 부록 E). 재료는 text 또는 ingredients 중 정확히 하나, 사용자는 최대 하나."""

    title: Annotated[str, Field(min_length=1, max_length=100)]
    text: Annotated[str, Field(max_length=5000)] | None = None  # 재료 원문(줄·쉼표 구분)
    ingredients: Annotated[list[IngredientText], Field(max_length=100)] | None = None  # 재료 한 줄씩
    profile_id: int | None = None
    persona_id: str | None = None
    allergen_groups: Annotated[list[str], Field(max_length=50)] | None = None  # 저장 없이 알레르기만 줄 때

    @model_validator(mode="after")
    def _shape(self) -> AnalyzeRecipeIn:
        if not self.title.strip():
            raise ValueError("title이 비어 있습니다")
        if (self.text is None) == (self.ingredients is None):
            raise ValueError("text와 ingredients 중 정확히 하나를 주세요")
        subjects = [x for x in (self.profile_id, self.persona_id, self.allergen_groups) if x is not None]
        if len(subjects) > 1:
            raise ValueError("profile_id, persona_id, allergen_groups 중 최대 하나만 주세요")
        return self

    def source_text(self) -> str:
        return self.text if self.text is not None else "\n".join(self.ingredients or [])
