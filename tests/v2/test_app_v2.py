"""Streamlit 화면(app/v2.py) 실행 확인: 실제 v2 API(메모리 저장소)를 httpx 대신 연결해 화면 스크립트를 끝까지 돌린다."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api.v2 import create_v2_app
from storage.engine_source import load_files
from storage.users import InMemoryUserStore

APP = str(Path(__file__).resolve().parents[2] / "app" / "v2.py")


@pytest.fixture(scope="module")
def api_client(tmp_path_factory):
    log = tmp_path_factory.mktemp("log") / "exclusions.jsonl"
    data = load_files()
    return TestClient(create_v2_app(lambda: data, InMemoryUserStore(), exclusion_log=log))


@pytest.fixture()
def app(api_client, monkeypatch):
    def request(method, url, **kwargs):
        kwargs.pop("timeout", None)
        return api_client.request(method, url.replace("http://127.0.0.1:8000", ""), **kwargs)

    monkeypatch.setattr(httpx, "request", request)
    return AppTest.from_file(APP, default_timeout=120)


def errors(at) -> list[str]:
    return [e.message for e in at.exception] + [e.value for e in at.error]


def test_each_test_persona_runs_all_tabs(app):
    at = app.run()
    assert not errors(at)
    labels = [o for o in at.selectbox[0].options if o.startswith("테스트:")]
    assert len(labels) == 5
    for label in labels:
        at.selectbox[0].select(label).run()
        assert not errors(at), label
        assert any("확인할 것" in m.value for m in at.markdown), label
        at.button(key="random_go").click().run()
        assert not errors(at), label
        at.button(key="pantry_fill").click().run()
        assert at.multiselect(key="pantry_ms").value, label
        at.button(key="pantry_go").click().run()
        assert not errors(at), label
        at.text_input(key="dish_q").input("김치찌개").run()
        at.button(key="dish_go").click().run()
        assert not errors(at), label
