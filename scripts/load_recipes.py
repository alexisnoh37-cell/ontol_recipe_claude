"""레시피 시드(data/recipes/*.yaml)를 검증하고 DB에 넣는다.

    uv run python scripts/load_recipes.py --dry-run   # 검증만
    uv run python scripts/load_recipes.py             # 검증 후 DB 반영(DATABASE_URL 필요)
    uv run python scripts/load_recipes.py --prune     # 시드에 없는 DB 레시피도 삭제

순서: 지식 컴파일(검증 기준) → 레시피 검증(scripts/validate_data.py와 같은 검사) → DB 반영(한 트랜잭션).
오류가 하나라도 있으면 DB를 건드리지 않는다. 재료 FK 때문에 먼저 scripts/compile_knowledge.py로
지식을 DB에 반영해 두어야 한다. status는 시드 값 그대로 넣는다(검수 전에는 draft).
종료 코드: 0 성공, 1 검증 오류, 2 설정 오류.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kb import KnowledgeError, compile_paths  # noqa: E402
from kb.recipes import RecipeSeedError, load_recipe_specs  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="검증만 하고 DB는 건드리지 않는다")
    parser.add_argument("--prune", action="store_true", help="시드에 없는 DB 레시피를 삭제한다")
    parser.add_argument("--knowledge-dir", type=Path, default=ROOT / "knowledge")
    parser.add_argument("--pantry", type=Path, default=ROOT / "config" / "pantry_staples.yaml")
    parser.add_argument("--recipes-dir", type=Path, default=ROOT / "data" / "recipes")
    args = parser.parse_args(argv)

    try:
        ck = compile_paths(args.knowledge_dir, args.pantry)
        specs = load_recipe_specs(ck, args.recipes_dir, ROOT)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    except KnowledgeError as exc:
        print(f"지식 검증 실패: 오류 {len(exc.errors)}건. 먼저 knowledge/를 고치세요.", file=sys.stderr)
        return 1
    except RecipeSeedError as exc:
        print(f"== 레시피 검증 실패: 오류 {len(exc.issues)}건 (DB는 바뀌지 않음) ==", file=sys.stderr)
        for issue in exc.issues:
            print(f"  {issue}", file=sys.stderr)
        return 1

    by_cuisine = Counter(r.cuisine for r in specs)
    by_status = Counter(r.status for r in specs)
    print(f"레시피 검증 통과: {len(specs)}개 ({', '.join(f'{k} {v}' for k, v in sorted(by_cuisine.items()))}; "
          f"{', '.join(f'{k} {v}' for k, v in sorted(by_status.items()))})")
    if args.dry_run:
        print("--dry-run: DB 반영을 건너뜁니다.")
        return 0

    from sqlalchemy import create_engine
    from sqlalchemy.exc import IntegrityError

    from storage.recipe_writer import write_recipes
    from storage.settings import database_url

    url = database_url()
    if not url:
        print("DATABASE_URL이 없습니다. .env.example을 .env로 복사하거나 --dry-run으로 실행하세요.", file=sys.stderr)
        return 2
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            result = write_recipes(conn, specs, prune=args.prune)
    except IntegrityError as exc:
        print("DB 반영 실패(롤백됨). 지식이 DB에 반영되어 있는지 확인하세요: "
              "uv run python scripts/compile_knowledge.py", file=sys.stderr)
        print(f"  {exc.orig}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    print(f"DB 반영: 레시피 {result.written}개")
    if result.pruned:
        print(f"삭제(--prune): {', '.join(result.pruned)}")
    if result.untouched:
        print(f"시드에 없어 그대로 둔 DB 레시피 {len(result.untouched)}개: {', '.join(result.untouched)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
