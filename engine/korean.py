"""한국어 표시 도우미: 받침에 맞는 조사 (설명 문장 표시용. 판정에는 쓰지 않는다)."""

from __future__ import annotations

_PAIRS = {"은": ("은", "는"), "는": ("은", "는"), "이": ("이", "가"), "가": ("이", "가"),
          "을": ("을", "를"), "를": ("을", "를"), "과": ("과", "와"), "와": ("과", "와")}
_FALLBACK = {"은": "은(는)", "이": "이(가)", "을": "을(를)", "과": "과(와)"}


def has_batchim(word: str) -> bool | None:
    """마지막 글자가 한글 음절이면 받침 유무, 판단할 수 없으면(영문·숫자·빈 문자열) None.

    끝의 닫는 괄호 표기(예: "버터(무염)")는 괄호 앞 글자로 판단한다.
    """
    text = word.rstrip()
    while text.endswith(")") and "(" in text:
        text = text[: text.rindex("(")].rstrip()
    if not text:
        return None
    code = ord(text[-1]) - 0xAC00
    if 0 <= code <= 11171:
        return code % 28 != 0
    return None


def josa(word: str, particle: str) -> str:
    """word + 받침에 맞는 조사. particle은 "은/는", "이/가", "을/를", "과/와" 중 아무 쪽이나 쓴다."""
    with_b, without_b = _PAIRS[particle[0]]
    b = has_batchim(word)
    if b is None:
        return word + _FALLBACK[with_b]
    return word + (with_b if b else without_b)
