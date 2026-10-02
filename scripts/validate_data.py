"""데이터 검증 (docs/plan.md 5-4).

    uv run python scripts/validate_data.py          # 지식 + data/recipes/*.yaml
    uv run python scripts/validate_data.py --db     # + DB의 user_pantry, user_preference

검사 항목:
  - 지식: 스키마, 참조, is_processed → derived_from, is_a·derived_from·합집합 순환 (kb.compile)
  - 레시피: 모든 재료가 정규 id에 매핑, concept 노드 금지, cuisine·equipment·technique 어휘,
            published 레시피의 맛 프로필·난이도
  - DB(--db): 보유 재료가 실제 재료이고 concept이 아님, user_preference의 target_id 존재
종료 코드: 0 통과, 1 오류 있음, 2 설정 오류.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

from kb import Issue, KnowledgeError, compile_paths  # noqa: E402
from kb.datacheck import check_pantry, check_preferences, check_recipes  # noqa: E402


def load_recipes(recipes_dir: Path) -> list[tuple[str, object]]:
    if not recipes_dir.is_dir():
        return []
    out = []
    for path in sorted(recipes_dir.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as fh:
            out.append((path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix(), yaml.safe_load(fh)))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--knowledge-dir", type=Path, default=ROOT / "knowledge")
    parser.add_argument("--pantry", type=Path, default=ROOT / "config" / "pantry_staples.yaml")
    parser.add_argument("--recipes-dir", type=Path, default=ROOT / "data" / "recipes")
    parser.add_argument("--db", action="store_true", help="DB의 사용자 데이터도 검사(DATABASE_URL 필요)")
    args = parser.parse_args(argv)

    errors: list[Issue] = []
    try:
        ck = compile_paths(args.knowledge_dir, args.pantry)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    except KnowledgeError as exc:
        print(f"지식 검증 실패: 오류 {len(exc.errors)}건. 지식 오류를 먼저 고쳐야 레시피·사용자 데이터를 검사할 수 있습니다.")
        for e in exc.errors:
            print(f"  {e}")
        return 1
    print(f"지식: 통과 (재료 {len(ck.ingredients)}개, 경고 {len(ck.warnings)}건)")

    recipes = load_recipes(args.recipes_dir)
    recipe_issues = check_recipes(ck, recipes)
    errors += recipe_issues
    print(f"레시피: {len(recipes)}개 검사, 오류 {len(recipe_issues)}건")

    if args.db:
        from sqlalchemy import create_engine, select

        from storage import tables as t
        from storage.settings import database_url

        url = database_url()
        if not url:
            print("DATABASE_URL이 없습니다.", file=sys.stderr)
            return 2
        engine = create_engine(url)
        try:
            with engine.connect() as conn:
                pantry = conn.execute(select(t.user_pantry.c.user_id, t.user_pantry.c.ingredient_id)).all()
                p = t.user_preference
                prefs = conn.execute(select(p.c.user_id, p.c.target_type, p.c.target_id)).all()
        finally:
            engine.dispose()
        db_issues = check_pantry(ck, pantry) + check_preferences(ck, prefs)
        errors += db_issues
        print(f"DB: 보유 재료 {len(pantry)}행, 선호 {len(prefs)}행 검사, 오류 {len(db_issues)}건")

    if errors:
        print(f"== 오류 {len(errors)}건 ==")
        for e in errors:
            print(f"  {e}")
        return 1
    print("검증 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
