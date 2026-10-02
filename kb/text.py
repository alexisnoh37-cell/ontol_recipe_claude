"""식재료 이름·별칭 정규화."""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def normalize_term(text: str) -> str:
    """NFC 정규화, 모든 공백 제거, 라틴 문자 소문자화.

    "다진 마늘"과 "다진마늘", "Olive Oil"과 "oliveoil"을 같은 키로 만든다.
    """
    return _WHITESPACE.sub("", unicodedata.normalize("NFC", text)).lower()
