"""검증된 레시피 시드(RecipeSpec)를 DB에 반영한다 (scripts/load_recipes.py).

시드 파일이 원본이다. 시드에 있는 레시피는 하위 행(재료·맛·조리기구·단계)까지 지우고 다시 넣는다.
시드에 없는 DB 레시피는 기본적으로 그대로 두고, prune=True일 때만 지운다.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Connection, delete, func, insert, select

from kb.datacheck import RecipeSpec
from storage import tables as t

_CHILDREN = (t.recipe_step, t.recipe_equipment, t.recipe_taste, t.recipe_ingredient)


@dataclass(frozen=True)
class RecipeWriteResult:
    written: int
    pruned: tuple[str, ...]
    untouched: tuple[str, ...]  # 시드에 없어 그대로 둔 DB 레시피


def write_recipes(conn: Connection, specs: Sequence[RecipeSpec], *, prune: bool = False) -> RecipeWriteResult:
    ids = [r.id for r in specs]
    existing = set(conn.scalars(select(t.recipe.c.id)))
    extra = sorted(existing - set(ids))

    if ids:
        for table in _CHILDREN:
            conn.execute(delete(table).where(table.c.recipe_id.in_(ids)))
        conn.execute(delete(t.recipe).where(t.recipe.c.id.in_(ids)))
    if prune and extra:
        for table in _CHILDREN:
            conn.execute(delete(table).where(table.c.recipe_id.in_(extra)))
        conn.execute(delete(t.recipe).where(t.recipe.c.id.in_(extra)))

    recipes, lines, tastes, equipment, steps = [], [], [], [], []
    for r in specs:
        if r.difficulty is None:
            raise ValueError(f"{r.id}: DB 적재에는 difficulty가 필요합니다")
        recipes.append({
            "id": r.id, "title": r.title, "cuisine": r.cuisine, "difficulty": r.difficulty,
            "cook_time_min": r.cook_time_min, "servings": r.servings, "source": r.source, "status": r.status,
            "confidence": r.confidence, "note": r.note, "updated_at": func.now(),
        })
        for n, line in enumerate(r.ingredients, start=1):
            lines.append({
                "recipe_id": r.id, "line_no": n, "ingredient_id": line.ingredient, "role": line.role,
                "optional": line.optional, "amount": line.amount, "unit": line.unit, "raw_text": line.raw_text,
            })
        if r.taste is not None:
            tastes.append({"recipe_id": r.id, **r.taste.model_dump()})
        for e in r.equipment:
            equipment.append({"recipe_id": r.id, "equipment": e.name, "required": e.required})
        for n, step in enumerate(r.steps, start=1):
            steps.append({"recipe_id": r.id, "step_no": n, "text": step.text, "technique": step.technique})

    for row in recipes:  # updated_at에 SQL 함수를 쓰므로 행 단위로 넣는다
        conn.execute(insert(t.recipe).values(**row))
    for table, rows in ((t.recipe_ingredient, lines), (t.recipe_taste, tastes),
                        (t.recipe_equipment, equipment), (t.recipe_step, steps)):
        if rows:
            conn.execute(insert(table), rows)
    return RecipeWriteResult(len(specs), tuple(extra) if prune else (), () if prune else tuple(extra))
