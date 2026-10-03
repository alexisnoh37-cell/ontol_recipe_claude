"""시각화 시연용 저장 프로필 3개를 DB에 만든다(docs/plan.md 부록 D-5, viz-5). 같은 이름이 이미 있으면 건너뛴다.

    uv run python scripts/seed_demo_profiles.py            # DATABASE_URL(.env)의 DB에 생성
    uv run python scripts/seed_demo_profiles.py --dry-run  # 재료·그룹 id 검증만

시연 장면(README "시연 순서"):
  - 시연: 새우 알레르기   → 3단계에서 돼지고기 김치찌개(배추김치 → 새우젓 → 새우)·계란찜(선택 재료 새우젓) 제외
  - 시연: 매운 것 못 먹음 → 3단계에서 매운 레시피가 회색으로 가라앉음(매운맛 한도 1)
  - 시연: 견과류 알레르기 → 3단계에서 멸치볶음(아몬드 → 기타 견과류 ⊂ 견과류) 제외
id는 실행 전에 실제 knowledge/ 컴파일 결과로 확인한다(모르는 id면 아무것도 쓰지 않음).
종료 코드: 0 성공, 1 id 오류, 2 설정 오류.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kb import CompiledKnowledge, compile_paths  # noqa: E402
from storage.users import PreferenceRow, ProfilePatch, TasteRow, UserStore  # noqa: E402


@dataclass(frozen=True)
class DemoProfile:
    name: str
    pantry: tuple[str, ...]
    allergen_groups: tuple[str, ...] = ()
    spicy_max: int | None = None
    skill_level: int = 2
    equipment: tuple[str, ...] = ("냄비", "프라이팬")
    scene: str = field(default="", compare=False)


DEMO_PROFILES = (
    DemoProfile("시연: 새우 알레르기", ("kimchi", "pork", "tofu", "egg", "green_onion"), allergen_groups=("shrimp",),
                scene="김치찌개·계란찜이 새우 경로로 제외"),
    DemoProfile("시연: 매운 것 못 먹음", ("pork", "squid", "tofu", "onion"), spicy_max=1,
                scene="매운 레시피가 회색으로 제외"),
    DemoProfile("시연: 견과류 알레르기", ("anchovy", "beef", "potato"), allergen_groups=("nuts_bundle",),
                scene="멸치볶음(아몬드) 제외"),
)


def check_ids(ck: CompiledKnowledge, profiles: tuple[DemoProfile, ...] = DEMO_PROFILES) -> list[str]:
    usable = {i.id for i in ck.ingredients if i.kind != "concept"}
    groups = {g.id for g in ck.allergen_groups}
    equipment = set(ck.vocab["equipment"])
    errors = []
    for p in profiles:
        errors += [f"{p.name}: 모르는 재료(또는 concept) {i}" for i in p.pantry if i not in usable]
        errors += [f"{p.name}: 모르는 알레르기 그룹 {g}" for g in p.allergen_groups if g not in groups]
        errors += [f"{p.name}: 모르는 조리기구 {e}" for e in p.equipment if e not in equipment]
    return errors


def seed(store: UserStore, profiles: tuple[DemoProfile, ...] = DEMO_PROFILES) -> list[tuple[str, int, bool]]:
    """(이름, 프로필 id, 새로 만들었는지). 이름이 같은 프로필이 있으면 내용을 바꾸지 않고 건너뛴다."""
    existing = {p.display_name: p.id for p in store.list()}
    out = []
    for p in profiles:
        if p.name in existing:
            out.append((p.name, existing[p.name], False))
            continue
        created = store.create(p.name, skill_level=p.skill_level)
        store.update(created.id, ProfilePatch(
            pantry=p.pantry, equipment=p.equipment,
            preferences=[PreferenceRow("allergen_group", g, -1, 1.0, True) for g in p.allergen_groups],  # 부록 B CHECK
            tastes=[TasteRow("spicy", None, p.spicy_max)] if p.spicy_max is not None else [],
        ))
        out.append((p.name, created.id, True))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="id 검증만 하고 DB는 건드리지 않는다")
    args = ap.parse_args(argv)

    errors = check_ids(compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml"))
    for e in errors:
        print(e, file=sys.stderr)
    if errors:
        return 1
    if args.dry_run:
        print(f"id 확인 완료: 시연 프로필 {len(DEMO_PROFILES)}개")
        return 0

    from sqlalchemy import create_engine

    from storage.settings import database_url
    from storage.users import SqlUserStore

    url = database_url()
    if not url:
        print("DATABASE_URL이 없습니다(.env 확인).", file=sys.stderr)
        return 2
    for name, pid, created in seed(SqlUserStore(create_engine(url))):
        print(f"{'생성' if created else '건너뜀(이미 있음)'}: {name} (#{pid})")
    print("API가 실행 중이면 /viz에서 프로필 목록을 새로 고치면 보입니다(프로필은 reload 없이 바로 읽음).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
