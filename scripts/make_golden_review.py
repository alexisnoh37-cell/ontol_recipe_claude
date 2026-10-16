"""골든셋 기대값 재검토 자료(docs/review/golden_review.md)를 만든다. 판단(expected_top3)은 사람이 한다.

    uv run python scripts/make_golden_review.py

검수 전(draft) 레시피도 제공한다고 가정한 결과를 보여 준다(config는 바꾸지 않고 serve_draft_recipes 인자로만 계산).
"동점 인정 적중률"은 참고 지표다. 실제 평가 방식(scripts/eval_golden.py, tests/golden)은 바꾸지 않는다.
data/recipes, knowledge, config를 바꾼 뒤 다시 실행한다.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.scoring import _rank_key, missing_count  # noqa: E402
from storage.engine_source import load_files  # noqa: E402
from tests.golden.golden import _profile, hit_rate, load_personas  # noqa: E402

TARGETS = ("korean_lover", "beginner", "multi_allergy", "japanese_lover", "few_ingredients")
KEY_NAMES = ["점수", "I 높은 순", "부족 재료 적은 순", "조리시간 짧은 순", "id 순"]
OUT = ROOT / "docs" / "review" / "golden_review.md"

data = load_files(ROOT)
spec = {r.id: r for r in data.recipes}
names = {i.id: i.name for i in data.knowledge.ingredients}
engines = {"published": data.recommender(serve_draft_recipes=False), "draft": data.recommender(serve_draft_recipes=True)}
personas = load_personas()


def tie_hit_rate(expected, ordered) -> float | None:
    """참고 지표: 기대 레시피가 상위 3개에 있거나, 점수(소수 셋째 자리)가 3위 점수와 같으면 적중."""
    if not expected:
        return None
    third = round(ordered[2].score, 3) if len(ordered) >= 3 else -1
    top3 = {s.candidate.recipe.id for s in ordered[:3]}
    score = {s.candidate.recipe.id: round(s.score, 3) for s in ordered}
    hits = sum(1 for e in expected if e in top3 or score.get(e) == third)
    return hits / min(3, len(expected))


def decided_by(a, b) -> str:
    ka, kb = _rank_key(a), _rank_key(b)
    for i, (x, y) in enumerate(zip(ka, kb)):
        if x != y:
            return KEY_NAMES[i]
    return "같음"


rows_rate = []
for p in personas:
    res = {}
    for name, eng in engines.items():
        _, tr = eng.trace(p.user, p.request)
        items = eng.recommend(p.user, p.request).items
        res[name] = (hit_rate(p.expected_top3, items), tie_hit_rate(p.expected_top3, tr.ordered))
    rows_rate.append((p, res))


def avg(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals)


L = [
    "# 골든셋 기대값 재검토 자료 (data-1)",
    "",
    "> `uv run python scripts/make_golden_review.py`로 생성한다. 손으로 고치지 않는다.",
    "> 신규 레시피(draft)를 모두 제공한다고 가정한 결과다(config 변경 없이 `serve_draft_recipes=True` 인자로만 계산).",
    "> **기대 레시피(expected_top3)는 사람이 고른다. 이 문서는 고르기 위한 자료이며 제안을 담지 않는다.**",
    "> 실제 평가 방식(`scripts/eval_golden.py`, `tests/golden/`)은 바꾸지 않았다.",
    "",
    "## 보는 법",
    "",
    "- 점수 S = 0.30·I + 0.20·K + 0.15·T + 0.15·P + 0.10·D + 0.10·M (config/weights.yaml).",
    "- 순위는 다양성 보정 후 최종 순위. \"점수 순위\"는 보정 전 순위.",
    "- 동점 묶음: 점수를 소수 셋째 자리로 반올림해 같은 레시피를 같은 글자(A, B, …)로 묶었다.",
    "- 엔진의 동점 처리 순서: I 높은 순 → 부족 재료 적은 순 → 조리시간 짧은 순 → id 순(engine/scoring.py `rank`).",
    "- \"앞 순위와 갈린 기준\": 바로 앞 레시피와 같은 동점 묶음일 때 어느 기준에서 순서가 정해졌는지. 다양성 보정으로 자리가 바뀐 경우 따로 적었다.",
    "",
    "## 적중률 요약",
    "",
    "참고 지표 \"동점 인정 적중률\": 기대 레시피가 상위 3개에 있거나, 점수가 3위 점수와 같으면 적중으로 센다. **실제 평가에는 쓰지 않는다.**",
    "",
    "| 페르소나 | 기대 레시피 | 적중률(published만) | 적중률(draft 포함) | 동점 인정(published만) | 동점 인정(draft 포함) |",
    "|---|---|---|---|---|---|",
]
for p, res in rows_rate:
    L.append(f"| `{p.id}` | {', '.join(p.expected_top3)} | {res['published'][0]:.2f} | {res['draft'][0]:.2f} | "
             f"{res['published'][1]:.2f} | {res['draft'][1]:.2f} |")
L.append(f"| **전체** | | **{avg(r['published'][0] for _, r in rows_rate):.2f}** | **{avg(r['draft'][0] for _, r in rows_rate):.2f}** | "
         f"**{avg(r['published'][1] for _, r in rows_rate):.2f}** | **{avg(r['draft'][1] for _, r in rows_rate):.2f}** |")
L.append("")
L.append("회귀 기준(tests/golden `MIN_HIT_RATE`)은 0.85이며 실제 적중률(동점 인정 아님)로 판정한다.")
L.append("")

for p in personas:
    if p.id not in TARGETS:
        continue
    eng = engines["draft"]
    _, tr = eng.trace(p.user, p.request)
    ordered = tr.ordered
    score_rank = {s.candidate.recipe.id: i + 1 for i, s in enumerate(tr.ranked)}
    _, tr_old = engines["published"].trace(p.user, p.request)
    old_rank = {s.candidate.recipe.id: i + 1 for i, s in enumerate(tr_old.ordered)}
    groups: dict[float, str] = {}
    for s in ordered[:10]:
        r = round(s.score, 3)
        if r not in groups:
            groups[r] = chr(ord("A") + len(groups))
    res = dict(rows_rate)[p]
    L += [
        f"## {p.name} (`{p.id}`)",
        "",
        f"{p.description}",
        "",
        *_profile(p, names),
        f"- 현재 expected_top3: **{', '.join(p.expected_top3)}**",
        f"- 적중률: published만 {res['published'][0]:.2f} → draft 포함 {res['draft'][0]:.2f} (동점 인정 {res['draft'][1]:.2f})",
        "",
        "| 순위 | 점수 순위 | 이전 순위(published만) | 레시피 | 상태 | 기대 | 점수 | 동점 묶음 | I | K | T | P | D | M | 부족 재료 수 | 조리시간 | 앞 순위와 갈린 기준 |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, s in enumerate(ordered[:10]):
        rid = s.candidate.recipe.id
        r = spec[rid]
        if i == 0:
            why = "-"
        else:
            prev = ordered[i - 1]
            if score_rank[rid] < score_rank[prev.candidate.recipe.id]:
                why = "다양성 보정(점수가 더 높지만 뒤로 밀림)"
            elif round(prev.score, 3) == round(s.score, 3):
                why = decided_by(prev, s)
            elif score_rank[rid] != score_rank[prev.candidate.recipe.id] + 1:
                why = "다양성 보정(사이 레시피가 뒤로 밀림)"
            else:
                why = "점수"
        L.append(
            f"| {i + 1} | {score_rank[rid]} | {old_rank.get(rid, '신규')} | {r.title} (`{rid}`) | "
            f"{'**신규(draft)**' if r.status == 'draft' else '기존'} | {'★' if rid in p.expected_top3 else ''} | "
            f"{s.score:.3f} | {groups[round(s.score, 3)]} | " + " | ".join(f"{s.breakdown[k]:.2f}" for k in "IKTPDM")
            + f" | {missing_count(s.candidate)} | {r.cook_time_min}분 | {why} |")
    out_of_top = [e for e in p.expected_top3 if e not in {s.candidate.recipe.id for s in ordered[:10]}]
    for e in out_of_top:
        idx = next((i for i, s in enumerate(ordered) if s.candidate.recipe.id == e), None)
        L.append(f"\n- 기대 레시피 `{e}`: 상위 10 밖({'없음' if idx is None else f'{idx + 1}위, {ordered[idx].score:.3f}'})")
    L.append("")

OUT.write_text("\n".join(L).rstrip() + "\n", encoding="utf-8")
print(f"생성: {OUT.relative_to(ROOT).as_posix()}")
