"""Alembic 실행 환경. URL 우선순위: -x url=... → sqlalchemy.url 설정 → DATABASE_URL(.env)."""

from __future__ import annotations

from alembic import context
from sqlalchemy import create_engine, pool

from storage.settings import database_url

config = context.config


def _url() -> str:
    url = context.get_x_argument(as_dictionary=True).get("url") or config.get_main_option("sqlalchemy.url")
    url = url or database_url()
    if not url:
        raise SystemExit("DATABASE_URL이 없습니다. .env.example을 .env로 복사하고 값을 확인하세요.")
    return url


def run_migrations_offline() -> None:
    context.configure(url=_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(connection=connection, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
