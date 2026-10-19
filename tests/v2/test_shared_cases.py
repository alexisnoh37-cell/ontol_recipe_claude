"""공용 시험 세트(tests/shared/v2_cases.json)를 JSON만 읽어 다시 돌린다 (docs/integration/v2_logic_spec.md 10장).

다른 앱이 v2 로직을 다른 언어로 옮겼을 때 같은 방법으로 이 파일을 통과해야 한다. 여기서는
(1) 파일이 엔진의 현재 결과와 같은지(최신인지), (2) 파일 안의 입력만으로 엔진을 조립해 기대 결과가 나오는지 본다.
비교 방법은 옮기는 쪽의 참고 구현이다: compare_case().
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from engine.v2.model import V2Request
from engine.v2.ports import RerankAnswer, RerankError
from engine.v2.profile import SimpleProfile
from scripts import make_shared_cases
from storage.v2_bundle import recommender_from_json

CASES_FILE = Path(__file__).resolve().parents[1] / "shared" / "v2_cases.json"
DATA = json.loads(CASES_FILE.read_text(encoding="utf-8"))
TOL = 1e-3


class TableJudge:
    """명세 10-3의 가짜 Jev(옮기는 쪽도 같은 정의로 구현한다)."""

    model = "table-judge"

    def __init__(self, spec: dict):
        self.spec = spec
        self.aspects: list[str] | None = None  # 마지막으로 요청된 판단 항목(명세 10-4의 6번 비교용)

    def judge(self, profile, candidates, aspects, *, timeout_s):
        self.aspects = list(aspects)
        if self.spec.get("fails"):
            raise RerankError("시험용 실패")
        s = self.spec
        return {c.key: {a: RerankAnswer(s["judge_scores"].get(c.title, s["default"]), s["confidence"])
                        for a in aspects} for c in candidates}

    def screen(self, profile, candidates, *, timeout_s):
        if self.spec.get("fails"):
            raise RerankError("시험용 실패")
        return {c.key: self.spec["screen_scores"].get(c.title, 0.0) for c in candidates}


def run_case(case: dict) -> dict[str, Any]:
    """JSON의 입력만으로 실행해 비교 가능한 형태로 돌려준다."""
    p = case["profile"]
    profile = SimpleProfile(frozenset(p.get("allergens", ())), frozenset(p.get("never_eat", ())),
                            frozenset(p.get("likes", ())), frozenset(p.get("dislikes", ())), p.get("spicy_level"),
                            frozenset(p.get("cuisine_likes", ())), frozenset(p.get("cuisine_dislikes", ())),
                            p.get("skill_level"))
    try:
        user = profile.to_user_context(equipment=DATA["equipment"])
    except ValueError:
        return {"error": "invalid_profile"}
    q = case["request"]
    req = V2Request(mode=q["mode"], query=q.get("query"), pantry=frozenset(q["pantry"]) if "pantry" in q else None,
                    seed=q.get("seed"), rerank=q.get("rerank"), max_time_min=q.get("max_time_min"),
                    time_is_hard=bool(q.get("time_is_hard", False)), limit=q.get("limit"))
    judge = TableJudge(case["judge"]) if case["judge"] else None
    v2 = recommender_from_json(DATA["knowledge"], DATA["recipes"], DATA["config"], judge=judge)
    result = v2.recommend(user, req)
    return {"ranking": result.ranking, "notes": list(result.notes), "aspects": judge.aspects if judge else None,
            "items": [{"id": i.item.recipe_id, "group": i.group, "score": i.item.score,
                       "breakdown": dict(i.item.breakdown), "missing": list(i.item.missing),
                       "substitutions": [[s.need_id, s.use_id] for s in i.item.substitutions],
                       "notes": list(i.notes)} for i in result.items]}


def compare_case(expect: dict, got: dict) -> list[str]:
    """명세 10-4의 비교 규칙. 빈 목록이면 통과."""
    if "error" in expect:
        return [] if got.get("error") == expect["error"] else [f"입력 오류여야 하는데 {got}"]
    if "error" in got:
        return [f"입력 오류가 나면 안 됨: {got}"]
    errs: list[str] = []
    ids = [i["id"] for i in got["items"]]
    for bad in set(ids) & set(expect["must_exclude"]):
        errs.append(f"제외되어야 할 레시피가 나옴: {bad}")
    if got["ranking"] != expect["ranking"]:
        errs.append(f"ranking {got['ranking']} != {expect['ranking']}")
    if sorted(got["notes"]) != sorted(expect["notes"]):
        errs.append(f"notes {got['notes']} != {expect['notes']}")
    if "aspects" in expect and got.get("aspects") != expect["aspects"]:
        errs.append(f"판단 항목 {got.get('aspects')} != {expect['aspects']}")
    want = expect["items"]
    if expect["compare"] == "set":
        if sorted(ids) != sorted(i["id"] for i in want):
            errs.append(f"레시피 집합이 다름: {sorted(ids)} != {sorted(i['id'] for i in want)}")
        got_items = {i["id"]: i for i in got["items"]}
        pairs = [(w, got_items.get(w["id"])) for w in want]
    else:
        if ids != [i["id"] for i in want]:
            errs.append(f"순서가 다름: {ids} != {[i['id'] for i in want]}")
        pairs = list(zip(want, got["items"]))
    for w, g in pairs:
        if g is None:
            continue
        if w["group"] != g["group"]:
            errs.append(f"{w['id']} 묶음 {g['group']} != {w['group']}")
        if abs(w["score"] - g["score"]) > TOL:
            errs.append(f"{w['id']} 점수 {g['score']} != {w['score']}")
        for k, v in w["breakdown"].items():
            if k not in g["breakdown"] or abs(g["breakdown"][k] - v) > TOL:
                errs.append(f"{w['id']} breakdown {k}: {g['breakdown'].get(k)} != {v}")
        if set(g["breakdown"]) != set(w["breakdown"]):
            errs.append(f"{w['id']} breakdown 항목 {sorted(g['breakdown'])} != {sorted(w['breakdown'])}")
        if w["missing"] != g["missing"] or w["substitutions"] != g["substitutions"]:
            errs.append(f"{w['id']} 부족·대체 {g['missing']}/{g['substitutions']} != {w['missing']}/{w['substitutions']}")
        if sorted(w["notes"]) != sorted(g["notes"]):
            errs.append(f"{w['id']} notes {g['notes']} != {w['notes']}")
    return errs


def test_cases_file_is_up_to_date():
    assert make_shared_cases.main(["--check"]) == 0


def test_cases_cover_required_kinds():
    ids = {c["id"] for c in DATA["cases"]}
    for prefix in ("safety_", "spicy_", "pantry_", "dish_", "jev_", "invalid_"):
        assert any(i.startswith(prefix) for i in ids), prefix
    assert DATA["format_version"] == 1


@pytest.mark.parametrize("case", DATA["cases"], ids=[c["id"] for c in DATA["cases"]])
def test_case_from_json_only(case):
    errors = compare_case(case["expect"], run_case(case))
    assert not errors, "\n".join(errors)


def test_comparator_catches_unsafe_item():
    case = next(c for c in DATA["cases"] if c["id"] == "safety_shrimp_random")
    got = run_case(case)
    got["items"].append({"id": case["expect"]["must_exclude"][0], "group": None, "score": 0, "breakdown": {},
                         "missing": [], "substitutions": [], "notes": []})
    assert any("제외되어야 할" in e for e in compare_case(case["expect"], got))
