"""v2 설정: config/v2.yaml (docs/plan.md 부록 G-7). 형식이 틀리거나 키가 빠지면 ValueError."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from engine.v2.ports import ASPECTS

TASTE_DIMENSIONS = ("spicy", "salty", "sweet", "sour", "umami", "savory")
SIMILARITY_KEYS = ("title", "ingredient", "keyword", "anchor")


@dataclass(frozen=True)
class KeywordRule:
    match: tuple[str, ...]
    taste: Mapping[str, tuple[int | None, int | None]]  # 차원 → (min, max)
    cuisine: str | None
    title_any: tuple[str, ...]


@dataclass(frozen=True)
class V2Config:
    near_max_missing: int
    random_default_limit: int
    dish_pool_size: int
    dish_s_weight: float
    dish_similarity: Mapping[str, float]
    dish_min_term_len: int
    dish_keywords: tuple[KeywordRule, ...]
    rerank_enabled: bool
    rerank_model: str
    rerank_top_n: int
    rerank_jev_weight: float
    rerank_min_confidence: float
    rerank_timeout_ms: int
    spicy_inference_enabled: bool = False
    spicy_markers: frozenset[str] = frozenset()
    spicy_title_markers: tuple[str, ...] = ()
    ranking_mode: str = "rules"  # jev | rules (D10)
    ranking_pool_size: int = 40
    ranking_min_pool: int = 10
    ranking_screen_max: int = 1200
    ranking_screen_chunk: int = 250
    ranking_timeout_ms: int = 8000
    aspect_weights: Mapping[str, float] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> V2Config:
        try:
            pantry, rnd, dish, rr = raw["pantry"], raw["random"], raw["dish"], raw["rerank"]
            spicy = raw.get("spicy_inference") or {}
            ranking = raw.get("ranking") or {}
            sim = {k: float(dish["similarity"][k]) for k in SIMILARITY_KEYS}
            cfg = cls(
                near_max_missing=int(pantry["near_max_missing"]),
                random_default_limit=int(rnd["default_limit"]),
                dish_pool_size=int(dish["pool_size"]),
                dish_s_weight=float(dish["s_weight"]),
                dish_similarity=sim,
                dish_min_term_len=int(dish["min_term_len"]),
                dish_keywords=tuple(_rule(r) for r in dish["keywords"]),
                rerank_enabled=bool(rr["enabled"]),
                rerank_model=str(rr["model"]),
                rerank_top_n=int(rr["top_n"]),
                rerank_jev_weight=float(rr["jev_weight"]),
                rerank_min_confidence=float(rr["min_confidence"]),
                rerank_timeout_ms=int(rr["timeout_ms"]),
                spicy_inference_enabled=bool(spicy.get("enabled", False)),
                spicy_markers=frozenset(str(m) for m in spicy.get("markers") or ()),
                spicy_title_markers=tuple(str(m) for m in spicy.get("title_markers") or ()),
                ranking_mode=str(ranking.get("mode", "rules")),
                ranking_pool_size=int(ranking.get("pool_size", 40)),
                ranking_min_pool=int(ranking.get("min_pool", 10)),
                ranking_screen_max=int(ranking.get("screen_max", 1200)),
                ranking_screen_chunk=int(ranking.get("screen_chunk", 250)),
                ranking_timeout_ms=int(ranking.get("timeout_ms", 8000)),
                aspect_weights={str(k): float(v) for k, v in (ranking.get("aspect_weights") or {}).items()},
            )
        except (KeyError, TypeError, AttributeError) as e:
            raise ValueError(f"config/v2.yaml 형식 오류 또는 누락된 키: {e!r}") from e
        for name, value in (("dish.s_weight", cfg.dish_s_weight), ("rerank.jev_weight", cfg.rerank_jev_weight),
                            ("rerank.min_confidence", cfg.rerank_min_confidence)):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"config/v2.yaml {name}는 0~1이어야 합니다: {value}")
        if cfg.near_max_missing < 0 or cfg.dish_pool_size < 1 or cfg.rerank_top_n < 1 or cfg.rerank_timeout_ms < 1:
            raise ValueError("config/v2.yaml 개수·시간 값은 양수여야 합니다(near_max_missing은 0 이상)")
        if cfg.ranking_mode not in ("jev", "rules"):
            raise ValueError(f"config/v2.yaml ranking.mode는 jev 또는 rules입니다: {cfg.ranking_mode}")
        if cfg.ranking_mode == "jev":
            unknown = sorted(set(cfg.aspect_weights) - set(ASPECTS))
            missing = sorted(set(ASPECTS) - set(cfg.aspect_weights))
            if unknown or missing or any(w <= 0 for w in cfg.aspect_weights.values()):
                raise ValueError(f"config/v2.yaml ranking.aspect_weights는 {list(ASPECTS)} 모두 양수여야 합니다 "
                                 f"(모름 {unknown}, 빠짐 {missing})")
            if min(cfg.ranking_pool_size, cfg.ranking_screen_max, cfg.ranking_screen_chunk, cfg.ranking_timeout_ms) < 1:
                raise ValueError("config/v2.yaml ranking 개수·시간 값은 양수여야 합니다")
        if cfg.spicy_inference_enabled and not cfg.spicy_markers:
            raise ValueError("config/v2.yaml spicy_inference.markers가 비었습니다(비우면 모든 레시피를 맵지 않다고 보게 됨)")
        if any(w < 0 for w in sim.values()) or not sum(sim.values()):
            raise ValueError("config/v2.yaml dish.similarity 가중치는 0 이상이고 합이 0보다 커야 합니다")
        return cfg


def _rule(raw: Mapping[str, Any]) -> KeywordRule:
    match = tuple(str(m) for m in raw["match"])
    if not match:
        raise ValueError("config/v2.yaml dish.keywords: match가 비었습니다")
    taste: dict[str, tuple[int | None, int | None]] = {}
    for dim, bound in (raw.get("taste") or {}).items():
        if dim not in TASTE_DIMENSIONS:
            raise ValueError(f"config/v2.yaml dish.keywords: 모르는 맛 차원 {dim}")
        taste[dim] = (bound.get("min"), bound.get("max"))
    rule = KeywordRule(match, taste, raw.get("cuisine"), tuple(str(t) for t in raw.get("title_any") or ()))
    if not (rule.taste or rule.cuisine or rule.title_any):
        raise ValueError(f"config/v2.yaml dish.keywords: 조건이 없는 규칙 {match}")
    return rule


def load_v2_config(config_dir: Path) -> V2Config:
    with (config_dir / "v2.yaml").open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    if not isinstance(raw, dict):
        raise ValueError("config/v2.yaml: 최상위가 매핑이 아닙니다")
    return V2Config.from_mapping(raw)
