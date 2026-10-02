"""knowledge/*.yaml 항목 스키마 (형식: knowledge/README.md).

모든 모델은 정의되지 않은 키를 거부한다(extra="forbid"). 단축형(문자열 별칭,
문자열 derived_from)은 여기서 정식 객체로 펼친다.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ID_PATTERN = r"^[a-z][a-z0-9_]*$"

Id = Annotated[str, Field(pattern=ID_PATTERN)]
Text = Annotated[str, Field(min_length=1)]
Status = Literal["draft", "reviewed"]
Confidence = Literal["high", "low"]
Certainty = Literal["definite", "possible"]
Kind = Literal["ingredient", "concept"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --- allergens.yaml -------------------------------------------------------


class AllergenGroupSpec(StrictModel):
    id: Id
    display_name: Text
    status: Status
    confidence: Confidence = "high"
    note: str | None = None


class AllergenBundleSpec(AllergenGroupSpec):
    includes: Annotated[list[Id], Field(min_length=1)]


# --- vocab.yaml -----------------------------------------------------------


class VocabSpec(StrictModel):
    cuisines: list[Text]
    equipment: list[Text]
    techniques: list[Text]
    categories: list[Text]


# --- ingredients.yaml -----------------------------------------------------


class AliasSpec(StrictModel):
    text: Text
    form: Text | None = None


class DerivedFromSpec(StrictModel):
    id: Id
    certainty: Certainty = "definite"


class AllergenRefSpec(StrictModel):
    group: Id
    certainty: Certainty


class IngredientSpec(StrictModel):
    id: Id
    name: Text
    kind: Kind = "ingredient"
    category: Text | None = None
    aliases: list[AliasSpec] = []
    is_a: list[Id] = []
    derived_from: list[DerivedFromSpec] = []
    is_processed: bool = False
    allergens: list[AllergenRefSpec] = []
    status: Status
    confidence: Confidence = "high"
    note: str | None = None

    @field_validator("aliases", mode="before")
    @classmethod
    def _expand_aliases(cls, value: object) -> object:
        if isinstance(value, list):
            return [{"text": a} if isinstance(a, str) else a for a in value]
        return value

    @field_validator("derived_from", mode="before")
    @classmethod
    def _expand_derived_from(cls, value: object) -> object:
        if isinstance(value, list):
            return [{"id": d, "certainty": "definite"} if isinstance(d, str) else d for d in value]
        return value


# --- substitutes.yaml -----------------------------------------------------


class SubstituteSpec(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    from_id: Id = Field(alias="from")
    to_id: Id = Field(alias="to")
    context: list[Text] = []
    ratio: Annotated[float, Field(gt=0, le=1)] | None = None
    status: Status
    confidence: Confidence = "high"
    note: str | None = None


# --- config/pantry_staples.yaml -------------------------------------------


class PantryStaplesSpec(StrictModel):
    staples: list[Id]
