"""엔진 설정: config/weights.yaml(점수 가중치·계수)과 config/engine.yaml(실행 옵션).

가중치와 계수는 코드에 두지 않는다(CLAUDE.md). 파일 내용을 EngineConfig.weights로 받고,
Recommender가 ScoringConfig.from_mapping으로 검증해 쓴다. 키가 빠지면 ValueError.
기본 양념 목록은 설정이 아니라 KnowledgeSnapshot.pantry_staples로 받는다(컴파일 시 반영).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

COMPONENTS = ("I", "K", "T", "P", "D", "M")
_WEIGHT_KEYS = {
    "I": "ingredient_coverage",
    "K": "cuisine",
    "T": "taste",
    "P": "ingredient_preference",
    "D": "difficulty",
    "M": "time",
}


@dataclass(frozen=True)
class EngineConfig:
    weights: Mapping[str, Any] = field(default_factory=dict)  # config/weights.yaml 내용
    serve_draft_recipes: bool = False  # config/engine.yaml


def load_engine_config(config_dir: Path, *, serve_draft_recipes: bool | None = None) -> EngineConfig:
    """config_dir의 weights.yaml과 engine.yaml을 읽는다. serve_draft_recipes를 주면 파일 값을 덮어쓴다."""
    weights = _read_yaml(config_dir / "weights.yaml")
    engine = _read_yaml(config_dir / "engine.yaml")
    serve = bool(engine.get("serve_draft_recipes", False)) if serve_draft_recipes is None else serve_draft_recipes
    ScoringConfig.from_mapping(weights)  # 적재 시점에 검증
    return EngineConfig(weights=weights, serve_draft_recipes=serve)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: 최상위가 매핑이 아닙니다")
    return data


@dataclass(frozen=True)
class ScoringConfig:
    """weights.yaml을 검증한 형태 (docs/plan.md 4-4~4-6)."""

    weights: Mapping[str, float]  # I, K, T, P, D, M
    coverage_role_weight: Mapping[str, float]
    substitute_credit: float
    coverage_exclude_optional: bool
    coverage_exclude_pantry_staples: bool
    cuisine_like: float
    cuisine_neutral: float
    cuisine_dislike: float
    preference_neutral: float
    preference_role_weight: Mapping[str, float]  # main, sub, garnish, optional
    difficulty: Mapping[int, float]  # (레시피 난이도 - 사용자 실력) → 점수
    taste_dimensions: tuple[str, ...]
    taste_dimension_weight: Mapping[str, float]
    diversity_top_n: int
    diversity_max_same_cuisine: int
    diversity_max_same_main: int

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> ScoringConfig:
        try:
            w = raw["weights"]
            cov = raw["coverage"]
            cui = raw["cuisine"]
            pref = raw["ingredient_preference"]
            taste = raw["taste"]
            div = raw["diversity"]
            dims = tuple(taste["dimensions"])
            cfg = cls(
                weights={c: float(w[_WEIGHT_KEYS[c]]) for c in COMPONENTS},
                coverage_role_weight={k: float(v) for k, v in cov["role_weight"].items()},
                substitute_credit=float(cov["substitute_credit"]),
                coverage_exclude_optional=bool(cov["exclude_optional"]),
                coverage_exclude_pantry_staples=bool(cov["exclude_pantry_staples"]),
                cuisine_like=float(cui["like"]),
                cuisine_neutral=float(cui["neutral"]),
                cuisine_dislike=float(cui["dislike"]),
                preference_neutral=float(pref["neutral"]),
                preference_role_weight={k: float(v) for k, v in pref["role_weight"].items()},
                difficulty={int(k): float(v) for k, v in raw["difficulty"].items()},
                taste_dimensions=dims,
                taste_dimension_weight={d: float(taste["dimension_weight"][d]) for d in dims},
                diversity_top_n=int(div["top_n"]),
                diversity_max_same_cuisine=int(div["max_same_cuisine"]),
                diversity_max_same_main=int(div["max_same_main_ingredient"]),
            )
        except (KeyError, TypeError, AttributeError) as e:
            raise ValueError(f"config/weights.yaml 형식 오류 또는 누락된 키: {e!r}") from e
        missing = [d for d in range(-2, 3) if d not in cfg.difficulty]
        if missing:
            raise ValueError(f"config/weights.yaml difficulty에 차이 {missing}가 없습니다")
        if "optional" not in cfg.preference_role_weight:
            raise ValueError("config/weights.yaml ingredient_preference.role_weight에 optional이 없습니다")
        return cfg
