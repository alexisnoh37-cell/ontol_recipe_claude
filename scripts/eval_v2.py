"""추천 v2 평가 (docs/plan.md 부록 G-13). 같은 평가 세트를 규칙 경로와 Jev 경로로 돌려 지표를 비교한다.

    uv run python scripts/eval_v2.py                  # 규칙·Jev 둘 다(TYPESAFE_API_KEY가 없으면 규칙만)
    uv run python scripts/eval_v2.py --ranking rules  # 규칙만(Jev 호출 없음, 빠름)

평가 세트
  - 기준 시나리오: bl-1과 같은 14개(골든셋 페르소나 8명 + 보유 재료 시나리오 6개), 내 재료로. v1 기준 결과와 겹침·골든셋 적중도 본다
  - 테스트 페르소나: data/personas/v2_test_personas.yaml 5명 × (랜덤 seed 2개, 내 재료로, 요리 찾기 문장)
  - 요리 문장: data/eval/v2_queries.yaml(설정 없는 사용자). 기대 제목 단어·재료가 있으면 '요청에 맞음'을 자동으로 센다
결과: docs/review/v2_eval.md(사람이 읽는 표, '사람 평가' 칸 포함), docs/review/v2_eval.json(같은 내용).
Jev 경로는 실제 Jev를 부르므로 토큰을 쓴다(요청당 입력 약 2만~3만, 실행 한 번에 약 50~70회 호출).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import yaml  # noqa: E402

from engine.model import UserContext  # noqa: E402
from engine.v2.config import load_v2_config  # noqa: E402
from engine.v2.model import V2Request  # noqa: E402
from engine.v2.recommend import RecommenderV2  # noqa: E402
from scripts.make_baseline_recommendations import EXTRA  # noqa: E402
from storage.engine_source import CONFIG_DIR, load_files  # noqa: E402
from storage.eval_v2 import Case, SafetyChecker, evaluate_case, render, to_json  # noqa: E402
from storage.personas import load_personas  # noqa: E402
from storage.personas_v2 import load_v2_personas  # noqa: E402

BASELINE_JSON = ROOT / "docs" / "review" / "baseline_recommendations.json"
QUERIES = ROOT / "data" / "eval" / "v2_queries.yaml"
OUT_MD = ROOT / "docs" / "review" / "v2_eval.md"
OUT_JSON = ROOT / "docs" / "review" / "v2_eval.json"
RANDOM_SEEDS = (1, 2)


def build_cases(equipment: frozenset[str]) -> list[Case]:
    baseline = {s["id"]: tuple(t["recipe_id"] for t in s["top"][:10])
                for s in json.loads(BASELINE_JSON.read_text(encoding="utf-8"))["scenarios"]}
    cases: list[Case] = []
    for p in load_personas():
        cases.append(Case(f"golden:{p.id}", "기준 시나리오", f"{p.name}(골든셋)", p.user,
                          V2Request("pantry", max_time_min=p.request.max_time_min,
                                    time_is_hard=p.request.time_is_hard),
                          v1_top10=baseline.get(p.id, ()), golden_top3=p.expected_top3))
    for sid, title, _desc, user, request in EXTRA:
        cases.append(Case(f"extra:{sid}", "기준 시나리오", title, user,
                          V2Request("pantry", max_time_min=request.max_time_min, time_is_hard=request.time_is_hard),
                          v1_top10=baseline.get(sid, ())))
    for p in load_v2_personas():
        user = p.profile.to_user_context(equipment=equipment)
        cases.append(Case(f"persona:{p.id}:random", "테스트 페르소나", f"{p.name} · 랜덤", user,
                          V2Request("random"), seeds=RANDOM_SEEDS))
        cases.append(Case(f"persona:{p.id}:pantry", "테스트 페르소나", f"{p.name} · 내 재료로", user,
                          V2Request("pantry", pantry=frozenset(p.try_pantry))))
        for q in p.try_dish:
            cases.append(Case(f"persona:{p.id}:dish:{q}", "테스트 페르소나", f"{p.name} · \"{q}\"", user,
                              V2Request("dish", query=q)))
    neutral = UserContext(skill_level=2, equipment=equipment)
    for q in yaml.safe_load(QUERIES.read_text(encoding="utf-8"))["queries"]:
        cases.append(Case(f"query:{q['query']}", "요리 문장", f"\"{q['query']}\"", neutral,
                          V2Request("dish", query=q["query"]),
                          expect_title_any=tuple(q.get("expect_title_any") or ()),
                          expect_ingredients=tuple(q.get("expect_ingredients") or ())))
    return cases


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ranking", choices=["both", "rules", "jev"], default="both")
    ap.add_argument("--out-md", type=Path, default=OUT_MD)
    ap.add_argument("--out-json", type=Path, default=OUT_JSON)
    args = ap.parse_args(argv)

    data = load_files()
    v1 = data.recommender()
    cfg = load_v2_config(CONFIG_DIR)
    judge = client = None
    if args.ranking in ("both", "jev"):
        from integrations.jev import JevClient, JevJudge, api_key_from_env

        key = api_key_from_env()
        if key:
            client = JevClient(key, model=cfg.rerank_model)
            judge = JevJudge(client, screen_chunk=cfg.ranking_screen_chunk)
        elif args.ranking == "jev":
            print("TYPESAFE_API_KEY가 없어 Jev 경로를 평가할 수 없습니다", file=sys.stderr)
            return 2
    rankings = ["rules"] + (["jev"] if judge else [])
    v2 = RecommenderV2.from_v1(v1, cfg, judge=judge)
    recipes = {r.id: r for r in v1.recipes.all()}
    origins = {s.id: ("식품안전나라" if s.source == "foodsafety" else s.status) for s in data.recipes}
    checker = SafetyChecker(v1.knowledge.snapshot(), v2.not_spicy())
    usage = (lambda: (client.calls, client.input_tokens)) if client else (lambda: (0, 0))

    cases = build_cases(frozenset(data.knowledge.vocab["equipment"]))
    rows = []
    for case in cases:
        for rk in rankings:
            row = evaluate_case(v2, case, rk, recipes, origins, checker, usage)
            rows.append(row)
            flag = " 위반!" if row.violations else ""
            print(f"[{rk}] {case.title}: {len(row.titles)}개 {row.metrics['latency_ms']:.0f}ms{flag}")

    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True).stdout.strip()
    meta = {"date": date.today().isoformat(), "commit": commit, "recipes": len(recipes),
            "model": cfg.rerank_model if judge else None,
            "n_baseline": sum(c.group == "기준 시나리오" for c in cases),
            "n_persona": sum(c.group == "테스트 페르소나" for c in cases),
            "n_query": sum(c.group == "요리 문장" for c in cases)}
    if client:
        meta["jev_total_calls"] = client.calls
        meta["jev_total_input_tokens"] = client.input_tokens
    args.out_md.write_text(render(rows, rankings, meta), encoding="utf-8", newline="\n")
    args.out_json.write_text(json.dumps(to_json(rows, rankings, meta), ensure_ascii=False, indent=1),
                             encoding="utf-8", newline="\n")
    total = sum(len(r.violations) for r in rows)
    print(f"\n안전 위반 {total}건. 결과: {args.out_md}")
    if client:
        print(f"Jev 호출 {client.calls}회, 입력 토큰 {client.input_tokens:,}")
    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
