"""컴파일 결과를 DB에 반영한다 (docs/plan.md 부록 C-5).

호출자가 트랜잭션을 연다(`with engine.begin() as conn:`). 예외가 나면 전체가 롤백된다.
같은 입력이면 같은 DB 상태가 된다(knowledge_build 이력 행만 늘어남).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from sqlalchemy import Connection, delete, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from kb.compiled import CompiledKnowledge
from storage import tables as t


class KnowledgeInUseError(Exception):
    """YAML에서 사라진 재료·알레르기 그룹을 레시피나 사용자 데이터가 참조 중이다."""

    def __init__(self, references: list[str]):
        self.references = references
        super().__init__(
            "삭제할 지식 항목을 참조하는 데이터가 있어 반영을 중단했습니다:\n"
            + "\n".join(f"  {r}" for r in references)
        )


def _rows(items: Any) -> list[dict[str, Any]]:
    rows = []
    for item in items:
        row = asdict(item)
        for key in ("via", "context"):
            if key in row:
                row[key] = list(row[key])
        rows.append(row)
    return rows


def _upsert(conn: Connection, table, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    stmt = pg_insert(table).values(rows)
    keys = [c.name for c in table.primary_key.columns]
    stmt = stmt.on_conflict_do_update(
        index_elements=keys,
        set_={c.name: stmt.excluded[c.name] for c in table.columns if c.name not in keys},
    )
    conn.execute(stmt)


def _find_references(conn: Connection, removed_ingredients: set[str], removed_groups: set[str]) -> list[str]:
    refs: list[str] = []
    if removed_ingredients:
        ids = sorted(removed_ingredients)
        for recipe_id, line_no, ing in conn.execute(
            select(t.recipe_ingredient.c.recipe_id, t.recipe_ingredient.c.line_no, t.recipe_ingredient.c.ingredient_id)
            .where(t.recipe_ingredient.c.ingredient_id.in_(ids))
            .order_by(t.recipe_ingredient.c.recipe_id, t.recipe_ingredient.c.line_no)
        ):
            refs.append(f"recipe_ingredient: 레시피 {recipe_id} {line_no}행 → {ing}")
        for user_id, ing in conn.execute(
            select(t.user_pantry.c.user_id, t.user_pantry.c.ingredient_id)
            .where(t.user_pantry.c.ingredient_id.in_(ids))
            .order_by(t.user_pantry.c.user_id, t.user_pantry.c.ingredient_id)
        ):
            refs.append(f"user_pantry: 사용자 {user_id} → {ing}")
    # user_preference.target_id는 FK가 없다. 조용히 끊기면 알레르기·불선호가 무효가 되므로 함께 막는다.
    targets = [("ingredient", sorted(removed_ingredients)), ("allergen_group", sorted(removed_groups))]
    for target_type, ids in targets:
        if not ids:
            continue
        p = t.user_preference
        for user_id, target in conn.execute(
            select(p.c.user_id, p.c.target_id)
            .where(p.c.target_type == target_type, p.c.target_id.in_(ids))
            .order_by(p.c.user_id, p.c.target_id)
        ):
            refs.append(f"user_preference: 사용자 {user_id} → {target_type} {target}")
    return refs


def write_compiled(conn: Connection, ck: CompiledKnowledge) -> int:
    """컴파일 결과를 반영하고 knowledge_build id를 돌려준다."""
    build_id = conn.execute(
        insert(t.knowledge_build).values(source_hash=ck.source_hash, stats=ck.stats()).returning(t.knowledge_build.c.id)
    ).scalar_one()

    new_ingredients = {i.id for i in ck.ingredients}
    new_groups = {g.id for g in ck.allergen_groups}
    removed_ingredients = set(conn.scalars(select(t.ingredient.c.id))) - new_ingredients
    removed_groups = set(conn.scalars(select(t.allergen_group.c.id))) - new_groups
    refs = _find_references(conn, removed_ingredients, removed_groups)
    if refs:
        raise KnowledgeInUseError(refs)

    for table in t.DERIVED_KNOWLEDGE_TABLES:
        conn.execute(delete(table))

    _upsert(conn, t.allergen_group, _rows(ck.allergen_groups))
    _upsert(conn, t.ingredient, _rows(ck.ingredients))
    if removed_ingredients:
        conn.execute(delete(t.ingredient).where(t.ingredient.c.id.in_(sorted(removed_ingredients))))
    if removed_groups:
        conn.execute(delete(t.allergen_group).where(t.allergen_group.c.id.in_(sorted(removed_groups))))

    for table, items in (
        (t.ingredient_alias, ck.aliases),
        (t.ingredient_relation, ck.relations),
        (t.allergen_group_member, ck.group_members),
        (t.ingredient_allergen, ck.ingredient_allergens),
        (t.ingredient_ancestor, ck.ancestors),
        (t.ingredient_contains, ck.contains),
        (t.allergen_closure, ck.allergen_closure),
    ):
        rows = _rows(items)
        if rows:
            conn.execute(insert(table), rows)
    return build_id
