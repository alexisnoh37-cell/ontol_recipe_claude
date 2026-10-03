"""DB 공급원 = 파일 공급원 (docs/plan.md 부록 A "DB에서 읽은 스냅샷 = YAML 컴파일 스냅샷").

API는 DB에서, 골든셋·테스트는 파일에서 엔진을 만든다. 둘 다 storage.engine_source의 같은 변환 함수를 거치므로
DB에서 되돌린 CompiledKnowledge·RecipeSpec이 파일 것과 같으면 엔진 입력도 같다.
"""

from __future__ import annotations

from engine.model import RecommendRequest, UserContext
from storage.engine_source import load_db, load_files, recipe_from_spec, snapshot_from_compiled
from storage.knowledge_writer import write_compiled
from storage.recipe_writer import write_recipes


def test_db_source_equals_file_source(db_engine):
    files = load_files()
    with db_engine.begin() as conn:
        write_compiled(conn, files.knowledge)
        write_recipes(conn, files.recipes)
    with db_engine.connect() as conn:
        db = load_db(conn)

    assert snapshot_from_compiled(db.knowledge) == snapshot_from_compiled(files.knowledge)
    a, b = db.knowledge, files.knowledge
    for name in ("ingredients", "aliases", "relations", "allergen_groups", "group_members",
                 "ingredient_allergens", "ancestors", "contains", "allergen_closure"):
        assert sorted(getattr(a, name), key=repr) == sorted(getattr(b, name), key=repr), name
    assert set(a.pantry_staples) == set(b.pantry_staples)
    assert a.vocab == b.vocab
    assert a.source_hash == b.source_hash

    assert [recipe_from_spec(r) for r in db.recipes] == [recipe_from_spec(r) for r in files.recipes]
    assert [dump(r) for r in db.recipes] == [dump(r) for r in files.recipes]

    user = UserContext(skill_level=2, allergen_groups=frozenset({"shrimp"}),
                       pantry=frozenset({"pork", "kimchi", "rice", "egg", "potato"}))
    ra = db.recommender().recommend(user, RecommendRequest())
    rb = files.recommender().recommend(user, RecommendRequest())
    assert ra == rb



def dump(spec):
    """조리기구는 DB에 순서 열이 없어 이름순으로 비교한다(엔진은 집합으로 쓴다)."""
    d = spec.model_dump()
    d["equipment"] = sorted(d["equipment"], key=lambda e: e["name"])
    return d
