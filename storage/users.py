"""사용자 프로필 저장소 (docs/plan.md 3-3). API가 쓰고, 엔진에는 UserContext로 넘긴다.

구현은 두 가지이고 같은 동작을 해야 한다(tests/storage/test_users.py가 SQL 쪽을, tests/api가 메모리 쪽을 검사).
  - SqlUserStore: PostgreSQL(user_profile, user_preference, user_taste, user_pantry, user_equipment)
  - InMemoryUserStore: API 테스트용
값 검증(재료·알레르기 그룹 id가 지식에 있는지)은 API가 한다. 저장소는 저장만 한다.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from typing import Any, Protocol


@dataclass(frozen=True)
class PreferenceRow:
    target_type: str  # ingredient | cuisine | allergen_group
    target_id: str
    polarity: int  # -1 | 1
    strength: float = 1.0
    is_hard: bool = False


@dataclass(frozen=True)
class TasteRow:
    dimension: str
    preferred_level: int | None = None
    max_level: int | None = None


@dataclass(frozen=True)
class Profile:
    id: int
    display_name: str
    skill_level: int = 1
    household_size: int = 1
    preferences: tuple[PreferenceRow, ...] = ()
    tastes: tuple[TasteRow, ...] = ()
    pantry: tuple[str, ...] = ()
    equipment: tuple[str, ...] = ()


class ProfileNotFound(LookupError):
    pass


class DuplicateProfileName(ValueError):
    pass


@dataclass(frozen=True)
class ProfilePatch:
    """None인 필드는 바꾸지 않는다. 목록 필드는 주어지면 통째로 교체한다."""

    display_name: str | None = None
    skill_level: int | None = None
    household_size: int | None = None
    preferences: Sequence[PreferenceRow] | None = None
    tastes: Sequence[TasteRow] | None = None
    pantry: Sequence[str] | None = None
    equipment: Sequence[str] | None = None


class UserStore(Protocol):
    def list(self) -> list[Profile]: ...
    def get(self, profile_id: int) -> Profile: ...
    def create(self, display_name: str, skill_level: int = 1, household_size: int = 1) -> Profile: ...
    def update(self, profile_id: int, patch: ProfilePatch) -> Profile: ...
    def delete(self, profile_id: int) -> None: ...


def _prefs(rows: Iterable[PreferenceRow]) -> tuple[PreferenceRow, ...]:
    uniq = {(r.target_type, r.target_id): r for r in rows}  # 같은 대상은 마지막 값(DB의 PK와 같은 규칙)
    return tuple(sorted(uniq.values(), key=lambda r: (r.target_type, r.target_id)))


def _tastes(rows: Iterable[TasteRow]) -> tuple[TasteRow, ...]:
    uniq = {r.dimension: r for r in rows}
    return tuple(sorted(uniq.values(), key=lambda r: r.dimension))


def _basic(patch: ProfilePatch) -> dict[str, Any]:
    return {k: getattr(patch, k) for k in ("display_name", "skill_level", "household_size")
            if getattr(patch, k) is not None}


class InMemoryUserStore:
    def __init__(self) -> None:
        self._items: dict[int, Profile] = {}
        self._next = 1

    def list(self) -> list[Profile]:
        return sorted(self._items.values(), key=lambda p: p.id)

    def get(self, profile_id: int) -> Profile:
        if profile_id not in self._items:
            raise ProfileNotFound(profile_id)
        return self._items[profile_id]

    def _check_name(self, name: str, own_id: int | None) -> None:
        if any(p.display_name == name and p.id != own_id for p in self._items.values()):
            raise DuplicateProfileName(name)

    def create(self, display_name: str, skill_level: int = 1, household_size: int = 1) -> Profile:
        self._check_name(display_name, None)
        p = Profile(self._next, display_name, skill_level, household_size)
        self._items[p.id] = p
        self._next += 1
        return p

    def update(self, profile_id: int, patch: ProfilePatch) -> Profile:
        p = self.get(profile_id)
        if patch.display_name is not None:
            self._check_name(patch.display_name, profile_id)
        changes = _basic(patch)
        if patch.preferences is not None:
            changes["preferences"] = _prefs(patch.preferences)
        if patch.tastes is not None:
            changes["tastes"] = _tastes(patch.tastes)
        if patch.pantry is not None:
            changes["pantry"] = tuple(sorted(set(patch.pantry)))
        if patch.equipment is not None:
            changes["equipment"] = tuple(sorted(set(patch.equipment)))
        self._items[profile_id] = replace(p, **changes)
        return self._items[profile_id]

    def delete(self, profile_id: int) -> None:
        self.get(profile_id)
        del self._items[profile_id]


class SqlUserStore:
    """호출마다 트랜잭션 하나(engine.begin())."""

    def __init__(self, engine: Any):  # sqlalchemy.Engine
        self.engine = engine

    def _read(self, conn: Any, profile_id: int) -> Profile:
        from sqlalchemy import select

        from storage import tables as t

        row = conn.execute(select(t.user_profile).where(t.user_profile.c.id == profile_id)).mappings().first()
        if row is None:
            raise ProfileNotFound(profile_id)
        prefs = conn.execute(select(t.user_preference).where(t.user_preference.c.user_id == profile_id)).mappings()
        tastes = conn.execute(select(t.user_taste).where(t.user_taste.c.user_id == profile_id)).mappings()
        pantry = conn.scalars(select(t.user_pantry.c.ingredient_id).where(t.user_pantry.c.user_id == profile_id))
        equip = conn.scalars(select(t.user_equipment.c.equipment).where(t.user_equipment.c.user_id == profile_id))
        return Profile(
            id=row["id"], display_name=row["display_name"], skill_level=row["skill_level"],
            household_size=row["household_size"],
            preferences=_prefs(PreferenceRow(r["target_type"], r["target_id"], r["polarity"],
                                             float(r["strength"]), r["is_hard"]) for r in prefs),
            tastes=_tastes(TasteRow(r["dimension"], r["preferred_level"], r["max_level"]) for r in tastes),
            pantry=tuple(sorted(pantry)), equipment=tuple(sorted(equip)),
        )

    def list(self) -> list[Profile]:
        from sqlalchemy import select

        from storage import tables as t

        with self.engine.begin() as conn:
            ids = conn.scalars(select(t.user_profile.c.id).order_by(t.user_profile.c.id)).all()
            return [self._read(conn, i) for i in ids]

    def get(self, profile_id: int) -> Profile:
        with self.engine.begin() as conn:
            return self._read(conn, profile_id)

    def create(self, display_name: str, skill_level: int = 1, household_size: int = 1) -> Profile:
        from sqlalchemy import insert
        from sqlalchemy.exc import IntegrityError

        from storage import tables as t

        try:
            with self.engine.begin() as conn:
                new_id = conn.execute(insert(t.user_profile).values(
                    display_name=display_name, skill_level=skill_level, household_size=household_size,
                ).returning(t.user_profile.c.id)).scalar_one()
                return self._read(conn, new_id)
        except IntegrityError as exc:
            raise DuplicateProfileName(display_name) from exc

    def update(self, profile_id: int, patch: ProfilePatch) -> Profile:
        from sqlalchemy import delete, func, insert, update
        from sqlalchemy.exc import IntegrityError

        from storage import tables as t

        children = (
            (t.user_preference, None if patch.preferences is None else [
                {"target_type": r.target_type, "target_id": r.target_id, "polarity": r.polarity,
                 "strength": r.strength, "is_hard": r.is_hard} for r in _prefs(patch.preferences)]),
            (t.user_taste, None if patch.tastes is None else [
                {"dimension": r.dimension, "preferred_level": r.preferred_level, "max_level": r.max_level}
                for r in _tastes(patch.tastes)]),
            (t.user_pantry, None if patch.pantry is None else [
                {"ingredient_id": i} for i in sorted(set(patch.pantry))]),
            (t.user_equipment, None if patch.equipment is None else [
                {"equipment": e} for e in sorted(set(patch.equipment))]),
        )
        try:
            with self.engine.begin() as conn:
                self._read(conn, profile_id)  # 없으면 ProfileNotFound
                conn.execute(update(t.user_profile).where(t.user_profile.c.id == profile_id)
                             .values(**_basic(patch), updated_at=func.now()))
                for table, rows in children:
                    if rows is None:
                        continue
                    conn.execute(delete(table).where(table.c.user_id == profile_id))
                    if rows:
                        conn.execute(insert(table), [{"user_id": profile_id, **r} for r in rows])
                return self._read(conn, profile_id)
        except IntegrityError as exc:
            if patch.display_name is not None and "display_name" in str(exc.orig):
                raise DuplicateProfileName(patch.display_name) from exc
            raise

    def delete(self, profile_id: int) -> None:
        from sqlalchemy import delete

        from storage import tables as t

        with self.engine.begin() as conn:
            self._read(conn, profile_id)
            conn.execute(delete(t.user_profile).where(t.user_profile.c.id == profile_id))
