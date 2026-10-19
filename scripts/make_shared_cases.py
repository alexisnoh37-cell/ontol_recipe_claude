"""추천 v2 공용 시험 세트 생성 (docs/integration/v2_logic_spec.md 10장). 결과: tests/shared/v2_cases.json

    uv run python scripts/make_shared_cases.py           # 다시 만들기
    uv run python scripts/make_shared_cases.py --check   # 파일이 최신인지만 확인(다르면 종료 코드 1)

다른 앱이 v2 로직을 다른 언어로 옮길 때, 이 파일 하나로 "같게 옮겼는지"를 확인한다.
  - 입력이 모두 들어 있다: 작은 지식(knowledge)·레시피(recipes)·설정(config, storage/v2_bundle.py 형식)
  - 사례마다 사용자 정보(profile, 6가지), 요청(request), 가짜 Jev(judge: 제목별 고정 점수), 기대 결과(expect)
  - 기대 결과는 이 저장소의 엔진(engine/v2)이 계산한 값이다. 엔진을 바꾸면 이 스크립트를 다시 돌리고 차이를 검토한다
  - 언어마다 달라지는 것(랜덤 섞기 순서)은 순서 대신 포함 여부로 비교한다(compare: set)
지식·레시피는 tests/allergy/fixtures.py(사람 승인된 알레르기 시험 데이터)에 맛 정보 없는 레시피 3개를 더한 것이다.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from engine.model import Recipe, RecipeIngredient  # noqa: E402
from engine.v2.filters import check_v2  # noqa: E402
from engine.v2.model import V2Request  # noqa: E402
from engine.v2.ports import RerankAnswer, RerankError  # noqa: E402
from engine.v2.profile import SimpleProfile  # noqa: E402
from kb import KnowledgeSources, compile  # noqa: E402
from storage.engine_source import CONFIG_DIR, snapshot_from_compiled  # noqa: E402
from storage.v2_bundle import (  # noqa: E402
    FORMAT_VERSION,
    config_to_json,
    dumps,
    knowledge_to_json,
    recipe_from_json,
    recipe_to_json,
    recommender_from_json,
)
from tests.allergy import fixtures as fx  # noqa: E402

OUT = ROOT / "tests" / "shared" / "v2_cases.json"
EQUIPMENT = list(fx.VOCAB["equipment"])
SPICY_MARKERS = ["gochujang", "kimchi"]  # 시험용 지식에 있는 매운 재료(실제 목록은 config/v2.yaml)
SPICY_TITLE_MARKERS = ["매콤", "고추"]


def unknown(id: str, title: str, *lines: tuple) -> Recipe:
    """맛·난이도·조리시간을 모르는 레시피(식품안전나라 같은 경우)."""
    return Recipe(id=id, title=title, cuisine="미분류", difficulty=None, cook_time_min=None, taste=None,
                  ingredients=tuple(RecipeIngredient(n, line[0], line[1], False, line[0] or "비법 소스")
                                    for n, line in enumerate(lines, start=1)))


EXTRA = [
    unknown("u_mild_potato", "감자 소금찜", ("potato", "main"), ("salt", "seasoning")),
    unknown("u_gochujang_potato", "감자 고추장볶음", ("potato", "main"), ("gochujang", "seasoning")),
    unknown("u_title_spicy", "매콤 버섯구이", ("mushroom", "main"), ("salt", "seasoning")),
]


def build_inputs() -> tuple[dict, list[dict], dict]:
    ck = compile(KnowledgeSources(allergens={"groups": fx.GROUPS, "bundles": fx.BUNDLES}, vocab=fx.VOCAB,
                                  ingredients=(("allergy_fixture", fx.INGREDIENTS),), substitutes=fx.SUBSTITUTES,
                                  pantry_staples={"staples": fx.STAPLES}))
    knowledge = knowledge_to_json(snapshot_from_compiled(ck), ck)
    recipes = [recipe_to_json(r) for r in sorted([*fx.RECIPES, *EXTRA], key=lambda r: r.id)]
    v2 = yaml.safe_load((CONFIG_DIR / "v2.yaml").read_text(encoding="utf-8"))
    v2["spicy_inference"] = {**v2["spicy_inference"], "markers": SPICY_MARKERS, "title_markers": SPICY_TITLE_MARKERS}
    weights = yaml.safe_load((CONFIG_DIR / "weights.yaml").read_text(encoding="utf-8"))
    engine = yaml.safe_load((CONFIG_DIR / "engine.yaml").read_text(encoding="utf-8"))
    engine = {k: v for k, v in engine.items() if k != "recipe_dirs"}  # 파일 경로는 시험과 무관
    return knowledge, recipes, config_to_json(weights, engine, v2)


class TableJudge:
    """시험용 가짜 Jev. 같은 정의를 옮기는 쪽에서도 구현한다(v2_logic_spec.md 10-3).

    judge: 후보마다 요청된 모든 항목에 judge_scores[제목](없으면 default) 점수, 확신도 confidence
    screen: 후보마다 screen_scores[제목](없으면 0)
    fails: true면 judge·screen 모두 실패(오류)
    """

    model = "table-judge"

    def __init__(self, spec: dict):
        self.spec = spec

    def judge(self, profile, candidates, aspects, *, timeout_s):
        if self.spec.get("fails"):
            raise RerankError("시험용 실패")
        s = self.spec
        return {c.key: {a: RerankAnswer(s["judge_scores"].get(c.title, s["default"]), s["confidence"])
                        for a in aspects} for c in candidates}

    def screen(self, profile, candidates, *, timeout_s):
        if self.spec.get("fails"):
            raise RerankError("시험용 실패")
        return {c.key: self.spec["screen_scores"].get(c.title, 0.0) for c in candidates}


def distinct_scores(recipes: list[dict]) -> dict[str, float]:
    """제목마다 겹치지 않는 점수(정렬 동점이 생기지 않게). 제목 가나다순으로 0.98부터 0.03씩 낮춘다."""
    titles = sorted({r["title"] for r in recipes})
    return {t: round(0.98 - 0.03 * i, 2) for i, t in enumerate(titles)}


# 사례: (id, 설명, profile, request, judge 설정 또는 None)
def cases(recipes: list[dict]) -> list[tuple[str, str, dict, dict, dict | None]]:
    jev = {"judge_scores": distinct_scores(recipes), "default": 0.5, "confidence": 0.9, "screen_scores": {},
           "fails": False}
    pantry_all = sorted(fx.PANTRY)
    return [
        # --- 제외(안전) ---
        ("safety_shrimp_random", "새우 알레르기: 랜덤에 새우·새우젓·김치(포함 가능) 레시피가 없다",
         {"allergens": ["shrimp"]}, {"mode": "random", "seed": 1, "limit": 50, "rerank": False}, None),
        ("safety_shrimp_pantry", "새우 알레르기: 내 재료로(모든 재료 보유)에서도 없다. 낙지 → 새우 대체도 쓰지 않는다",
         {"allergens": ["shrimp"]}, {"mode": "pantry", "pantry": pantry_all, "limit": 50, "rerank": False}, None),
        ("safety_shrimp_dish_excluded", "새우 알레르기로 '김치볶음밥'을 찾으면 그 요리는 빠지고 dish_excluded",
         {"allergens": ["shrimp"]}, {"mode": "dish", "query": "김치볶음밥", "limit": 50, "rerank": False}, None),
        ("safety_egg_garnish_optional", "계란 알레르기: 고명·선택 재료로 든 레시피도 제외",
         {"allergens": ["egg"]}, {"mode": "pantry", "pantry": pantry_all, "limit": 50, "rerank": False}, None),
        ("safety_unmapped_with_allergy", "알레르기가 있으면 미매칭 재료(비법 소스) 레시피 제외",
         {"allergens": ["milk"]}, {"mode": "dish", "query": "버섯", "limit": 50, "rerank": False}, None),
        ("safety_unmapped_without_allergy", "알레르기가 없으면 미매칭 재료 레시피도 나온다",
         {}, {"mode": "dish", "query": "버섯", "limit": 50, "rerank": False}, None),
        ("safety_allergy_beats_like", "김치를 좋아해도 새우 알레르기면 김치 레시피 제외",
         {"allergens": ["shrimp"], "likes": ["kimchi"]},
         {"mode": "random", "seed": 2, "limit": 50, "rerank": False}, None),
        ("safety_never_eat_definite_only", "새우 절대 안 먹음: 확실히 든 것만 제외, 김치(포함 가능)는 통과하고 dislike_possible",
         {"never_eat": ["shrimp_raw"]}, {"mode": "dish", "query": "김치볶음밥", "limit": 50, "rerank": False}, None),
        ("safety_bundle", "갑각류 묶음 = 게 + 새우", {"allergens": ["crustacean_bundle"]},
         {"mode": "random", "seed": 3, "limit": 50, "rerank": False}, None),
        ("dislike_is_not_exclusion", "싫어하는 재료(감자)는 제외하지 않는다", {"dislikes": ["potato"]},
         {"mode": "random", "seed": 4, "limit": 50, "rerank": False}, None),
        # --- 매운맛 ---
        ("spicy_limit_with_inference", "매운맛 0: 맛 모르는 레시피는 매운 재료·매운 제목이 없을 때만 통과(spicy_inferred)",
         {"spicy_level": 0}, {"mode": "random", "seed": 5, "limit": 50, "rerank": False}, None),
        ("spicy_five_no_limit", "매운맛 5 = 한도 없음(맛 모르는 레시피도 모두 통과)",
         {"spicy_level": 5}, {"mode": "random", "seed": 6, "limit": 50, "rerank": False}, None),
        # --- 형태(규칙 순위) ---
        ("pantry_groups_rules", "감자만 보유: 지금 바로 / 조금만 사면 묶음과 규칙 순위",
         {"skill_level": 1}, {"mode": "pantry", "pantry": ["potato"], "limit": 50, "rerank": False}, None),
        ("pantry_substitute", "버섯 + 버터 보유: 버섯볶음은 식용유 대신 버터로 지금 바로",
         {}, {"mode": "pantry", "pantry": ["mushroom", "butter"], "limit": 50, "rerank": False}, None),
        ("dish_rules_exact_title", "'감자조림' 찾기(규칙 순위): 정확히 같은 제목이 1위",
         {}, {"mode": "dish", "query": "감자조림", "limit": 50, "rerank": False}, None),
        ("dish_no_match", "아무것도 걸리지 않는 문장(규칙 순위) → 결과 없음, dish_no_match",
         {}, {"mode": "dish", "query": "xyzxyz", "limit": 50, "rerank": False}, None),
        # --- Jev 순위(가짜 Jev) ---
        ("jev_dish", "Jev 순위: '감자' 찾기, 항목은 요청·실력", {"skill_level": 2},
         {"mode": "dish", "query": "감자", "limit": 50}, jev),
        ("jev_pantry_aspects", "Jev 순위: 내 재료로, 항목은 맛·재료 취향·음식 종류·실력·가진 재료. 묶음 경계 유지",
         {"likes": ["potato"], "spicy_level": 2, "cuisine_likes": ["한식"], "skill_level": 1},
         {"mode": "pantry", "pantry": ["potato", "mushroom"], "limit": 50}, jev),
        ("jev_screen_fill", "Jev 순위: 규칙 관련 후보가 없는 문장 → 걸러내기로 보충(jev_screened)",
         {}, {"mode": "dish", "query": "오늘 저녁 뭐 먹지", "limit": 50},
         # 판단 점수를 모두 같게 두어, 최종 순서가 걸러내기 순서(점수 → 같으면 레시피 id 순)를 그대로 따르는지 본다
         {**jev, "judge_scores": {}, "screen_scores": {"버섯볶음": 1.0, "파전": 0.9, "감자구이": 0.8}}),
        ("jev_random_pool", "Jev 순위: 랜덤(후보 = 제외 통과 레시피 전체, 시험 데이터가 40개 미만)",
         {"allergens": ["egg"]}, {"mode": "random", "seed": 7, "limit": 50}, jev),
        ("jev_failure_fallback", "Jev 실패 → 규칙 순위로 대체(jev_unavailable)",
         {}, {"mode": "dish", "query": "감자", "limit": 50}, {**jev, "fails": True}),
        ("jev_spicy_five_not_asked", "매운맛 5는 Jev 맛 취향 항목으로 묻지 않는다",
         {"spicy_level": 5, "likes": ["potato"]}, {"mode": "dish", "query": "감자", "limit": 50}, jev),
        # --- 입력 오류 ---
        ("invalid_like_and_dislike", "같은 재료를 좋아함·싫어함에 동시에 → 입력 오류",
         {"likes": ["potato"], "dislikes": ["potato"]}, {"mode": "random", "seed": 1}, None),
        ("invalid_spicy_range", "매운맛 정도 범위 밖 → 입력 오류", {"spicy_level": 6}, {"mode": "random", "seed": 1}, None),
    ]


def profile_of(p: dict) -> SimpleProfile:
    return SimpleProfile(frozenset(p.get("allergens", ())), frozenset(p.get("never_eat", ())),
                         frozenset(p.get("likes", ())), frozenset(p.get("dislikes", ())), p.get("spicy_level"),
                         frozenset(p.get("cuisine_likes", ())), frozenset(p.get("cuisine_dislikes", ())),
                         p.get("skill_level"))


def request_of(q: dict) -> V2Request:
    return V2Request(mode=q["mode"], query=q.get("query"),
                     pantry=frozenset(q["pantry"]) if "pantry" in q else None, seed=q.get("seed"),
                     rerank=q.get("rerank"), max_time_min=q.get("max_time_min"),
                     time_is_hard=bool(q.get("time_is_hard", False)), limit=q.get("limit"))


def expected(knowledge: dict, recipes: list[dict], config: dict, profile: dict, request: dict,
             judge: dict | None) -> dict[str, Any]:
    try:
        user = profile_of(profile).to_user_context(equipment=EQUIPMENT)
    except ValueError as exc:
        return {"error": "invalid_profile", "message": str(exc)}
    v2 = recommender_from_json(knowledge, recipes, config, judge=TableJudge(judge) if judge else None)
    result = v2.recommend(user, request_of(request))
    # 반드시 빠져야 하는 레시피: 시험 레시피 전체를 v2 제외 규칙으로 판정(형태와 무관한 불변식)
    from engine.filters import UserConstraints
    from engine.model import RecommendRequest

    snapshot = v2.knowledge.snapshot()
    constraints = UserConstraints(snapshot, user, RecommendRequest(max_time_min=request.get("max_time_min"),
                                                                   time_is_hard=bool(request.get("time_is_hard"))))
    must_exclude = sorted(r["id"] for r in recipes
                          if check_v2(constraints, recipe_from_json(r), not_spicy=r["id"] in v2.not_spicy()).exclusions)
    random_rules = request["mode"] == "random" and result.ranking == "rules"
    items = [{"id": i.item.recipe_id, "group": i.group, "score": i.item.score,
              "breakdown": {k: round(v, 3) for k, v in i.item.breakdown.items()},
              "missing": list(i.item.missing),
              "substitutions": [[s.need_id, s.use_id] for s in i.item.substitutions],
              "notes": list(i.notes)} for i in result.items]
    out: dict[str, Any] = {
        "compare": "set" if random_rules else "ordered",
        "ranking": result.ranking,
        "notes": list(result.notes),
        "items": sorted(items, key=lambda x: x["id"]) if random_rules else items,
        "must_exclude": must_exclude,
    }
    if result.ranking == "jev" and v2.judge is not None:
        from engine.v2.recommend import _Run

        out["aspects"] = list(_Run(v2, user, request_of(request)).aspects())
    return out


def build() -> dict[str, Any]:
    knowledge, recipes, config = build_inputs()
    return {
        "format_version": FORMAT_VERSION,
        "description": "추천 v2 공용 시험 세트. 형식·비교 방법: docs/integration/v2_logic_spec.md 10장. "
                       "생성: scripts/make_shared_cases.py(이 저장소 엔진의 계산 결과).",
        "equipment": EQUIPMENT,
        "knowledge": knowledge,
        "recipes": recipes,
        "config": config,
        "cases": [{"id": cid, "description": desc, "profile": prof, "request": req, "judge": judge,
                   "expect": expected(knowledge, recipes, config, prof, req, judge)}
                  for cid, desc, prof, req, judge in cases(recipes)],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="파일이 최신인지만 확인")
    args = ap.parse_args(argv)
    text = dumps(build())
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            print(f"{OUT.relative_to(ROOT)}이(가) 최신이 아닙니다. scripts/make_shared_cases.py로 다시 만드세요.",
                  file=sys.stderr)
            return 1
        print("최신입니다.")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(text.encode("utf-8"))
    data = json.loads(text)
    print(f"만듦: {OUT.relative_to(ROOT)} (사례 {len(data['cases'])}개, 레시피 {len(data['recipes'])}개)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
