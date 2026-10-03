"""받침에 맞는 조사(engine/korean.py)와 설명 문장 적용 (Phase 1-5, 표시 전용)."""

from __future__ import annotations

import pytest

from engine.korean import has_batchim, josa


@pytest.mark.parametrize(("word", "particle", "expected"), [
    ("양파", "은", "양파는"), ("두부", "은/는", "두부는"), ("당근", "는", "당근은"),
    ("대파", "이", "대파가"), ("김치", "이/가", "김치가"), ("새우젓", "가", "새우젓이"),
    ("쪽파", "을", "쪽파를"), ("버터", "를", "버터를"), ("식용유", "을/를", "식용유를"), ("굴소스", "을", "굴소스를"),
    ("올리브유", "을", "올리브유를"), ("생크림", "을", "생크림을"), ("밥", "과", "밥과"), ("우유", "과", "우유와"),
    ("버터(무염)", "을", "버터(무염)를"), ("두반장", "이", "두반장이"),
])
def test_josa(word, particle, expected):
    assert josa(word, particle) == expected


def test_non_hangul_falls_back():
    assert has_batchim("MSG") is None
    assert josa("MSG", "을") == "MSG을(를)"
    assert josa("", "이") == "이(가)"
