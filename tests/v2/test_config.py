"""config/v2.yaml 검증(docs/plan.md 부록 G-7)."""

from __future__ import annotations

import copy

import pytest
import yaml

from engine.v2.config import V2Config, load_v2_config
from tests.support.engine_fixtures import CONFIG_DIR


def raw() -> dict:
    return yaml.safe_load((CONFIG_DIR / "v2.yaml").read_text(encoding="utf-8"))


def test_real_config_loads():
    cfg = load_v2_config(CONFIG_DIR)
    assert cfg.rerank_model == "jev-1.14.0"
    assert cfg.near_max_missing == 2 and cfg.dish_keywords


@pytest.mark.parametrize(("path", "value"), [
    (("rerank", "jev_weight"), 1.5),
    (("rerank", "min_confidence"), -0.1),
    (("dish", "s_weight"), 2),
    (("rerank", "top_n"), 0),
    (("pantry", "near_max_missing"), -1),
])
def test_rejects_out_of_range(path, value):
    data = copy.deepcopy(raw())
    data[path[0]][path[1]] = value
    with pytest.raises(ValueError):
        V2Config.from_mapping(data)


def test_rejects_missing_key():
    data = raw()
    del data["rerank"]["model"]
    with pytest.raises(ValueError):
        V2Config.from_mapping(data)


def test_rejects_unknown_taste_dimension():
    data = raw()
    data["dish"]["keywords"] = [{"match": ["x"], "taste": {"bitter": {"min": 1}}}]
    with pytest.raises(ValueError):
        V2Config.from_mapping(data)


def test_rejects_rule_without_condition():
    data = raw()
    data["dish"]["keywords"] = [{"match": ["x"]}]
    with pytest.raises(ValueError):
        V2Config.from_mapping(data)
