"""엔진 응답 시간 측정 (docs/plan.md 7-4): 합성 레시피 1만 개, LLM 제외, p95 200ms 이하가 Phase 1 관문.

    uv run python scripts/bench.py                    # 레시피 10000개, 요청 300회
    uv run python scripts/bench.py --recipes 2000 --requests 100 --seed 7

지식은 실제 knowledge/를 컴파일해 쓰고(storage.engine_source와 같은 변환), 레시피만 합성한다.
측정 구간은 Recommender.recommend 한 번(후보 → 필터 → 점수 → 다양성 → 설명). 엔진 조립(색인 생성)은 제외.
"""

from __future__ import annotations

import argparse
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.model import (  # noqa: E402
    Preference,
    Recipe,
    RecipeIngredient,
    RecommendRequest,
    Taste,
    TastePreference,
    UserContext,
)
from kb import CompiledKnowledge, compile_paths  # noqa: E402
from storage.engine_source import build_recommender  # noqa: E402

P95_LIMIT_MS = 200.0


def synth_recipes(ck: CompiledKnowledge, n: int, rng: random.Random) -> list[Recipe]:
    usable = sorted(i.id for i in ck.ingredients if i.kind != "concept")
    staples = sorted(ck.pantry_staples)
    non_staple = [i for i in usable if i not in set(staples)]
    cuisines = list(ck.vocab["cuisines"])
    techniques = list(ck.vocab["techniques"])
    equipment = list(ck.vocab["equipment"])
    out = []
    for k in range(n):
        lines: list[tuple[str | None, str, bool]] = []
        picked = rng.sample(non_staple, rng.randint(4, 8))
        mains, rest = picked[: rng.randint(1, 2)], picked[2:]
        lines += [(i, "main", False) for i in mains]
        lines += [(i, "sub", rng.random() < 0.2) for i in rest]
        lines += [(i, "seasoning", False) for i in rng.sample(staples, rng.randint(2, 5))]
        if rng.random() < 0.3:
            lines.append((rng.choice(non_staple), "garnish", True))
        if rng.random() < 0.01:  # 미매칭 재료(알레르기 사용자에게 제외)
            lines.append((None, "sub", False))
        out.append(Recipe(
            id=f"synth_{k:05d}",
            title=f"합성 레시피 {k}",
            cuisine=rng.choice(cuisines),
            difficulty=rng.randint(1, 3),
            cook_time_min=rng.choice([10, 15, 20, 30, 40, 60, 90]),
            ingredients=tuple(RecipeIngredient(n, i, role, opt, i or "알 수 없는 재료")
                              for n, (i, role, opt) in enumerate(lines, start=1)),
            taste=Taste(*(rng.randint(0, 5) for _ in range(6))),
            required_equipment=frozenset({rng.choice(equipment)}) if rng.random() < 0.05 else frozenset(),
            techniques=frozenset(rng.sample(techniques, rng.randint(1, 3))),
            status="published",
        ))
    return out


def synth_user(ck: CompiledKnowledge, rng: random.Random) -> tuple[UserContext, RecommendRequest]:
    usable = sorted(i.id for i in ck.ingredients if i.kind != "concept")
    groups = sorted(g.id for g in ck.allergen_groups)
    cuisines = list(ck.vocab["cuisines"])
    prefs = [Preference("cuisine", rng.choice(cuisines), rng.choice([-1, 1]), round(rng.random(), 2))]
    prefs += [Preference("ingredient", i, rng.choice([-1, 1]), round(rng.random(), 2))
              for i in rng.sample(usable, rng.randint(0, 3))]
    if rng.random() < 0.3:
        prefs.append(Preference("ingredient", rng.choice(usable), -1, 1.0, True))
    user = UserContext(
        skill_level=rng.randint(1, 3),
        allergen_groups=frozenset(rng.sample(groups, rng.choice([0, 0, 1, 1, 2, 3]))),
        preferences=tuple(prefs),
        tastes=(TastePreference("spicy", rng.randint(0, 3), rng.choice([None, 2, 3, 5])),
                TastePreference("salty", rng.randint(0, 5), None)),
        pantry=frozenset(rng.sample(usable, rng.randint(5, 12))),
        equipment=frozenset(rng.sample(list(ck.vocab["equipment"]), 2)),
    )
    req = RecommendRequest(max_time_min=rng.choice([None, 20, 30, 60]), time_is_hard=rng.random() < 0.2, limit=10)
    return user, req


def percentile(values: list[float], p: float) -> float:
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def run(n_recipes: int, n_requests: int, seed: int, warmup: int = 10) -> dict[str, float]:
    rng = random.Random(seed)
    ck = compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")
    t0 = time.perf_counter()
    recommender = build_recommender(ck, synth_recipes(ck, n_recipes, rng), serve_draft_recipes=False)
    build_ms = (time.perf_counter() - t0) * 1000
    users = [synth_user(ck, rng) for _ in range(n_requests + warmup)]
    times, items, excluded = [], [], []
    for n, (user, req) in enumerate(users):
        t = time.perf_counter()
        result = recommender.recommend(user, req)
        ms = (time.perf_counter() - t) * 1000
        if n >= warmup:
            times.append(ms)
            items.append(len(result.items))
            excluded.append(len({e.recipe_id for e in result.exclusions}))
    return {
        "recipes": n_recipes, "requests": n_requests, "build_ms": build_ms,
        "p50_ms": percentile(times, 50), "p95_ms": percentile(times, 95), "max_ms": max(times),
        "mean_ms": statistics.fmean(times), "mean_items": statistics.fmean(items),
        "mean_excluded": statistics.fmean(excluded),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recipes", type=int, default=10_000)
    ap.add_argument("--requests", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)
    r = run(args.recipes, args.requests, args.seed)
    print(f"레시피 {r['recipes']}개(합성), 요청 {r['requests']}회, seed {args.seed}")
    print(f"엔진 조립(색인) {r['build_ms']:.0f}ms")
    print(f"p50 {r['p50_ms']:.1f}ms · p95 {r['p95_ms']:.1f}ms · 최대 {r['max_ms']:.1f}ms · 평균 {r['mean_ms']:.1f}ms")
    print(f"평균 추천 {r['mean_items']:.1f}개, 평균 제외 레시피 {r['mean_excluded']:.1f}개")
    ok = r["p95_ms"] <= P95_LIMIT_MS
    print(f"기준 p95 ≤ {P95_LIMIT_MS:.0f}ms: {'통과' if ok else '초과'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
