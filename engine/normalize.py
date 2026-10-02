"""입력 정규화 (docs/plan.md 4-1).

자유 입력 재료 이름을 별칭 색인(KnowledgeSnapshot.alias_index)으로 정규 id에 매핑한다.
매핑되지 않은 입력은 돌려주기만 하고, 미매칭 로그(unmapped_term) 기록은 호출자(API)가 한다.
concept 노드(분류 전용)는 보유 재료로 쓸 수 없으므로 매핑되어도 따로 돌려준다(A1).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass

from engine.model import KnowledgeSnapshot

_WHITESPACE = re.compile(r"\s+")


def normalize_term(text: str) -> str:
    """NFC 정규화, 모든 공백 제거, 라틴 문자 소문자화.

    컴파일러(kb/text.py)가 alias_norm을 만드는 규칙과 같아야 한다. engine은 kb를 import할 수 없어
    같은 규칙을 따로 두고, tests/logic/test_normalize.py가 두 구현의 일치를 검사한다.
    """
    return _WHITESPACE.sub("", unicodedata.normalize("NFC", text)).lower()


@dataclass(frozen=True)
class NormalizedInput:
    ids: frozenset[str]  # 매핑된 정규 재료 id(concept 제외)
    unmapped: tuple[str, ...] = ()  # 매핑 실패한 원문(입력 순서)
    concepts: tuple[str, ...] = ()  # concept 노드에 매핑된 원문. 더 구체적인 재료를 고르도록 안내한다


def resolve_terms(snapshot: KnowledgeSnapshot, terms: Iterable[str]) -> NormalizedInput:
    ids: set[str] = set()
    unmapped: list[str] = []
    concepts: list[str] = []
    for term in terms:
        key = normalize_term(term)
        if not key:
            continue
        ingredient_id = snapshot.alias_index.get(key)
        if ingredient_id is None:
            unmapped.append(term)
        elif ingredient_id in snapshot.concept_ids:
            concepts.append(term)
        else:
            ids.add(ingredient_id)
    return NormalizedInput(frozenset(ids), tuple(unmapped), tuple(concepts))


def clean_pantry(snapshot: KnowledgeSnapshot, ids: Iterable[str]) -> frozenset[str]:
    """보유 재료 id 중 지식에 있는 구체 재료만 남긴다(모르는 id, concept 노드는 버린다)."""
    return frozenset(i for i in ids if i in snapshot.ingredient_names and i not in snapshot.concept_ids)
