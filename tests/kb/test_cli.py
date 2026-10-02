"""scripts/compile_knowledge.py, scripts/validate_data.py 종료 코드."""

from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load_script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def copy_knowledge(tmp_path: Path) -> Path:
    target = tmp_path / "knowledge"
    shutil.copytree(ROOT / "knowledge", target)
    return target


def test_dry_run_and_dump(tmp_path, capsys):
    dump = tmp_path / "out" / "knowledge.json"
    assert load_script("compile_knowledge").main(["--dry-run", "--dump", str(dump)]) == 0
    data = json.loads(dump.read_text(encoding="utf-8"))
    assert data["stats"]["ingredients"] > 0
    assert "--dry-run" in capsys.readouterr().out


def test_invalid_knowledge_exits_1_before_touching_db(tmp_path, monkeypatch, capsys):
    kdir = copy_knowledge(tmp_path)
    (kdir / "ingredients" / "zz_typo.yaml").write_text("- id: oops\n  name: 오타\n  stauts: draft\n", encoding="utf-8")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://invalid:invalid@127.0.0.1:1/none")
    # DB 반영 모드여도 검증 실패면 DB에 접속하지 않고 1로 끝난다
    assert load_script("compile_knowledge").main(["--knowledge-dir", str(kdir)]) == 1
    err = capsys.readouterr().err
    assert "unknown_key" in err and "stauts" in err


def test_validate_data_passes_on_repo_data():
    assert load_script("validate_data").main([]) == 0


def test_validate_data_fails_on_concept_recipe_ingredient(tmp_path):
    recipes = tmp_path / "recipes"
    recipes.mkdir()
    (recipes / "bad.yaml").write_text(
        "id: seafood_mix\ntitle: 해물볶음\ncuisine: 한식\ncook_time_min: 15\nsource: test\n"
        "ingredients:\n  - {ingredient: seafood, raw_text: 해산물 200g, role: main}\n",
        encoding="utf-8",
    )
    assert load_script("validate_data").main(["--recipes-dir", str(recipes)]) == 1


def test_yaml_syntax_error_is_reported_not_crashed(tmp_path, capsys):
    kdir = copy_knowledge(tmp_path)
    bad = kdir / "ingredients" / "zz_bad.yaml"
    bad.write_text("- id: oops\n  name: 오타\n  note: '따옴표'로 시작하는 메모\n  status: draft\n", encoding="utf-8")
    assert load_script("compile_knowledge").main(["--dry-run", "--knowledge-dir", str(kdir)]) == 1
    err = capsys.readouterr().err
    assert "yaml_syntax" in err and "zz_bad.yaml:3" in err
