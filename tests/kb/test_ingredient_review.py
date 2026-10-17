"""draft 재료 검수 화면(ir-1): 모든 draft 재료가 들어 있고, 미리 채운 값이 규칙대로이며, 화면 파일이 최신인지."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

from kb import compile_paths

ROOT = Path(__file__).resolve().parents[2]


def _lf(text: str) -> str:
    """git 줄바꿈 변환(CRLF)과 무관하게 비교한다."""
    return text.replace("\r\n", "\n")


def _script():
    spec = importlib.util.spec_from_file_location("make_ingredient_review_html",
                                                  ROOT / "scripts" / "make_ingredient_review_html.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_review_html_covers_every_draft_and_is_up_to_date():
    html, data = _script().build()
    ck = compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")
    assert {d["id"] for d in data} == {i.id for i in ck.ingredients if i.status == "draft"}
    assert _lf((ROOT / "docs" / "review" / "ingredient_review.html").read_text(encoding="utf-8")) == _lf(html)


def test_commercial_products_are_not_prefilled_as_reviewed():
    # 시판 제품은 알레르기 목록이 추정이라 포장 표시 확인 전에는 reviewed로 미리 채우지 않는다.
    _, data = _script().build()
    display = yaml.safe_load((ROOT / "config" / "display.yaml").read_text(encoding="utf-8"))
    commercial = set(display["commercial_product_notice"]["ingredients"])
    for d in data:
        assert d["prefill"]["decision"] in {"O", "X", "보류"}
        if d["origin"] == "시판 제품" or d["id"] in commercial:
            assert d["prefill"]["decision"] == "보류", d["id"]
