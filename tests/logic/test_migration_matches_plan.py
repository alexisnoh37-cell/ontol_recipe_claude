"""마이그레이션이 docs/plan.md 부록 B DDL과 문장 단위로 같은지 확인한다."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def plan_statements() -> list[str]:
    """부록 B의 모든 sql 블록(0001 DDL, 0002 ...)을 순서대로 문장 단위로 나눈다."""
    plan = (ROOT / "docs" / "plan.md").read_text(encoding="utf-8")
    start = plan.index("## 부록 B")
    section = plan[start:plan.index("## 부록 C", start)]
    out = []
    for block in section.split("```sql\n")[1:]:
        ddl = block[:block.index("```")]
        for chunk in ddl.split(";"):
            lines = [line for line in chunk.splitlines() if line.strip() and not line.strip().startswith("--")]
            if lines:
                out.append("\n".join(lines))
    return out


def migration_statements() -> list[str]:
    """migrations/versions/의 STATEMENTS를 리비전 순서(파일명 순)로 이어 붙인다."""
    out = []
    for path in sorted((ROOT / "migrations" / "versions").glob("[0-9][0-9][0-9][0-9]_*.py")):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore[union-attr]
        out += [s.strip() for s in module.STATEMENTS]
    return out


def test_migrations_match_appendix_b():
    assert migration_statements() == plan_statements()


def test_alembic_ini_is_ascii():
    # Windows에서 Alembic은 ini를 locale 인코딩(cp949)으로 읽는다. 한글이 있으면 실행이 깨진다.
    (ROOT / "alembic.ini").read_bytes().decode("ascii")
