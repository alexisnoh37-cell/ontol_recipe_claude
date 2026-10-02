"""엔진 설정. config/weights.yaml, config/engine.yaml 로딩은 Phase 1에서 구현한다.

기본 양념 목록은 설정이 아니라 KnowledgeSnapshot.pantry_staples로 받는다(컴파일 시 반영).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EngineConfig:
    weights: Mapping[str, Any] = field(default_factory=dict)  # config/weights.yaml 내용
    serve_draft_recipes: bool = False  # config/engine.yaml
