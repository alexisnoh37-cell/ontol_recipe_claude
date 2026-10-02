"""지식 컴파일 결과 (docs/plan.md 부록 C-3, C-4).

`compile`은 순수 함수다. 같은 입력이면 항상 같은(정렬된) 결과를 낸다.
DB 반영은 storage/knowledge_writer.py가 한다.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from kb import graph
from kb.load import KnowledgeSources, load_sources
from kb.text import normalize_term
from kb.validate import Issue, Knowledge, validate


@dataclass(frozen=True)
class IngredientRow:
    id: str
    name: str
    kind: str
    category: str | None
    is_pantry_staple: bool
    is_processed: bool
    status: str
    confidence: str
    note: str | None


@dataclass(frozen=True)
class AliasRow:
    alias_norm: str
    alias: str
    ingredient_id: str
    form: str | None
    is_primary: bool


@dataclass(frozen=True)
class RelationRow:
    from_id: str
    to_id: str
    type: str  # is_a | derived_from | substitute
    certainty: str | None  # derived_from에만
    context: tuple[str, ...]
    ratio: float | None
    status: str
    confidence: str
    note: str | None


@dataclass(frozen=True)
class AllergenGroupRow:
    id: str
    display_name: str
    kind: str  # base | bundle
    status: str
    confidence: str
    note: str | None


@dataclass(frozen=True)
class GroupMemberRow:
    bundle_id: str
    member_id: str


@dataclass(frozen=True)
class IngredientAllergenRow:
    ingredient_id: str
    allergen_group_id: str
    certainty: str


@dataclass(frozen=True)
class AncestorRow:
    ingredient_id: str
    ancestor_id: str
    depth: int


@dataclass(frozen=True)
class ContainsRow:
    ingredient_id: str
    contained_id: str
    certainty: str
    via: tuple[str, ...]


@dataclass(frozen=True)
class ClosureRow:
    allergen_group_id: str
    ingredient_id: str
    certainty: str
    via: tuple[str, ...]  # 재료 → 알레르기를 직접 가진 원천 재료까지의 경로


@dataclass(frozen=True)
class CompiledKnowledge:
    source_hash: str
    ingredients: tuple[IngredientRow, ...]
    aliases: tuple[AliasRow, ...]
    relations: tuple[RelationRow, ...]
    allergen_groups: tuple[AllergenGroupRow, ...]
    group_members: tuple[GroupMemberRow, ...]
    ingredient_allergens: tuple[IngredientAllergenRow, ...]
    ancestors: tuple[AncestorRow, ...]
    contains: tuple[ContainsRow, ...]
    allergen_closure: tuple[ClosureRow, ...]
    vocab: dict[str, tuple[str, ...]]
    pantry_staples: tuple[str, ...]
    warnings: tuple[Issue, ...]

    # --- 조회 도우미(테스트·검증용) ------------------------------------
    @property
    def ingredient_ids(self) -> frozenset[str]:
        return frozenset(i.id for i in self.ingredients)

    @property
    def concept_ids(self) -> frozenset[str]:
        return frozenset(i.id for i in self.ingredients if i.kind == "concept")

    def closure_of(self, group_id: str) -> dict[str, ClosureRow]:
        return {r.ingredient_id: r for r in self.allergen_closure if r.allergen_group_id == group_id}

    def contains_of(self, ingredient_id: str) -> dict[str, ContainsRow]:
        return {r.contained_id: r for r in self.contains if r.ingredient_id == ingredient_id}

    def low_confidence_count(self) -> int:
        return (
            sum(i.confidence == "low" for i in self.ingredients)
            + sum(r.confidence == "low" for r in self.relations)
            + sum(g.confidence == "low" for g in self.allergen_groups)
        )

    def stats(self) -> dict[str, Any]:
        return {
            "ingredients": len(self.ingredients),
            "concepts": len(self.concept_ids),
            "aliases": len(self.aliases),
            "relations": {
                t: sum(r.type == t for r in self.relations) for t in ("is_a", "derived_from", "substitute")
            },
            "allergen_groups": len(self.allergen_groups),
            "group_members": len(self.group_members),
            "ingredient_allergens": len(self.ingredient_allergens),
            "ancestors": len(self.ancestors),
            "contains": len(self.contains),
            "allergen_closure": len(self.allergen_closure),
            "pantry_staples": len(self.pantry_staples),
            "low_confidence": self.low_confidence_count(),
            "draft": sum(i.status == "draft" for i in self.ingredients),
            "warnings": len(self.warnings),
        }

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["warnings"] = [asdict(w) for w in self.warnings]
        data["stats"] = self.stats()
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)


def source_hash(sources: KnowledgeSources) -> str:
    payload = {
        "allergens": sources.allergens,
        "vocab": sources.vocab,
        "ingredients": [list(x) for x in sources.ingredients],
        "substitutes": sources.substitutes,
        "pantry_staples": sources.pantry_staples,
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def compile(sources: KnowledgeSources) -> CompiledKnowledge:  # noqa: A001 - plan의 이름(kb.compile)을 따른다
    """검증 → 그래프 확장 → 정렬된 산출물. 검증 실패 시 KnowledgeError."""
    kn, warnings = validate(sources)
    return _build(kn, warnings, source_hash(sources))


def compile_paths(knowledge_dir: Path, pantry_staples_path: Path) -> CompiledKnowledge:
    return compile(load_sources(knowledge_dir, pantry_staples_path))


def _build(kn: Knowledge, warnings: list[Issue], src_hash: str) -> CompiledKnowledge:
    staples = set(kn.pantry_staples)
    ingredients = tuple(
        IngredientRow(
            id=i.id,
            name=i.name,
            kind=i.kind,
            category=i.category,
            is_pantry_staple=i.id in staples,
            is_processed=i.is_processed,
            status=i.status,
            confidence=i.confidence,
            note=i.note,
        )
        for i in kn.ingredients
    )

    aliases: list[AliasRow] = []
    for i in kn.ingredients:
        aliases.append(AliasRow(normalize_term(i.name), i.name, i.id, None, True))
        for a in i.aliases:
            aliases.append(AliasRow(normalize_term(a.text), a.text, i.id, a.form, False))

    relations: list[RelationRow] = []
    for i in kn.ingredients:
        for p in i.is_a:
            relations.append(RelationRow(i.id, p, "is_a", None, (), None, i.status, i.confidence, None))
        for d in i.derived_from:
            relations.append(RelationRow(i.id, d.id, "derived_from", d.certainty, (), None, i.status, i.confidence, None))
    for s in kn.substitutes:
        relations.append(
            RelationRow(s.from_id, s.to_id, "substitute", None, tuple(s.context), s.ratio, s.status, s.confidence, s.note)
        )

    groups = [AllergenGroupRow(g.id, g.display_name, "base", g.status, g.confidence, g.note) for g in kn.groups]
    groups += [AllergenGroupRow(b.id, b.display_name, "bundle", b.status, b.confidence, b.note) for b in kn.bundles]
    members = [GroupMemberRow(b.id, m) for b in kn.bundles for m in b.includes]
    direct = [IngredientAllergenRow(i.id, a.group, a.certainty) for i in kn.ingredients for a in i.allergens]

    # --- 그래프 확장 ------------------------------------------------------
    ids = [i.id for i in kn.ingredients]
    parents = {i.id: list(i.is_a) for i in kn.ingredients}
    sources = {i.id: [(d.id, d.certainty) for d in i.derived_from] for i in kn.ingredients}

    ancestor_rows = [
        AncestorRow(x, a, depth) for x, anc in graph.ancestors(parents).items() for a, depth in anc.items()
    ]
    reach = graph.expand_contains(ids, parents, sources)
    contains_rows = [
        ContainsRow(x, y, r.certainty, r.via) for x, targets in reach.items() for y, r in targets.items()
    ]

    has_group: dict[str, list[tuple[str, str]]] = {}  # 재료 → [(그룹, certainty)]
    for row in direct:
        has_group.setdefault(row.ingredient_id, []).append((row.allergen_group_id, row.certainty))

    base_closure: dict[str, dict[str, graph.Reach]] = {g.id: {} for g in kn.groups}
    for x in ids:
        candidates = [(x, graph.Reach(graph.DEFINITE, (x,)))] + sorted(reach[x].items())
        for y, path in candidates:
            for group, cert in has_group.get(y, ()):
                r = graph.Reach(graph.weaker(path.certainty, cert), path.via)
                cur = base_closure[group].get(x)
                if cur is None or graph.better(r, cur):
                    base_closure[group][x] = r

    closure: dict[str, dict[str, graph.Reach]] = dict(base_closure)
    for b in kn.bundles:
        merged: dict[str, graph.Reach] = {}
        for m in sorted(b.includes):
            for x, r in base_closure[m].items():
                if x not in merged or graph.better(r, merged[x]):
                    merged[x] = r
        closure[b.id] = merged

    closure_rows = [
        ClosureRow(g, x, r.certainty, r.via) for g, items in closure.items() for x, r in items.items()
    ]

    warns = list(warnings)
    for g in kn.groups:
        if not base_closure[g.id]:
            warns.append(Issue("empty_allergen_group", "allergens.yaml", f"알레르기 그룹 '{g.id}'에 해당하는 재료가 없습니다"))

    return CompiledKnowledge(
        source_hash=src_hash,
        ingredients=ingredients,
        aliases=tuple(sorted(aliases, key=lambda a: a.alias_norm)),
        relations=tuple(sorted(relations, key=lambda r: (r.from_id, r.to_id, r.type))),
        allergen_groups=tuple(sorted(groups, key=lambda g: g.id)),
        group_members=tuple(sorted(members, key=lambda m: (m.bundle_id, m.member_id))),
        ingredient_allergens=tuple(sorted(direct, key=lambda d: (d.ingredient_id, d.allergen_group_id))),
        ancestors=tuple(sorted(ancestor_rows, key=lambda a: (a.ingredient_id, a.ancestor_id))),
        contains=tuple(sorted(contains_rows, key=lambda c: (c.ingredient_id, c.contained_id))),
        allergen_closure=tuple(sorted(closure_rows, key=lambda c: (c.allergen_group_id, c.ingredient_id))),
        vocab={
            "cuisines": tuple(kn.vocab.cuisines),
            "equipment": tuple(kn.vocab.equipment),
            "techniques": tuple(kn.vocab.techniques),
            "categories": tuple(kn.vocab.categories),
        },
        pantry_staples=kn.pantry_staples,
        warnings=tuple(warns),
    )
