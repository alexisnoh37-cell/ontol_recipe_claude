"""지식 원본 읽기. 파일 시스템 접근은 이 모듈에만 둔다.

테스트는 파일 없이 `KnowledgeSources`를 dict로 직접 만들어 `kb.compile`에 넘긴다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class KnowledgeSources:
    """YAML을 safe_load한 원본 데이터. 출처 이름은 오류 위치 표시에 쓴다."""

    allergens: Any
    vocab: Any
    ingredients: tuple[tuple[str, Any], ...]  # (출처 이름, 항목 목록)
    substitutes: Any = field(default_factory=list)
    pantry_staples: Any = field(default_factory=lambda: {"staples": []})
    names: dict[str, str] = field(
        default_factory=lambda: {
            "allergens": "allergens.yaml",
            "vocab": "vocab.yaml",
            "substitutes": "substitutes.yaml",
            "pantry_staples": "pantry_staples.yaml",
        }
    )


def _read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def ingredient_files(knowledge_dir: Path) -> list[Path]:
    """ingredients.yaml과 ingredients/*.yaml(이름 정렬 순서)."""
    files: list[Path] = []
    single = knowledge_dir / "ingredients.yaml"
    if single.is_file():
        files.append(single)
    folder = knowledge_dir / "ingredients"
    if folder.is_dir():
        files.extend(sorted(folder.glob("*.yaml")))
    return files


def load_sources(knowledge_dir: Path, pantry_staples_path: Path) -> KnowledgeSources:
    knowledge_dir = Path(knowledge_dir)
    pantry_staples_path = Path(pantry_staples_path)

    def rel(path: Path) -> str:
        try:
            return path.relative_to(knowledge_dir.parent).as_posix()
        except ValueError:
            return path.as_posix()

    allergens_path = knowledge_dir / "allergens.yaml"
    vocab_path = knowledge_dir / "vocab.yaml"
    substitutes_path = knowledge_dir / "substitutes.yaml"

    missing = [p for p in (allergens_path, vocab_path) if not p.is_file()]
    ing_files = ingredient_files(knowledge_dir)
    if not ing_files:
        missing.append(knowledge_dir / "ingredients.yaml")
    if not pantry_staples_path.is_file():
        missing.append(pantry_staples_path)
    if missing:
        raise FileNotFoundError("지식 원본 파일이 없습니다: " + ", ".join(p.as_posix() for p in missing))

    return KnowledgeSources(
        allergens=_read_yaml(allergens_path),
        vocab=_read_yaml(vocab_path),
        ingredients=tuple((rel(p), _read_yaml(p)) for p in ing_files),
        substitutes=_read_yaml(substitutes_path) if substitutes_path.is_file() else [],
        pantry_staples=_read_yaml(pantry_staples_path),
        names={
            "allergens": rel(allergens_path),
            "vocab": rel(vocab_path),
            "substitutes": rel(substitutes_path),
            "pantry_staples": rel(pantry_staples_path),
        },
    )
