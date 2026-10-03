"""지식·레시피 → 엔진 입력 변환과 엔진 조립 (docs/plan.md 부록 A "데이터 주입").

API, 골든셋, 벤치, 테스트가 모두 이 모듈의 같은 함수를 쓴다(1-5에서 tests/support에서 옮김).

    CompiledKnowledge ──snapshot_from_compiled──▶ KnowledgeSnapshot
    RecipeSpec        ──recipe_from_spec────────▶ Recipe

공급원은 두 가지다. 어느 쪽이든 위 두 함수를 거친다.
  - 파일: knowledge/*.yaml을 kb로 컴파일 + data/recipes/*.yaml 시드(load_files)
  - DB: 컴파일 결과 테이블과 레시피 테이블을 읽어 CompiledKnowledge·RecipeSpec으로 되돌림(load_db)
DB 공급원에서도 그래프 탐색은 하지 않는다. 컴파일 시점에 계산된 행만 읽는다.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import yaml

from engine.config import load_engine_config
from engine.memory import InMemoryKnowledgeRepository, InMemoryRecipeRepository
from engine.model import AllergenHit, ContainsHit, KnowledgeSnapshot, Recipe, RecipeIngredient, Substitute, Taste
from engine.recommend import Recommender
from kb import CompiledKnowledge, compile_paths
from kb.compiled import (
    AliasRow,
    AllergenGroupRow,
    AncestorRow,
    ClosureRow,
    ContainsRow,
    GroupMemberRow,
    IngredientAllergenRow,
    IngredientRow,
    RelationRow,
)
from kb.datacheck import RecipeSpec
from kb.recipes import load_recipe_specs

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
KNOWLEDGE_DIR = ROOT / "knowledge"
RECIPES_DIR = ROOT / "data" / "recipes"


def snapshot_from_compiled(ck: CompiledKnowledge) -> KnowledgeSnapshot:
    ancestors: dict[str, dict[str, int]] = {}
    for a in ck.ancestors:
        ancestors.setdefault(a.ingredient_id, {})[a.ancestor_id] = a.depth
    contains: dict[str, dict[str, ContainsHit]] = {}
    for c in ck.contains:
        contains.setdefault(c.ingredient_id, {})[c.contained_id] = ContainsHit(c.certainty, c.via)
    closure: dict[str, dict[str, AllergenHit]] = {g.id: {} for g in ck.allergen_groups}
    for r in ck.allergen_closure:
        closure[r.allergen_group_id][r.ingredient_id] = AllergenHit(r.certainty, r.via)
    substitutes: dict[str, list[Substitute]] = {}
    for r in ck.relations:
        if r.type == "substitute":
            substitutes.setdefault(r.from_id, []).append(Substitute(r.from_id, r.to_id, frozenset(r.context), r.ratio))
    return KnowledgeSnapshot(
        ingredient_names={i.id: i.name for i in ck.ingredients},
        alias_index={a.alias_norm: a.ingredient_id for a in ck.aliases},
        ancestors=ancestors,
        contains=contains,
        allergen_closure=closure,
        substitutes={k: tuple(v) for k, v in substitutes.items()},
        pantry_staples=frozenset(ck.pantry_staples),
        concept_ids=ck.concept_ids,
    )


def recipe_from_spec(spec: RecipeSpec) -> Recipe:
    """레시피 시드(RecipeSpec) → 엔진 Recipe."""
    return Recipe(
        id=spec.id,
        title=spec.title,
        cuisine=spec.cuisine,
        difficulty=spec.difficulty or 1,
        cook_time_min=spec.cook_time_min,
        ingredients=tuple(
            RecipeIngredient(n, line.ingredient, line.role, line.optional, line.raw_text)
            for n, line in enumerate(spec.ingredients, start=1)
        ),
        taste=Taste(**spec.taste.model_dump()) if spec.taste else Taste(),
        required_equipment=frozenset(e.name for e in spec.equipment if e.required),
        techniques=frozenset(s.technique for s in spec.steps if s.technique),
        status=spec.status,
    )


def build_recommender(
    ck: CompiledKnowledge, recipes: Iterable[Recipe], *, config_dir: Path = CONFIG_DIR,
    serve_draft_recipes: bool | None = None,
) -> Recommender:
    """config/(weights.yaml, engine.yaml)를 읽는다. serve_draft_recipes를 주면 engine.yaml 값을 덮어쓴다."""
    return Recommender(
        InMemoryKnowledgeRepository(snapshot_from_compiled(ck)),
        InMemoryRecipeRepository(recipes),
        load_engine_config(config_dir, serve_draft_recipes=serve_draft_recipes),
    )


@dataclass(frozen=True)
class EngineData:
    """엔진 조립에 필요한 원본 묶음. API는 화면용 정보(별칭, 알레르기 그룹, confidence)도 여기서 읽는다."""

    knowledge: CompiledKnowledge
    recipes: tuple[RecipeSpec, ...]
    source: str  # "files" | "db"

    def recommender(self, *, config_dir: Path = CONFIG_DIR, serve_draft_recipes: bool | None = None) -> Recommender:
        return build_recommender(self.knowledge, [recipe_from_spec(s) for s in self.recipes],
                                 config_dir=config_dir, serve_draft_recipes=serve_draft_recipes)


def load_files(root: Path = ROOT) -> EngineData:
    """knowledge/ 컴파일 + data/recipes/ 시드. 시드 오류가 있으면 RecipeSeedError."""
    ck = compile_paths(root / "knowledge", root / "config" / "pantry_staples.yaml")
    specs = load_recipe_specs(ck, root / "data" / "recipes", root)
    return EngineData(ck, tuple(specs), "files")


# --- DB 공급원 --------------------------------------------------------------------------------------


def _vocab(knowledge_dir: Path) -> dict[str, tuple[str, ...]]:
    """고정 어휘는 DB에 없다(화면 선택지 용도). knowledge/vocab.yaml을 그대로 읽는다."""
    data = yaml.safe_load((knowledge_dir / "vocab.yaml").read_text(encoding="utf-8")) or {}
    return {k: tuple(data.get(k) or ()) for k in ("cuisines", "equipment", "techniques", "categories")}


def compiled_from_db(conn, knowledge_dir: Path = KNOWLEDGE_DIR) -> CompiledKnowledge:
    """DB의 컴파일 결과 테이블 → CompiledKnowledge. YAML 컴파일 결과와 같아야 한다(tests/storage가 검사)."""
    from sqlalchemy import select

    from storage import tables as t

    def rows(table, order):
        return conn.execute(select(table).order_by(*order)).mappings().all()

    ing = rows(t.ingredient, [t.ingredient.c.id])
    rel = rows(t.ingredient_relation, [t.ingredient_relation.c.from_id, t.ingredient_relation.c.to_id,
                                       t.ingredient_relation.c.type])
    build = conn.execute(select(t.knowledge_build.c.source_hash).order_by(t.knowledge_build.c.id.desc()).limit(1)).scalar()
    return CompiledKnowledge(
        source_hash=build or "",
        ingredients=tuple(IngredientRow(**dict(r)) for r in ing),
        aliases=tuple(AliasRow(**dict(r)) for r in rows(t.ingredient_alias, [t.ingredient_alias.c.alias_norm])),
        relations=tuple(
            RelationRow(r["from_id"], r["to_id"], r["type"], r["certainty"], tuple(r["context"] or ()),
                        float(r["ratio"]) if r["ratio"] is not None else None, r["status"], r["confidence"], r["note"])
            for r in rel
        ),
        allergen_groups=tuple(AllergenGroupRow(**dict(r)) for r in rows(t.allergen_group, [t.allergen_group.c.id])),
        group_members=tuple(GroupMemberRow(**dict(r)) for r in rows(
            t.allergen_group_member, [t.allergen_group_member.c.bundle_id, t.allergen_group_member.c.member_id])),
        ingredient_allergens=tuple(IngredientAllergenRow(**dict(r)) for r in rows(
            t.ingredient_allergen, [t.ingredient_allergen.c.ingredient_id, t.ingredient_allergen.c.allergen_group_id])),
        ancestors=tuple(AncestorRow(**dict(r)) for r in rows(
            t.ingredient_ancestor, [t.ingredient_ancestor.c.ingredient_id, t.ingredient_ancestor.c.ancestor_id])),
        contains=tuple(
            ContainsRow(r["ingredient_id"], r["contained_id"], r["certainty"], tuple(r["via"]))
            for r in rows(t.ingredient_contains, [t.ingredient_contains.c.ingredient_id,
                                                  t.ingredient_contains.c.contained_id])
        ),
        allergen_closure=tuple(
            ClosureRow(r["allergen_group_id"], r["ingredient_id"], r["certainty"], tuple(r["via"]))
            for r in rows(t.allergen_closure, [t.allergen_closure.c.allergen_group_id,
                                               t.allergen_closure.c.ingredient_id])
        ),
        vocab=_vocab(knowledge_dir),
        pantry_staples=tuple(r["id"] for r in ing if r["is_pantry_staple"]),
        warnings=(),
    )


def recipe_specs_from_db(conn) -> list[RecipeSpec]:
    """DB 레시피 테이블 → RecipeSpec(시드와 같은 형식). 엔진 변환은 recipe_from_spec이 한다."""
    from sqlalchemy import select

    from storage import tables as t

    def grouped(table, order):
        out: dict[str, list[dict]] = {}
        for r in conn.execute(select(table).order_by(*order)).mappings():
            out.setdefault(r["recipe_id"], []).append(dict(r))
        return out

    lines = grouped(t.recipe_ingredient, [t.recipe_ingredient.c.recipe_id, t.recipe_ingredient.c.line_no])
    tastes = {k: v[0] for k, v in grouped(t.recipe_taste, [t.recipe_taste.c.recipe_id]).items()}
    equipment = grouped(t.recipe_equipment, [t.recipe_equipment.c.recipe_id, t.recipe_equipment.c.equipment])
    steps = grouped(t.recipe_step, [t.recipe_step.c.recipe_id, t.recipe_step.c.step_no])
    specs = []
    for r in conn.execute(select(t.recipe).order_by(t.recipe.c.id)).mappings():
        taste = tastes.get(r["id"])
        specs.append(RecipeSpec.model_validate({
            "id": r["id"], "title": r["title"], "cuisine": r["cuisine"], "difficulty": r["difficulty"],
            "cook_time_min": r["cook_time_min"], "servings": r["servings"], "source": r["source"],
            "status": r["status"], "confidence": r["confidence"], "note": r["note"],
            "ingredients": [
                {"ingredient": x["ingredient_id"], "raw_text": x["raw_text"], "role": x["role"],
                 "optional": x["optional"], "amount": float(x["amount"]) if x["amount"] is not None else None,
                 "unit": x["unit"]}
                for x in lines.get(r["id"], [])
            ],
            "taste": {k: v for k, v in taste.items() if k != "recipe_id"} if taste else None,
            "equipment": [{"name": e["equipment"], "required": e["required"]} for e in equipment.get(r["id"], [])],
            "steps": [{"text": s["text"], "technique": s["technique"]} for s in steps.get(r["id"], [])],
        }))
    return sorted(specs, key=lambda r: r.id)  # load_recipe_specs와 같은 순서(DB 정렬 규칙은 collation에 따라 다름)


def load_db(conn, knowledge_dir: Path = KNOWLEDGE_DIR) -> EngineData:
    return EngineData(compiled_from_db(conn, knowledge_dir), tuple(recipe_specs_from_db(conn)), "db")
