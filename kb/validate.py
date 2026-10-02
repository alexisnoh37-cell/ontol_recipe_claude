"""지식 원본 검증 (docs/plan.md 부록 C-2). 오류를 모두 모아 한 번에 보고한다."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from kb import graph
from kb.load import KnowledgeSources
from kb.schema import (
    AllergenBundleSpec,
    AllergenGroupSpec,
    IngredientSpec,
    PantryStaplesSpec,
    SubstituteSpec,
    VocabSpec,
)
from kb.text import normalize_term

MAX_IS_A_LEVELS = 3  # docs/plan.md 5-1: 카테고리 계층은 3단계 이내


@dataclass(frozen=True)
class Issue:
    code: str
    where: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.where}: {self.message}"


class KnowledgeError(Exception):
    """검증 실패. errors는 전부, warnings는 참고용."""

    def __init__(self, errors: Sequence[Issue], warnings: Sequence[Issue] = ()):
        self.errors = tuple(errors)
        self.warnings = tuple(warnings)
        lines = "\n".join(f"  {e}" for e in self.errors)
        super().__init__(f"지식 검증 실패: 오류 {len(self.errors)}건\n{lines}")


@dataclass(frozen=True)
class Knowledge:
    """검증을 통과한 지식 원본(정식 객체)."""

    groups: tuple[AllergenGroupSpec, ...]
    bundles: tuple[AllergenBundleSpec, ...]
    vocab: VocabSpec
    ingredients: tuple[IngredientSpec, ...]
    substitutes: tuple[SubstituteSpec, ...]
    pantry_staples: tuple[str, ...]


M = TypeVar("M", bound=BaseModel)


def _parse(model: type[M], item: Any, where: str, errors: list[Issue]) -> M | None:
    if not isinstance(item, Mapping):
        errors.append(Issue("schema", where, "매핑(키: 값) 형식이어야 합니다"))
        return None
    try:
        return model.model_validate(dict(item))
    except ValidationError as exc:
        for e in exc.errors():
            loc = ".".join(str(p) for p in e["loc"]) or "(전체)"
            kind = e["type"]
            if kind == "extra_forbidden":
                errors.append(Issue("unknown_key", where, f"알 수 없는 키 '{loc}'"))
            elif kind == "missing":
                errors.append(Issue("missing_field", where, f"필수 필드 '{loc}'가 없습니다"))
            elif kind == "string_pattern_mismatch":
                errors.append(
                    Issue("bad_id", where, f"'{loc}' 값 {e['input']!r}이 id 형식(영문 소문자 snake_case)이 아닙니다")
                )
            else:
                errors.append(Issue("schema", where, f"'{loc}': {e['msg']} (입력: {e.get('input')!r})"))
        return None


def _where(source: str, index: int, item: Any) -> str:
    ident = item.get("id") if isinstance(item, Mapping) else None
    if ident is None and isinstance(item, Mapping) and "from" in item:
        ident = f"{item.get('from')}→{item.get('to')}"
    return f"{source}#{index + 1}" + (f" ({ident})" if ident else "")


def _as_list(data: Any, where: str, errors: list[Issue]) -> list[Any]:
    if data is None:
        return []
    if not isinstance(data, list):
        errors.append(Issue("schema", where, "항목 목록(list) 형식이어야 합니다"))
        return []
    return data


def _top_mapping(data: Any, where: str, allowed: set[str], errors: list[Issue]) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        errors.append(Issue("schema", where, "최상위는 매핑 형식이어야 합니다"))
        return {}
    for key in sorted(set(data) - allowed, key=str):
        errors.append(Issue("unknown_key", where, f"알 수 없는 최상위 키 '{key}'"))
    return data


def validate(sources: KnowledgeSources) -> tuple[Knowledge, list[Issue]]:
    """검증을 통과하면 (Knowledge, 경고 목록), 아니면 KnowledgeError."""
    errors: list[Issue] = []
    warnings: list[Issue] = []
    names = sources.names

    # --- 1. 스키마 ---------------------------------------------------------
    allergens = _top_mapping(sources.allergens, names["allergens"], {"groups", "bundles"}, errors)
    groups: list[AllergenGroupSpec] = []
    for i, item in enumerate(_as_list(allergens.get("groups"), f"{names['allergens']}:groups", errors)):
        if (g := _parse(AllergenGroupSpec, item, _where(f"{names['allergens']}:groups", i, item), errors)):
            groups.append(g)
    bundles: list[AllergenBundleSpec] = []
    for i, item in enumerate(_as_list(allergens.get("bundles"), f"{names['allergens']}:bundles", errors)):
        if (b := _parse(AllergenBundleSpec, item, _where(f"{names['allergens']}:bundles", i, item), errors)):
            bundles.append(b)

    vocab = _parse(VocabSpec, sources.vocab, names["vocab"], errors) or VocabSpec(
        cuisines=[], equipment=[], techniques=[], categories=[]
    )
    for field in ("cuisines", "equipment", "techniques", "categories"):
        for value, n in Counter(getattr(vocab, field)).items():
            if n > 1:
                errors.append(Issue("duplicate", names["vocab"], f"{field}에 '{value}'가 {n}번 있습니다"))

    ingredients: list[IngredientSpec] = []
    where_of: dict[str, str] = {}
    raw_ids: set[str] = set()
    raw_concepts: set[str] = set()
    for source, data in sources.ingredients:
        for i, item in enumerate(_as_list(data, source, errors)):
            where = _where(source, i, item)
            if isinstance(item, Mapping) and isinstance(item.get("id"), str):
                raw_ids.add(item["id"])
                if item.get("kind") == "concept":
                    raw_concepts.add(item["id"])
            if (ing := _parse(IngredientSpec, item, where, errors)):
                if ing.id in where_of:
                    errors.append(Issue("duplicate_id", where, f"재료 id '{ing.id}'가 {where_of[ing.id]}에도 있습니다"))
                    continue
                where_of[ing.id] = where
                ingredients.append(ing)

    substitutes: list[tuple[str, SubstituteSpec]] = []
    for i, item in enumerate(_as_list(sources.substitutes, names["substitutes"], errors)):
        where = _where(names["substitutes"], i, item)
        if (s := _parse(SubstituteSpec, item, where, errors)):
            substitutes.append((where, s))

    pantry = _parse(PantryStaplesSpec, sources.pantry_staples, names["pantry_staples"], errors)
    staples = list(pantry.staples) if pantry else []

    # --- 2. id 중복과 참조 ------------------------------------------------
    group_where: dict[str, str] = {}
    for g in [*groups, *bundles]:
        if g.id in group_where:
            errors.append(Issue("duplicate_id", names["allergens"], f"알레르기 그룹 id '{g.id}'가 중복됩니다"))
        group_where[g.id] = g.id
    for g in groups:
        if g.official != (g.source == "law_annex2"):
            errors.append(Issue("bad_source", names["allergens"], f"그룹 '{g.id}': official: true와 source: law_annex2는 함께 써야 합니다"))
    for b in bundles:
        if b.official or b.source != "custom":
            errors.append(Issue("bad_source", names["allergens"], f"묶음 '{b.id}'는 official: false, source: custom이어야 합니다"))
    base_ids = {g.id for g in groups}
    bundle_ids = {b.id for b in bundles}
    for b in bundles:
        for member, n in Counter(b.includes).items():
            if n > 1:
                errors.append(Issue("duplicate", names["allergens"], f"묶음 '{b.id}'에 '{member}'가 {n}번 있습니다"))
            if member in bundle_ids:
                errors.append(Issue("bad_ref", names["allergens"], f"묶음 '{b.id}'의 includes '{member}'는 묶음 그룹입니다(기본 그룹만 가능)"))
            elif member not in base_ids:
                errors.append(Issue("bad_ref", names["allergens"], f"묶음 '{b.id}'의 includes '{member}'가 없습니다"))

    categories = set(vocab.categories)
    for ing in ingredients:
        where = where_of[ing.id]
        for target, n in Counter(ing.is_a).items():
            if n > 1:
                errors.append(Issue("duplicate", where, f"is_a에 '{target}'가 {n}번 있습니다"))
            if target not in raw_ids:
                errors.append(Issue("bad_ref", where, f"is_a 대상 '{target}'가 없습니다"))
        for target, n in Counter(d.id for d in ing.derived_from).items():
            if n > 1:
                errors.append(Issue("duplicate", where, f"derived_from에 '{target}'가 {n}번 있습니다"))
            if target not in raw_ids:
                errors.append(Issue("bad_ref", where, f"derived_from 대상 '{target}'가 없습니다"))
        for group, n in Counter(a.group for a in ing.allergens).items():
            if n > 1:
                errors.append(Issue("duplicate", where, f"allergens에 '{group}'가 {n}번 있습니다"))
            if group in bundle_ids:
                errors.append(Issue("bad_ref", where, f"allergens에는 기본 그룹만 쓸 수 있습니다('{group}'는 묶음 그룹)"))
            elif group not in base_ids:
                errors.append(Issue("bad_ref", where, f"알레르기 그룹 '{group}'가 없습니다"))
        if ing.category is not None and ing.category not in categories:
            errors.append(Issue("bad_vocab", where, f"category '{ing.category}'가 vocab.yaml categories에 없습니다"))
        # 의미 규칙
        if ing.is_processed and not ing.derived_from:
            errors.append(Issue("processed_without_source", where, "is_processed: true인데 derived_from이 없습니다"))
        if ing.kind == "concept" and ing.allergens:
            errors.append(Issue("concept_allergen", where, "concept 노드에는 allergens를 적을 수 없습니다"))
        if ing.derived_from and not ing.is_processed:
            warnings.append(Issue("derived_not_processed", where, "derived_from이 있는데 is_processed가 지정되지 않았습니다"))

    staple_where = names["pantry_staples"]
    for sid, n in Counter(staples).items():
        if n > 1:
            errors.append(Issue("duplicate", staple_where, f"기본 양념 '{sid}'가 {n}번 있습니다"))
        if sid not in raw_ids:
            errors.append(Issue("bad_ref", staple_where, f"기본 양념 '{sid}'가 재료 목록에 없습니다"))
        elif sid in raw_concepts:
            errors.append(Issue("concept_usage", staple_where, f"concept 노드 '{sid}'는 기본 양념(보유 재료)으로 쓸 수 없습니다"))

    techniques = set(vocab.techniques)
    seen_pairs: set[tuple[str, str]] = set()
    for where, s in substitutes:
        for end in (s.from_id, s.to_id):
            if end not in raw_ids:
                errors.append(Issue("bad_ref", where, f"대체 관계의 재료 '{end}'가 없습니다"))
            elif end in raw_concepts:
                errors.append(Issue("concept_usage", where, f"concept 노드 '{end}'는 대체 관계에 쓸 수 없습니다"))
        if s.from_id == s.to_id:
            errors.append(Issue("bad_ref", where, "from과 to가 같습니다"))
        if (s.from_id, s.to_id) in seen_pairs:
            errors.append(Issue("duplicate", where, f"대체 관계 {s.from_id}→{s.to_id}가 중복됩니다"))
        seen_pairs.add((s.from_id, s.to_id))
        for c in s.context:
            if c not in techniques:
                errors.append(Issue("bad_vocab", where, f"context '{c}'가 vocab.yaml techniques에 없습니다"))

    # --- 3. 이름·별칭 전역 유일 -------------------------------------------
    owners: dict[str, list[str]] = {}
    for ing in ingredients:
        for text in [ing.name, *(a.text for a in ing.aliases)]:
            norm = normalize_term(text)
            if not norm:
                errors.append(Issue("bad_alias", where_of[ing.id], f"정규화 후 빈 이름·별칭 {text!r}"))
                continue
            owners.setdefault(norm, []).append(f"{ing.id}({text})")
    for norm, who in sorted(owners.items()):
        if len(who) > 1:
            errors.append(Issue("alias_conflict", "ingredients", f"이름·별칭 '{norm}'(정규화)가 겹칩니다: {', '.join(who)}"))

    # --- 4. 순환 ----------------------------------------------------------
    ids = [ing.id for ing in ingredients]
    is_a = {ing.id: list(ing.is_a) for ing in ingredients}
    derived = {ing.id: [d.id for d in ing.derived_from] for ing in ingredients}
    union = {i: sorted(set(is_a[i]) | set(derived[i])) for i in ids}
    cycle_found = False
    for label, edges in (("is_a", is_a), ("derived_from", derived)):
        if (cycle := graph.find_cycle(ids, edges)):
            cycle_found = True
            errors.append(Issue("cycle", label, "순환: " + " → ".join(cycle)))
    if not cycle_found and (cycle := graph.find_cycle(ids, union)):
        errors.append(Issue("cycle", "is_a ∪ derived_from", "순환: " + " → ".join(cycle)))

    # --- 5. 경고: is_a 깊이 -----------------------------------------------
    if not cycle_found:
        for ing_id, anc in graph.ancestors(is_a).items():
            levels = 1 + max(anc.values(), default=0)
            if levels > MAX_IS_A_LEVELS:
                warnings.append(Issue("deep_is_a", where_of[ing_id], f"is_a 계층이 {levels}단계입니다(권장 {MAX_IS_A_LEVELS}단계 이내)"))

    if errors:
        raise KnowledgeError(errors, warnings)

    knowledge = Knowledge(
        groups=tuple(sorted(groups, key=lambda g: g.id)),
        bundles=tuple(sorted(bundles, key=lambda b: b.id)),
        vocab=vocab,
        ingredients=tuple(sorted(ingredients, key=lambda i: i.id)),
        substitutes=tuple(sorted((s for _, s in substitutes), key=lambda s: (s.from_id, s.to_id))),
        pantry_staples=tuple(sorted(staples)),
    )
    return knowledge, warnings
