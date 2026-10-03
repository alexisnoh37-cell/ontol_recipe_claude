"""SqlUserStore: 프로필 생성·수정·선호 저장이 메모리 저장소와 같은 결과를 낸다 (Phase 1-5)."""

from __future__ import annotations

import pytest

from storage.engine_source import load_files
from storage.knowledge_writer import write_compiled
from storage.users import (
    DuplicateProfileName,
    InMemoryUserStore,
    PreferenceRow,
    ProfileNotFound,
    ProfilePatch,
    SqlUserStore,
    TasteRow,
)


@pytest.fixture()
def sql_store(db_engine):
    with db_engine.begin() as conn:  # user_pantry가 ingredient를 참조한다
        write_compiled(conn, load_files().knowledge)
    return SqlUserStore(db_engine)


def scenario(store):
    a = store.create("엄마", 3, 4)
    b = store.create("아이")
    with pytest.raises(DuplicateProfileName):
        store.create("엄마")
    store.update(a.id, ProfilePatch(
        skill_level=2, pantry=["egg", "rice", "egg"], equipment=["오븐"],
        tastes=[TasteRow("spicy", 1, 2), TasteRow("salty", 3, None)],
        preferences=[PreferenceRow("allergen_group", "shrimp", -1, 1.0, True),
                     PreferenceRow("cuisine", "한식", 1, 0.8, False),
                     PreferenceRow("cuisine", "한식", 1, 0.5, False)],  # 같은 대상은 마지막 값
    ))
    store.update(a.id, ProfilePatch(display_name="엄마2"))  # 목록 필드는 그대로
    with pytest.raises(DuplicateProfileName):
        store.update(b.id, ProfilePatch(display_name="엄마2"))
    with pytest.raises(ProfileNotFound):
        store.get(999)
    store.delete(b.id)
    return [(p.display_name, p.skill_level, p.household_size, p.preferences, p.tastes, p.pantry, p.equipment)
            for p in store.list()]


def test_sql_store_matches_memory_store(sql_store):
    got = scenario(sql_store)
    assert got == scenario(InMemoryUserStore())
    name, skill, household, prefs, tastes, pantry, equipment = got[0]
    assert (name, skill, household) == ("엄마2", 2, 4)
    assert pantry == ("egg", "rice") and equipment == ("오븐",)
    assert prefs[0] == PreferenceRow("allergen_group", "shrimp", -1, 1.0, True)
    assert prefs[1].strength == 0.5
