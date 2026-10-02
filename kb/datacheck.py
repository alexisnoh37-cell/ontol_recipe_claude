"""컴파일된 지식을 기준으로 레시피·사용자 데이터를 검증한다 (docs/plan.md 5-4).

레시피 시드 형식(RecipeSpec)은 0-2 시점의 잠정안이다. DDL(부록 B)의 recipe 계열 컬럼을
그대로 따르며, Phase 1-3에서 레시피 시드를 만들 때 확정한다.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator

from kb.compiled import CompiledKnowledge
from kb.schema import Confidence, Id, StrictModel, Text
from kb.validate import Issue, _parse

Level = Annotated[int, Field(ge=0, le=5)]


class RecipeIngredientSpec(StrictModel):
    ingredient: Id | None = None  # None = 미매칭
    raw_text: Text
    role: Literal["main", "sub", "seasoning", "garnish"]
    optional: bool = False
    amount: float | None = None
    unit: str | None = None


class TasteSpec(StrictModel):
    spicy: Level
    salty: Level
    sweet: Level
    sour: Level
    umami: Level
    savory: Level


class EquipmentSpec(StrictModel):
    name: Text
    required: bool = True


class StepSpec(StrictModel):
    text: Text
    technique: Text | None = None


class RecipeSpec(StrictModel):
    id: Id
    title: Text
    cuisine: Text
    difficulty: Annotated[int, Field(ge=1, le=3)] | None = None
    cook_time_min: Annotated[int, Field(gt=0)]
    servings: Annotated[int, Field(gt=0)] | None = None
    source: Text
    status: Literal["draft", "published"] = "draft"
    confidence: Confidence = "high"
    note: str | None = None
    ingredients: Annotated[list[RecipeIngredientSpec], Field(min_length=1)]
    taste: TasteSpec | None = None
    equipment: list[EquipmentSpec] = []
    steps: list[StepSpec] = []

    @field_validator("equipment", mode="before")
    @classmethod
    def _expand_equipment(cls, value: object) -> object:
        if isinstance(value, list):
            return [{"name": e} if isinstance(e, str) else e for e in value]
        return value


def _ingredient_issue(ck: CompiledKnowledge, ing_id: str | None, where: str, usage: str) -> Issue | None:
    if ing_id is None:
        return Issue("unmapped", where, f"{usage}이(가) 정규 재료 id에 매핑되지 않았습니다")
    if ing_id not in ck.ingredient_ids:
        return Issue("bad_ref", where, f"{usage} '{ing_id}'가 재료 목록에 없습니다")
    if ing_id in ck.concept_ids:
        return Issue("concept_usage", where, f"concept 노드 '{ing_id}'는 {usage}로 쓸 수 없습니다")
    return None


def check_recipes(ck: CompiledKnowledge, recipes: Iterable[tuple[str, Any]]) -> list[Issue]:
    """recipes: (출처, 레시피 dict) 목록."""
    issues: list[Issue] = []
    parsed: list[tuple[str, RecipeSpec]] = []
    for where, item in recipes:
        if (r := _parse(RecipeSpec, item, where, issues)):
            parsed.append((where, r))

    for rid, n in Counter(r.id for _, r in parsed).items():
        if n > 1:
            issues.append(Issue("duplicate_id", "recipes", f"레시피 id '{rid}'가 {n}번 있습니다"))

    cuisines = set(ck.vocab["cuisines"])
    equipment = set(ck.vocab["equipment"])
    techniques = set(ck.vocab["techniques"])
    for where, r in parsed:
        for n, line in enumerate(r.ingredients, start=1):
            issue = _ingredient_issue(ck, line.ingredient, f"{where} 재료 {n}({line.raw_text})", "레시피 재료")
            if issue:
                issues.append(issue)
        if r.cuisine not in cuisines:
            issues.append(Issue("bad_vocab", where, f"cuisine '{r.cuisine}'가 vocab.yaml에 없습니다"))
        for e in r.equipment:
            if e.name not in equipment:
                issues.append(Issue("bad_vocab", where, f"조리기구 '{e.name}'가 vocab.yaml에 없습니다"))
        for n, step in enumerate(r.steps, start=1):
            if step.technique is not None and step.technique not in techniques:
                issues.append(Issue("bad_vocab", f"{where} 단계 {n}", f"technique '{step.technique}'가 vocab.yaml에 없습니다"))
        if r.status == "published":
            if r.taste is None:
                issues.append(Issue("published_incomplete", where, "published 레시피에 맛 프로필(taste)이 없습니다"))
            if r.difficulty is None:
                issues.append(Issue("published_incomplete", where, "published 레시피에 난이도(difficulty)가 없습니다"))
    return issues


def check_pantry(ck: CompiledKnowledge, rows: Iterable[tuple[Any, str]]) -> list[Issue]:
    """rows: (user_id, ingredient_id). 보유 재료는 실제 재료여야 하고 concept이면 안 된다."""
    issues = []
    for user_id, ing_id in rows:
        if (issue := _ingredient_issue(ck, ing_id, f"user_pantry(user={user_id})", "보유 재료")):
            issues.append(issue)
    return issues


def check_preferences(ck: CompiledKnowledge, rows: Iterable[tuple[Any, str, str]]) -> list[Issue]:
    """rows: (user_id, target_type, target_id). target_id가 실제로 존재해야 한다."""
    groups = {g.id for g in ck.allergen_groups}
    cuisines = set(ck.vocab["cuisines"])
    issues = []
    for user_id, target_type, target_id in rows:
        where = f"user_preference(user={user_id}, {target_type})"
        if target_type == "ingredient":
            ok = target_id in ck.ingredient_ids  # 선호는 concept(예: 해산물)에도 둘 수 있다
        elif target_type == "allergen_group":
            ok = target_id in groups
        elif target_type == "cuisine":
            ok = target_id in cuisines
        else:
            issues.append(Issue("bad_ref", where, f"알 수 없는 target_type '{target_type}'"))
            continue
        if not ok:
            issues.append(Issue("bad_ref", where, f"대상 '{target_id}'가 존재하지 않습니다"))
    return issues
