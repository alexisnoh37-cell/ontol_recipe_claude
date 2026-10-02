"""레시피 시드 DB 반영 (scripts/load_recipes.py): 개수 일치, 멱등, prune."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import func, insert, select

from kb import compile_paths
from kb.recipes import load_recipe_specs
from storage import tables as t
from storage.knowledge_writer import write_compiled
from storage.recipe_writer import write_recipes

ROOT = Path(__file__).resolve().parents[2]


def count(conn, table) -> int:
    return conn.execute(select(func.count()).select_from(table)).scalar_one()


def test_seed_written_and_idempotent(db_engine):
    ck = compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")
    specs = load_recipe_specs(ck, ROOT / "data" / "recipes", ROOT)
    with db_engine.begin() as conn:
        write_compiled(conn, ck)
        write_recipes(conn, specs)
    for _ in range(2):
        with db_engine.connect() as conn:
            assert count(conn, t.recipe) == len(specs)
            assert count(conn, t.recipe_ingredient) == sum(len(s.ingredients) for s in specs)
            assert count(conn, t.recipe_taste) == len(specs)
            assert count(conn, t.recipe_step) == sum(len(s.steps) for s in specs)
            assert count(conn, t.recipe_equipment) == sum(len(s.equipment) for s in specs)
            assert set(conn.scalars(select(t.recipe.c.status))) == {s.status for s in specs}
        with db_engine.begin() as conn:
            write_recipes(conn, specs)  # 두 번째 반영도 같은 결과


def test_prune_removes_recipes_not_in_seed(db_engine):
    ck = compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")
    specs = load_recipe_specs(ck, ROOT / "data" / "recipes", ROOT)
    with db_engine.begin() as conn:
        write_compiled(conn, ck)
        conn.execute(insert(t.recipe).values(id="old_recipe", title="옛 레시피", cuisine="한식", difficulty=1,
                                             cook_time_min=10, source="test", status="draft", confidence="high"))
        kept = write_recipes(conn, specs[:3])
        assert kept.untouched and "old_recipe" in kept.untouched
        pruned = write_recipes(conn, specs[:3], prune=True)
        assert "old_recipe" in pruned.pruned
        assert set(conn.scalars(select(t.recipe.c.id))) == {s.id for s in specs[:3]}
