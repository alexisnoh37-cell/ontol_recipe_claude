"""추천 v2 응답 시간 측정 (docs/plan.md 부록 G-8). 기존 scripts/bench.py와 같은 합성 데이터·사용자를 쓴다.

    uv run python scripts/bench_v2.py                         # 레시피 10000개, 형태별 요청 300회, 재정렬 끔
    uv run python scripts/bench_v2.py --fake-jev-ms 300       # 재정렬 켬(가짜 Jev, 지연 300ms 흉내)

성능 기준(p95 200ms)은 "LLM 제외" 기준대로 재정렬을 끈 값으로 본다(D7). 재정렬 켬은 참고값이다.
dish 질의는 합성 레시피 제목에서 고른 낱말과 키워드 문장을 섞는다.
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.bench import percentile, synth_recipes, synth_user  # noqa: E402

from engine.v2.config import load_v2_config  # noqa: E402
from engine.v2.model import V2Request  # noqa: E402
from engine.v2.ports import RerankAnswer  # noqa: E402
from engine.v2.recommend import RecommenderV2  # noqa: E402
from kb import compile_paths  # noqa: E402
from storage.engine_source import CONFIG_DIR, build_recommender  # noqa: E402

PHRASES = ["오늘은 얼큰한 국물이 끌려", "담백한 거", "달달한 반찬", "볶음 요리", "일식 느낌"]


class SleepyJev:
    model = "fake"

    def __init__(self, ms: float):
        self.s = ms / 1000

    def rerank(self, query, *, timeout_s):
        time.sleep(self.s)
        return {c.key: RerankAnswer(0.5, 0.9) for c in query.candidates}


def run(n_recipes: int, n_requests: int, seed: int, fake_jev_ms: float | None, warmup: int = 10) -> dict:
    rng = random.Random(seed)
    ck = compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")
    recipes = synth_recipes(ck, n_recipes, rng)
    v1 = build_recommender(ck, recipes, serve_draft_recipes=False)
    reranker = SleepyJev(fake_jev_ms) if fake_jev_ms is not None else None
    v2 = RecommenderV2.from_v1(v1, load_v2_config(CONFIG_DIR), reranker)
    words = sorted({w for r in recipes for w in r.title.split() if len(w) >= 2})
    out = {"recipes": n_recipes, "requests": n_requests, "rerank": reranker is not None, "fake_jev_ms": fake_jev_ms}
    for mode in ("random", "pantry", "dish"):
        times, items = [], []
        for n in range(n_requests + warmup):
            user, req = synth_user(ck, rng)
            query = rng.choice(PHRASES + words) if mode == "dish" else None
            v2req = V2Request(mode, query=query, seed=n, rerank=reranker is not None,
                              max_time_min=req.max_time_min, time_is_hard=req.time_is_hard, limit=10)
            t = time.perf_counter()
            result = v2.recommend(user, v2req)
            ms = (time.perf_counter() - t) * 1000
            if n >= warmup:
                times.append(ms)
                items.append(len(result.items))
        out[mode] = {"p50_ms": round(percentile(times, 50), 1), "p95_ms": round(percentile(times, 95), 1),
                     "max_ms": round(max(times), 1), "mean_items": round(statistics.fmean(items), 1)}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recipes", type=int, default=10_000)
    ap.add_argument("--requests", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fake-jev-ms", type=float, help="재정렬을 켜고 가짜 Jev 지연(ms)을 흉내 낸다")
    args = ap.parse_args(argv)
    result = run(args.recipes, args.requests, args.seed, args.fake_jev_ms)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    off = result["fake_jev_ms"] is None
    worst = max(result[m]["p95_ms"] for m in ("random", "pantry", "dish"))
    if off:
        print(f"p95 최댓값 {worst}ms - 기준 200ms {'통과' if worst <= 200 else '초과'}")
    return 0 if (not off or worst <= 200) else 1


if __name__ == "__main__":
    raise SystemExit(main())
