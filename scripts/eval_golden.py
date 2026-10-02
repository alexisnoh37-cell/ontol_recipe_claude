"""골든셋 평가: 페르소나별 상위 3개 적중률 (docs/plan.md 7-3).

    uv run python scripts/eval_golden.py            # 적중률 출력
    uv run python scripts/eval_golden.py --draft    # + docs/review/golden_draft.md(상위 5개와 점수 내역, 다양성 보정 없는 비교) 생성

기대 레시피(expected_top3)는 tests/golden/personas.yaml에 사람이 채운다. 비어 있으면 "미기입"으로 표시한다.
가중치(config/weights.yaml)를 바꿀 때마다 다시 돌린다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.golden.golden import (  # noqa: E402
    build_engine, evaluate, load_personas, overall, render_draft, without_diversity,
)

DRAFT = ROOT / "docs" / "review" / "golden_draft.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--draft", action="store_true", help="docs/review/golden_draft.md를 다시 만든다")
    args = parser.parse_args(argv)

    recommender, names = build_engine()
    personas = load_personas()
    results = evaluate(recommender, personas)
    for r in results:
        top3 = ", ".join(i.recipe_id for i in r.result.items[:3])
        rate = "미기입" if r.hit_rate is None else f"{r.hit_rate:.2f}"
        print(f"{r.persona.id:<16} 적중률 {rate:<6} 상위 3개: {top3}")
    total = overall(results)
    filled = sum(r.hit_rate is not None for r in results)
    print(f"전체 상위 3개 적중률: {'미기입' if total is None else f'{total:.2f}'} (기입 {filled}/{len(results)})")
    if args.draft:
        plain = evaluate(without_diversity(recommender), personas)
        DRAFT.write_text(render_draft(results, names, no_diversity=plain), encoding="utf-8")
        print(f"초안 생성: {DRAFT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
