"""연동 명세(docs/integration/recipe_v2_api.md)의 예시가 실제 API와 맞는지 확인한다.

` ```json request ` 블록은 200, ` ```json error-400 `·` ```json error-422 ` 블록은 그 응답 코드여야 한다.
알레르기 그룹·음식 종류 목록이 문서에 빠짐없이 있는지도 본다. Jev는 부르지 않는다(규칙 경로).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.v2 import create_v2_app
from storage.engine_source import load_files
from storage.users import InMemoryUserStore

DOC = Path(__file__).resolve().parents[2] / "docs" / "integration" / "recipe_v2_api.md"
BLOCK = re.compile(r"```json (request|error-400|error-422)\n(.*?)```", re.S)
TEXT = DOC.read_text(encoding="utf-8")
BLOCKS = [(kind, json.loads(body)) for kind, body in BLOCK.findall(TEXT)]


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    data = load_files()
    log = tmp_path_factory.mktemp("log") / "exclusions.jsonl"
    return TestClient(create_v2_app(lambda: data, InMemoryUserStore(), exclusion_log=log))


def test_doc_has_examples():
    kinds = [k for k, _ in BLOCKS]
    assert kinds.count("request") >= 4 and kinds.count("error-400") >= 3 and kinds.count("error-422") >= 3


@pytest.mark.parametrize(("kind", "body"), BLOCKS, ids=[f"{k}-{i}" for i, (k, _) in enumerate(BLOCKS)])
def test_doc_example_matches_api(client, kind, body):
    r = client.post("/v2/recommend", json=body)
    expected = {"request": 200, "error-400": 400, "error-422": 422}[kind]
    assert r.status_code == expected, r.text
    if kind == "request":
        out = r.json()
        assert out["disclaimer"] and isinstance(out["items"], list)


def test_doc_lists_every_allergen_group_and_cuisine(client):
    for g in client.get("/allergen-groups").json():
        assert f"`{g['id']}`" in TEXT, g["id"]
    for c in client.get("/vocab").json()["cuisines"]:
        assert f"`{c}`" in TEXT, c
