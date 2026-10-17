"""현재 추천 로직의 결과를 기준 자료로 남긴다(bl-1). 추천 로직을 바꾸기 전·후 비교용.

    uv run python scripts/make_baseline_recommendations.py

골든셋 페르소나 8명과 보유 재료 시나리오 몇 개를 지금 엔진(config/engine.yaml 그대로: draft 포함, 레시피 1,522개)에 돌려
docs/review/baseline_recommendations.md(사람이 읽는 표)와 docs/review/baseline_recommendations.json(같은 내용)을 만든다.
기준점은 태그 baseline/v1이다. 이 파일은 기록이라 로직이 바뀌어도 고치지 않는다(새 로직 결과는 별도 파일로 만들어 비교).
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.model import RecommendRequest, TastePreference, UserContext  # noqa: E402
from storage.engine_source import load_files  # noqa: E402
from storage.personas import load_personas  # noqa: E402

OUT_MD = ROOT / "docs" / "review" / "baseline_recommendations.md"
OUT_JSON = ROOT / "docs" / "review" / "baseline_recommendations.json"
TOP = 20
TAG = "baseline/v1"

# 페르소나 외 보유 재료 시나리오(설정 없는 사용자 기준). 이름, 설명, UserContext, RecommendRequest
EXTRA = [
    ("fs_friendly", "식품안전나라에 유리한 재료", "단호박·우유·꿀(식품안전나라 레시피가 많이 쓰는 재료)",
     UserContext(skill_level=2, pantry=frozenset({"kabocha", "milk", "honey"})), RecommendRequest()),
    ("almost_empty", "냉장고 거의 빔", "계란·밥만",
     UserContext(skill_level=1, pantry=frozenset({"egg", "rice"})), RecommendRequest()),
    ("common_veg", "흔한 채소와 계란", "양파·감자·당근·계란·대파",
     UserContext(skill_level=2, pantry=frozenset({"onion", "potato", "carrot", "egg", "green_onion"})), RecommendRequest()),
    ("shrimp_allergy", "새우 알레르기", "김치·돼지고기·두부, 새우 알레르기",
     UserContext(skill_level=2, allergen_groups=frozenset({"shrimp"}), pantry=frozenset({"kimchi", "pork", "tofu"})),
     RecommendRequest()),
    ("no_spicy", "매운 것 못 먹음(한도 1)", "닭고기·감자·양파, 매운맛 한도 1",
     UserContext(skill_level=2, pantry=frozenset({"chicken", "potato", "onion"}),
                 tastes=(TastePreference("spicy", max_level=1),)), RecommendRequest()),
    ("quick_meal", "빨리 먹고 싶음(20분 엄수)", "계란·양파·밥·김치, 희망 20분(절대 조건)",
     UserContext(skill_level=2, pantry=frozenset({"egg", "onion", "rice", "kimchi"})),
     RecommendRequest(max_time_min=20, time_is_hard=True)),
]


def origin(spec) -> str:
    if spec.source == "foodsafety":
        return "식품안전나라"
    return "published" if spec.status == "published" else "draft 시드"


def run_scenario(eng, specs, names, sid, title, desc, user, request) -> dict:
    full = eng.recommend(user, replace(request, limit=5000))
    top = full.items[:TOP]
    excluded: dict[str, set[str]] = {}
    for e in full.exclusions:
        excluded.setdefault(e.reason.value, set()).add(e.recipe_id)
    return {
        "id": sid, "title": title, "description": desc,
        "pantry": sorted(names.get(i, i) for i in user.pantry),
        "allergen_groups": sorted(user.allergen_groups),
        "recommendable": len(full.items),
        "recommendable_by_origin": dict(Counter(origin(specs[i.recipe_id]) for i in full.items)),
        "excluded_by_reason": {k: len(v) for k, v in sorted(excluded.items())},
        "top": [{
            "rank": n, "recipe_id": i.recipe_id, "title": i.title, "origin": origin(specs[i.recipe_id]),
            "cuisine": specs[i.recipe_id].cuisine, "score": round(i.score, 3),
            "breakdown": {k: round(v, 3) for k, v in i.breakdown.items()},
            "missing": len(i.missing), "notes": list(i.notes),
        } for n, i in enumerate(top, 1)],
    }


def render(data: dict) -> str:
    out = [
        "# 현재 추천 로직 기준 결과 (baseline/v1)",
        "",
        f"> 생성: `uv run python scripts/make_baseline_recommendations.py`. 기준점 태그 `{data['tag']}`(커밋 `{data['commit']}`). "
        "추천 로직을 바꾸기 전 결과를 남긴 **기록**이라 로직이 바뀌어도 고치지 않는다. 새 로직의 결과는 같은 시나리오로 따로 만들어 나란히 비교한다.",
        "",
        f"엔진: 레시피 {data['recipes']}개({', '.join(f'{k} {v}' for k, v in data['recipes_by_origin'].items())}), "
        f"설정 그대로(draft 포함). 점수 = 0.30·I(재료 보유) + 0.20·K(음식 종류) + 0.15·T(맛) + 0.15·P(재료 선호) + 0.10·D(난이도) + 0.10·M(조리시간). "
        "모르는 값(식품안전나라의 조리시간·난이도·맛)은 0.5.",
        "",
        "## 시나리오 요약",
        "",
        "| 시나리오 | 추천 가능 | 그중 식품안전나라 | 상위 20 출처 | 주요 제외 사유(레시피 수) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for s in data["scenarios"]:
        top_origin = Counter(t["origin"] for t in s["top"])
        reasons = ", ".join(f"{k} {v}" for k, v in sorted(s["excluded_by_reason"].items(), key=lambda kv: -kv[1])[:3]) or "-"
        out.append(f"| {s['title']} | {s['recommendable']} | {s['recommendable_by_origin'].get('식품안전나라', 0)} | "
                   f"{', '.join(f'{k} {v}' for k, v in top_origin.items()) or '-'} | {reasons} |")
    for s in data["scenarios"]:
        out += ["", f"## {s['title']} (`{s['id']}`)", "", f"{s['description']}", "",
                f"- 보유 재료: {', '.join(s['pantry']) or '-'}" + (f" · 알레르기: {', '.join(s['allergen_groups'])}" if s["allergen_groups"] else ""),
                f"- 추천 가능 {s['recommendable']}개 ({', '.join(f'{k} {v}' for k, v in s['recommendable_by_origin'].items()) or '-'}), "
                f"제외 {', '.join(f'{k} {v}' for k, v in s['excluded_by_reason'].items()) or '없음'}", ""]
        if not s["top"]:
            out.append("추천 결과 없음")
            continue
        out += ["| # | 레시피 | 출처 | 음식 종류 | 점수 | I | K | T | P | D | M | 부족 | 메모 |",
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for t in s["top"]:
            b = t["breakdown"]
            flags = [x for x, on in (("검수 전", any("검수 전" in n for n in t["notes"])),
                                     ("정보 없음", any("정보가 없는" in n for n in t["notes"]))) if on]
            out.append(f"| {t['rank']} | {t['title']} | {t['origin']} | {t['cuisine']} | {t['score']:.3f} | "
                       + " | ".join(f"{b[k]:.2f}" for k in ("I", "K", "T", "P", "D", "M"))
                       + f" | {t['missing']} | {', '.join(flags)} |")
    return "\n".join(out) + "\n"


def main() -> int:
    data_src = load_files(ROOT)
    eng = data_src.recommender()
    specs = {s.id: s for s in data_src.recipes}
    names = {i.id: i.name for i in data_src.knowledge.ingredients}
    commit = subprocess.run(["git", "rev-parse", "--short", TAG], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    scenarios = [run_scenario(eng, specs, names, p.id, p.name, p.description, p.user, p.request) for p in load_personas()]
    scenarios += [run_scenario(eng, specs, names, *x) for x in EXTRA]
    data = {
        "tag": TAG, "commit": commit or "?", "recipes": len(specs),
        "recipes_by_origin": dict(Counter(origin(s) for s in specs.values())),
        "top_n": TOP, "scenarios": scenarios,
    }
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_MD.write_text(render(data), encoding="utf-8")
    print(f"기준 결과: {OUT_MD.relative_to(ROOT).as_posix()}, {OUT_JSON.relative_to(ROOT).as_posix()} (시나리오 {len(scenarios)}개)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
