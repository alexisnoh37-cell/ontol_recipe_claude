"""engine/은 표준 라이브러리와 pyyaml만 import한다 (docs/plan.md 부록 A, CLAUDE.md 아키텍처 규칙)."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "engine"

ALLOWED_THIRD_PARTY = {"yaml"}
# 금지 목록은 허용 목록에 이미 포함되지 않지만, 실패 메시지를 분명히 하려고 따로 둔다.
FORBIDDEN = {"sqlalchemy", "fastapi", "psycopg", "psycopg2", "streamlit", "alembic", "uvicorn", "starlette",
             "pydantic", "httpx", "kb", "storage", "api", "app"}


def imported_roots(source: str) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", None)) in {
            "__import__", "import_module"
        }:
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                roots.add(node.args[0].value.split(".")[0])
    return roots


def violations(source: str) -> set[str]:
    allowed = set(sys.stdlib_module_names) | ALLOWED_THIRD_PARTY | {"engine", "__future__"}
    return {r for r in imported_roots(source) if r not in allowed or r in FORBIDDEN}


def test_engine_package_exists():
    assert (ENGINE / "__init__.py").is_file()


def test_engine_imports_only_stdlib_and_yaml():
    found = {}
    for path in sorted(ENGINE.rglob("*.py")):
        bad = violations(path.read_text(encoding="utf-8"))
        if bad:
            found[path.relative_to(ROOT).as_posix()] = sorted(bad)
    assert not found, f"engine/에서 허용되지 않은 import: {found}"


def test_importing_engine_does_not_load_forbidden_modules():
    code = (
        "import sys, pkgutil, importlib, engine\n"
        "for m in pkgutil.walk_packages(engine.__path__, 'engine.'):\n"
        "    importlib.import_module(m.name)\n"
        f"bad = sorted(n for n in sys.modules if n.split('.')[0] in {sorted(FORBIDDEN)!r})\n"
        "print(','.join(bad))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "", f"engine import 시 로드된 금지 모듈: {out.stdout.strip()}"


def test_checker_detects_violations():
    # 검사기 자체가 동작하는지(항상 통과하는 테스트가 되지 않도록)
    assert violations("import sqlalchemy") == {"sqlalchemy"}
    assert violations("from fastapi import FastAPI") == {"fastapi"}
    assert violations("from psycopg.rows import dict_row") == {"psycopg"}
    assert violations("import streamlit as st") == {"streamlit"}
    assert violations("from kb import compile") == {"kb"}
    assert violations("import importlib\nimportlib.import_module('storage.tables')") == {"storage"}
    assert violations("import json, dataclasses\nimport yaml\nfrom engine.model import X\nfrom . import y") == set()
