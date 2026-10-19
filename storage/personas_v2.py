"""추천 v2 테스트 페르소나 로딩 (docs/plan.md 부록 G-11). 파일: data/personas/v2_test_personas.yaml.

골든셋 페르소나(storage/personas.py)와 별개다. 사용자 정보는 6가지 입력(engine/v2/profile.py SimpleProfile)이다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from engine.v2.profile import SimpleProfile
from storage.engine_source import ROOT

V2_PERSONAS = ROOT / "data" / "personas" / "v2_test_personas.yaml"


@dataclass(frozen=True)
class V2Persona:
    id: str
    name: str
    description: str
    profile: SimpleProfile
    try_pantry: tuple[str, ...] = ()
    try_dish: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict, compare=False)


def profile_from_mapping(p: dict[str, Any]) -> SimpleProfile:
    profile = SimpleProfile(
        allergens=frozenset(p.get("allergens") or ()),
        never_eat=frozenset(p.get("never_eat") or ()),
        likes=frozenset(p.get("likes") or ()),
        dislikes=frozenset(p.get("dislikes") or ()),
        spicy_level=p.get("spicy_level"),
        cuisine_likes=frozenset(p.get("cuisine_likes") or ()),
        cuisine_dislikes=frozenset(p.get("cuisine_dislikes") or ()),
        skill_level=p.get("skill_level"),
    )
    profile.validate()
    return profile


def load_v2_personas(path: Path = V2_PERSONAS) -> list[V2Persona]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    out = []
    for p in data["personas"]:
        tries = p.get("try") or {}
        out.append(V2Persona(p["id"], p["name"], p.get("description", ""), profile_from_mapping(p),
                             tuple(tries.get("pantry") or ()), tuple(tries.get("dish") or ()),
                             tuple(p.get("checks") or ()), raw=p))
    return out
