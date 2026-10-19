"""추천 v2 평가 기준(storage/eval_v2.py, scripts/eval_v2.py, docs/plan.md 부록 G-13)."""

from __future__ import annotations

import json

from engine.model import Preference, Recipe, RecipeIngredient, Taste, TastePreference, UserContext
from engine.v2.model import V2Request
from scripts import eval_v2
from storage.engine_source import snapshot_from_compiled
from storage.eval_v2 import SafetyChecker


def recipe(id, *lines, taste=Taste(), cuisine="한식"):
    return Recipe(id=id, title=id, cuisine=cuisine, difficulty=1, cook_time_min=20, taste=taste,
                  ingredients=tuple(RecipeIngredient(n, i, "main") for n, i in enumerate(lines, start=1)))


def test_safety_checker_is_independent_and_strict(compiled):
    checker = SafetyChecker(snapshot_from_compiled(compiled), not_spicy=frozenset({"mild_unknown"}))
    req = V2Request("random")
    shrimp = UserContext(allergen_groups=frozenset({"shrimp"}))
    assert checker.violations(shrimp, req, recipe("k", "kimchi"))  # 김치 → 새우젓(possible)도 위반
    assert checker.violations(shrimp, req, recipe("u", None))  # 알레르기 사용자 + 미매칭
    assert not checker.violations(shrimp, req, recipe("p", "potato"))
    never = UserContext(preferences=(Preference("ingredient", "shrimp_raw", -1, 1.0, is_hard=True),))
    assert checker.violations(never, req, recipe("s", "shrimp_raw"))
    assert not checker.violations(never, req, recipe("k", "kimchi"))  # possible은 절대 안 먹음 위반 아님(D8)
    hot = UserContext(tastes=(TastePreference("spicy", max_level=1),))
    assert checker.violations(hot, req, recipe("h", "potato", taste=Taste(spicy=3)))
    assert checker.violations(hot, req, recipe("x", "potato", taste=None))  # 모름 + 추정 없음
    assert not checker.violations(hot, req, recipe("mild_unknown", "potato", taste=None))  # 추정 0(D9)


def test_rules_evaluation_on_real_data_has_no_violations(tmp_path):
    md, js = tmp_path / "eval.md", tmp_path / "eval.json"
    assert eval_v2.main(["--ranking", "rules", "--out-md", str(md), "--out-json", str(js)]) == 0
    data = json.loads(js.read_text(encoding="utf-8"))
    assert data["summary"]["rules"]["violations"] == 0
    assert data["meta"]["n_baseline"] == 14 and data["meta"]["n_persona"] == 20 and data["meta"]["n_query"] >= 10
    assert "사람 평가" in md.read_text(encoding="utf-8")
