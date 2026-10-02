"""DB 접속 설정. 환경변수 → 저장소 루트의 .env 순서로 읽는다."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """KEY=VALUE 형식의 .env를 읽어, 아직 설정되지 않은 환경변수만 채운다."""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def database_url(var: str = "DATABASE_URL") -> str | None:
    load_dotenv()
    return os.environ.get(var) or None
