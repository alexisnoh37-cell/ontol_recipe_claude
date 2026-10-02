"""DB 통합 테스트. TEST_DATABASE_URL이 있을 때만 실행한다(테이블을 지우고 다시 만든다)."""

from __future__ import annotations

from pathlib import Path

import pytest

from storage.settings import database_url

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def test_db_url() -> str:
    url = database_url("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL이 없어 DB 통합 테스트를 건너뜁니다")
    return url


@pytest.fixture()
def db_engine(test_db_url):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", test_db_url)
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    engine = create_engine(test_db_url)
    yield engine
    engine.dispose()
