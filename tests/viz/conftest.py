"""시각화 API 테스트 공용 fixture. 실제 knowledge/·data/recipes/(load_files)와 메모리 사용자 저장소."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from storage.engine_source import load_files
from storage.users import InMemoryUserStore


@pytest.fixture(scope="session")
def data():
    return load_files()


@pytest.fixture()
def store():
    return InMemoryUserStore()


@pytest.fixture()
def client(data, store, tmp_path):
    return TestClient(create_app(lambda: data, store, exclusion_log=tmp_path / "exclusions.jsonl"))
