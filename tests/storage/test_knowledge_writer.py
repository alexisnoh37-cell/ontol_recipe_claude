"""컴파일 결과 DB 반영 (docs/plan.md 부록 C-5): 개수 일치, 멱등, 참조 중 삭제 차단."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import func, insert, select, text

from kb import compile, compile_paths
from storage import tables as t
from storage.knowledge_writer import KnowledgeInUseError, write_compiled
from tests.support.kb_builders import ing, korean_basics, sources

ROOT = Path(__file__).resolve().parents[2]

KNOWLEDGE_TABLES = [
    "ingredient", "ingredient_alias", "ingredient_relation", "allergen_group", "allergen_group_member",
    "ingredient_allergen", "ingredient_ancestor", "ingredient_contains", "allergen_closure",
]


def snapshot(conn) -> dict[str, list[tuple]]:
    return {name: sorted(map(tuple, conn.execute(text(f"SELECT * FROM {name}")).all()), key=repr)
            for name in KNOWLEDGE_TABLES}


def count(conn, table) -> int:
    return conn.execute(select(func.count()).select_from(table)).scalar_one()


def test_real_knowledge_counts_match(db_engine):
    ck = compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")
    with db_engine.begin() as conn:
        build_id = write_compiled(conn, ck)
    with db_engine.connect() as conn:
        assert build_id >= 1
        assert count(conn, t.ingredient) == len(ck.ingredients)
        assert count(conn, t.ingredient_alias) == len(ck.aliases)
        assert count(conn, t.ingredient_relation) == len(ck.relations)
        assert count(conn, t.allergen_closure) == len(ck.allergen_closure)
        assert count(conn, t.ingredient_contains) == len(ck.contains)
        row = conn.execute(
            select(t.allergen_closure.c.certainty, t.allergen_closure.c.via)
            .where(t.allergen_closure.c.allergen_group_id == "shrimp", t.allergen_closure.c.ingredient_id == "kimchi")
        ).one()
        assert row.certainty == "possible" and row.via == ["kimchi", "saeujeot", "shrimp_raw"]


def test_write_is_idempotent(db_engine):
    ck = compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")
    with db_engine.begin() as conn:
        write_compiled(conn, ck)
    with db_engine.connect() as conn:
        first = snapshot(conn)
    with db_engine.begin() as conn:
        write_compiled(conn, ck)
    with db_engine.connect() as conn:
        assert snapshot(conn) == first
        assert count(conn, t.knowledge_build) == 2


def test_removed_unreferenced_ingredient_is_deleted(db_engine):
    with db_engine.begin() as conn:
        write_compiled(conn, compile(sources(korean_basics() + [ing("extra")])))
    with db_engine.begin() as conn:
        write_compiled(conn, compile(sources(korean_basics())))
    with db_engine.connect() as conn:
        assert conn.execute(select(t.ingredient.c.id).where(t.ingredient.c.id == "extra")).first() is None


def test_removed_ingredient_in_use_fails_and_rolls_back(db_engine):
    with db_engine.begin() as conn:
        write_compiled(conn, compile(sources(korean_basics() + [ing("extra")])))
        user_id = conn.execute(
            insert(t.user_profile).values(display_name="테스트", skill_level=1, household_size=1)
            .returning(t.user_profile.c.id)
        ).scalar_one()
        conn.execute(insert(t.user_pantry).values(user_id=user_id, ingredient_id="extra"))
    with db_engine.connect() as conn:
        before = snapshot(conn)
        builds = count(conn, t.knowledge_build)

    with pytest.raises(KnowledgeInUseError) as exc:
        with db_engine.begin() as conn:
            write_compiled(conn, compile(sources(korean_basics())))
    assert "user_pantry" in str(exc.value) and "extra" in str(exc.value)

    with db_engine.connect() as conn:
        assert snapshot(conn) == before
        assert count(conn, t.knowledge_build) == builds


def test_removed_allergen_group_used_by_preference_fails(db_engine):
    with db_engine.begin() as conn:
        write_compiled(conn, compile(sources(korean_basics())))
        user_id = conn.execute(
            insert(t.user_profile).values(display_name="새우 알레르기", skill_level=1, household_size=1)
            .returning(t.user_profile.c.id)
        ).scalar_one()
        conn.execute(insert(t.user_preference).values(
            user_id=user_id, target_type="allergen_group", target_id="crab", polarity=-1, strength=1, is_hard=True))
    groups = [{"id": g, "display_name": g, "status": "draft"} for g in ("shrimp", "squid", "soybean", "wheat", "egg", "milk")]
    with pytest.raises(KnowledgeInUseError):
        with db_engine.begin() as conn:
            write_compiled(conn, compile(sources(korean_basics(), groups=groups, bundles=[])))
