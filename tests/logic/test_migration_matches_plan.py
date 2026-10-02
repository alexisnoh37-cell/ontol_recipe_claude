"""초기 마이그레이션이 docs/plan.md 부록 B DDL과 문장 단위로 같은지 확인한다."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def plan_statements() -> list[str]:
    plan = (ROOT / "docs" / "plan.md").read_text(encoding="utf-8")
    start = plan.index("```sql\n", plan.index("## 부록 B")) + len("```sql\n")
    ddl = plan[start:plan.index("```", start)]
    out = []
    for chunk in ddl.split(";"):
        lines = [line for line in chunk.splitlines() if line.strip() and not line.strip().startswith("--")]
        if lines:
            out.append("\n".join(lines))
    return out


def migration_statements() -> list[str]:
    path = ROOT / "migrations" / "versions" / "0001_initial.py"
    spec = importlib.util.spec_from_file_location("m0001", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return [s.strip() for s in module.STATEMENTS]


def test_initial_migration_matches_appendix_b():
    assert migration_statements() == plan_statements()


def test_alembic_ini_is_ascii():
    # Windows에서 Alembic은 ini를 locale 인코딩(cp949)으로 읽는다. 한글이 있으면 실행이 깨진다.
    (ROOT / "alembic.ini").read_bytes().decode("ascii")
