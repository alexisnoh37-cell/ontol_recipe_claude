"""지식 원본(knowledge/*.yaml)을 검증·컴파일해 DB에 반영한다 (docs/plan.md 부록 C).

    uv run python scripts/compile_knowledge.py --dry-run
    uv run python scripts/compile_knowledge.py --dump build/knowledge.json
    uv run python scripts/compile_knowledge.py            # DB 반영 (DATABASE_URL 필요)

종료 코드: 0 성공, 1 검증 실패 또는 반영 실패, 2 설정 오류.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from kb import CompiledKnowledge, KnowledgeError, compile_paths  # noqa: E402


def print_report(ck: CompiledKnowledge) -> None:
    s = ck.stats()
    rel = s["relations"]
    print("== 컴파일 결과 ==")
    print(f"재료 {s['ingredients']}개(concept {s['concepts']}), 별칭 {s['aliases']}개, 기본 양념 {s['pantry_staples']}개")
    print(f"관계: is_a {rel['is_a']}, derived_from {rel['derived_from']}, substitute {rel['substitute']}")
    print(f"알레르기 그룹 {s['allergen_groups']}개(묶음 멤버 {s['group_members']}), 직접 지정 {s['ingredient_allergens']}건")
    print(f"산출물: ancestor {s['ancestors']}, contains {s['contains']}, allergen_closure {s['allergen_closure']}")
    print(f"검수 대상: draft 재료 {s['draft']}개, confidence: low {s['low_confidence']}건")
    print(f"source_hash {ck.source_hash[:12]}")
    if ck.warnings:
        print(f"== 경고 {len(ck.warnings)}건 ==")
        for w in ck.warnings:
            print(f"  {w}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="검증·컴파일 리포트만 출력하고 DB는 건드리지 않는다")
    parser.add_argument("--dump", type=Path, help="컴파일 결과를 JSON으로 저장할 경로")
    parser.add_argument("--knowledge-dir", type=Path, default=ROOT / "knowledge")
    parser.add_argument("--pantry", type=Path, default=ROOT / "config" / "pantry_staples.yaml")
    args = parser.parse_args(argv)

    try:
        ck = compile_paths(args.knowledge_dir, args.pantry)
    except FileNotFoundError as exc:
        print(exc, file=sys.stderr)
        return 2
    except KnowledgeError as exc:
        print(f"== 검증 실패: 오류 {len(exc.errors)}건 (DB는 바뀌지 않음) ==", file=sys.stderr)
        for e in exc.errors:
            print(f"  {e}", file=sys.stderr)
        if exc.warnings:
            print(f"== 경고 {len(exc.warnings)}건 ==", file=sys.stderr)
            for w in exc.warnings:
                print(f"  {w}", file=sys.stderr)
        return 1

    print_report(ck)

    if args.dump:
        args.dump.parent.mkdir(parents=True, exist_ok=True)
        args.dump.write_text(ck.to_json() + "\n", encoding="utf-8")
        print(f"JSON 저장: {args.dump}")

    if args.dry_run:
        print("--dry-run: DB 반영을 건너뜁니다.")
        return 0

    from sqlalchemy import create_engine

    from storage.knowledge_writer import KnowledgeInUseError, write_compiled
    from storage.settings import database_url

    url = database_url()
    if not url:
        print("DATABASE_URL이 없습니다. .env.example을 .env로 복사하거나 --dry-run으로 실행하세요.", file=sys.stderr)
        return 2
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            build_id = write_compiled(conn, ck)
    except KnowledgeInUseError as exc:
        print(exc, file=sys.stderr)
        return 1
    finally:
        engine.dispose()
    print(f"DB 반영 완료: knowledge_build id {build_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
