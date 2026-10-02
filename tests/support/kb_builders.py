"""테스트 안에서 작은 지식 dict를 만들어 kb.compile에 넘기기 위한 도우미.

closure를 손으로 만들지 않는다(docs/plan.md 부록 A). 항상 실제 컴파일러를 통과시킨다.
"""

from __future__ import annotations

import copy
from typing import Any

from kb import CompiledKnowledge, KnowledgeSources, compile

VOCAB = {
    "cuisines": ["한식", "일식", "중식", "양식"],
    "equipment": ["냄비", "프라이팬", "오븐"],
    "techniques": ["볶음", "구이", "끓이기", "베이킹"],
    "categories": ["육류", "해산물", "젓갈", "콩·두부", "곡류·가루", "김치", "양념"],
}

GROUPS = [
    {"id": gid, "display_name": gid, "status": "draft"}
    for gid in ("shrimp", "crab", "squid", "soybean", "wheat", "egg", "milk")
]

BUNDLES = [{"id": "crustacean_bundle", "display_name": "갑각류", "includes": ["shrimp", "crab"], "status": "draft"}]


def ing(id: str, **fields: Any) -> dict[str, Any]:
    """재료 항목. name 기본값은 id(전역 유일 보장), status는 draft."""
    item = {"id": id, "name": fields.pop("name", id), "status": "draft"}
    item.update(fields)
    return item


def sources(
    ingredients: list[dict[str, Any]],
    *,
    groups: list[dict[str, Any]] | None = None,
    bundles: list[dict[str, Any]] | None = None,
    substitutes: list[dict[str, Any]] | None = None,
    staples: list[str] | None = None,
    vocab: dict[str, Any] | None = None,
) -> KnowledgeSources:
    return KnowledgeSources(
        allergens={
            "groups": copy.deepcopy(GROUPS if groups is None else groups),
            "bundles": copy.deepcopy(BUNDLES if bundles is None else bundles),
        },
        vocab=copy.deepcopy(VOCAB if vocab is None else vocab),
        ingredients=(("test_ingredients", copy.deepcopy(ingredients)),),
        substitutes=copy.deepcopy(substitutes or []),
        pantry_staples={"staples": list(staples or [])},
    )


def korean_basics() -> list[dict[str, Any]]:
    """부록 C 불변식 검사용 최소 지식: 해산물·젓갈·새우·오징어·김치·된장."""
    return [
        ing("seafood", name="해산물", kind="concept"),
        ing("jeotgal", name="젓갈류", is_a=["seafood"]),
        ing("shrimp_raw", name="새우", is_a=["seafood"], allergens=[{"group": "shrimp", "certainty": "definite"}]),
        ing("squid_raw", name="오징어", is_a=["seafood"], allergens=[{"group": "squid", "certainty": "definite"}]),
        ing("saeujeot", name="새우젓", is_a=["jeotgal"], derived_from=["shrimp_raw"], is_processed=True),
        ing("kimchi", name="배추김치", aliases=["김치"],
            derived_from=[{"id": "saeujeot", "certainty": "possible"}], is_processed=True),
        ing("soybean", name="대두", allergens=[{"group": "soybean", "certainty": "definite"}]),
        ing("wheat_flour", name="밀가루", allergens=[{"group": "wheat", "certainty": "definite"}]),
        ing("doenjang", name="된장",
            derived_from=["soybean", {"id": "wheat_flour", "certainty": "possible"}], is_processed=True),
        ing("salt", name="소금"),
    ]


def compile_basics(**kwargs: Any) -> CompiledKnowledge:
    return compile(sources(korean_basics(), **kwargs))
