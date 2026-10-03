"""골든셋 페르소나 로딩 (docs/plan.md 7-3, 부록 D-3).

데이터 파일은 tests/golden/personas.yaml(사람이 기대 결과를 기입하는 곳) 그대로다. API(/personas, 시각화)와
골든셋 평가가 같은 변환을 쓰도록 viz-2에서 tests/golden/golden.py에서 옮겼다(API가 tests를 import하지 않게).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from engine.model import Preference, RecommendRequest, TastePreference, UserContext
from storage.engine_source import ROOT

PERSONAS = ROOT / "tests" / "golden" / "personas.yaml"


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    description: str
    user: UserContext
    request: RecommendRequest
    expected_top3: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict, compare=False)


def load_personas(path: Path = PERSONAS) -> list[Persona]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    out = []
    for p in data["personas"]:
        prefs = tuple(
            Preference(x["type"], x["target"], x["polarity"], float(x.get("strength", 1.0)), bool(x.get("hard", False)))
            for x in p.get("preferences", [])
        )
        tastes = tuple(
            TastePreference(x["dimension"], x.get("preferred_level"), x.get("max_level")) for x in p.get("tastes", [])
        )
        user = UserContext(
            skill_level=p["skill_level"],
            allergen_groups=frozenset(p.get("allergen_groups", [])),
            preferences=prefs,
            tastes=tastes,
            pantry=frozenset(p["pantry"]),
            equipment=frozenset(p.get("equipment", [])),
        )
        req = p.get("request") or {}
        request = RecommendRequest(max_time_min=req.get("max_time_min"), time_is_hard=bool(req.get("time_is_hard", False)),
                                   limit=10)
        out.append(Persona(p["id"], p["name"], p["description"], user, request,
                           tuple(p.get("expected_top3") or ()), raw=p))
    return out
