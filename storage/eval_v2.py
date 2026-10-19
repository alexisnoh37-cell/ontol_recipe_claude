"""추천 v2 평가 기준 (docs/plan.md 부록 G-13). scripts/eval_v2.py가 쓴다.

같은 평가 세트를 규칙 경로(ranking rules)와 Jev 경로(ranking jev)로 돌려 같은 지표로 비교한다.
안전 위반은 엔진 필터 코드를 쓰지 않고 컴파일된 지식(closure·contains)으로 따로 다시 판정한다.

지표(상위 k = 5, 다양성·겹침은 10)
  violations      안전 위반 수(알레르기·알레르기 사용자의 미매칭·절대 안 먹음(확실)·매운맛 한도·음식 종류 절대 비선호·
                  조리기구·시간 엄수). 반드시 0
  empty           결과가 0개인가
  like_hit        좋아하는 재료(하위 재료 포함)를 쓰는 레시피 비율(좋아하는 재료가 있을 때)
  dislike_rate    싫어하는 재료를 쓰는 레시피 비율(낮을수록 좋음, 싫어하는 재료가 있을 때)
  cuisine_like    좋아하는 음식 종류 비율 / cuisine_dislike 싫어하는 음식 종류 비율
  skill_fit       난이도를 아는 레시피 중 난이도 ≤ 요리 실력 비율
  request_fit     요리 찾기: 기대 제목 단어나 기대 재료가 맞는 비율(평가 세트에 기대값이 있을 때)
  ready_share     내 재료로: 상위 중 '지금 바로' 비율
  foodsafety      상위 10 중 식품안전나라 레시피 비율
  diversity       상위 10의 서로 다른 주재료 수
  random_change   랜덤: seed 두 개 결과가 다른 비율(1 − 자카드)
  v1_overlap      기준 결과(bl-1, v1)와 상위 10 겹침 비율
  golden_hit      골든셋 기대 상위 3개 중 상위 3에 든 비율
  latency_ms      응답 시간 / jev_calls·jev_input_tokens Jev 사용량
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from engine.candidates import candidate_roles
from engine.model import KnowledgeSnapshot, Recipe, UserContext
from engine.v2.model import V2Request, V2Result
from engine.v2.recommend import RecommenderV2

TOP_K = 5
TOP_WIDE = 10


@dataclass
class Case:
    id: str
    group: str  # 기준 시나리오 / 테스트 페르소나 / 요리 문장
    title: str
    user: UserContext
    req: V2Request
    expect_title_any: tuple[str, ...] = ()
    expect_ingredients: tuple[str, ...] = ()
    v1_top10: tuple[str, ...] = ()
    golden_top3: tuple[str, ...] = ()
    seeds: tuple[int, ...] = ()  # 랜덤: 두 번 돌려 바뀌는 정도를 본다


@dataclass
class Row:
    case: Case
    ranking: str  # 요청한 경로(rules/jev)
    used: str  # 실제로 쓰인 경로(Jev 실패 시 rules)
    titles: list[str]
    metrics: dict[str, float | int | None]
    violations: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class SafetyChecker:
    """엔진 필터와 별개로 결과 레시피의 안전 위반을 판정한다(컴파일된 지식 조회만)."""

    def __init__(self, snapshot: KnowledgeSnapshot, not_spicy: frozenset[str]):
        self.s = snapshot
        self.not_spicy = not_spicy

    def violations(self, user: UserContext, req: V2Request, r: Recipe) -> list[str]:
        s = self.s
        out: list[str] = []
        ids = [line.ingredient_id for line in r.ingredients]
        for g in sorted(user.allergen_groups):
            hit = [i for i in ids if i is not None and i in s.allergen_closure.get(g, {})]
            if hit:
                out.append(f"알레르기 {g}: {hit[0]}")
        if user.allergen_groups and any(i is None or i not in s.ingredient_names for i in ids):
            out.append("알레르기 사용자에게 미매칭 재료")
        hard = [p for p in user.preferences if p.is_hard]
        for p in hard:
            if p.target_type == "ingredient":
                for i in ids:
                    if i == p.target_id or (i and s.contains.get(i, {}).get(p.target_id)
                                            and s.contains[i][p.target_id].certainty == "definite"):
                        out.append(f"절대 안 먹음 {p.target_id}: {i}")
                        break
            elif p.target_type == "cuisine" and r.cuisine == p.target_id:
                out.append(f"음식 종류 절대 비선호 {r.cuisine}")
        limits = [t.max_level for t in user.tastes if t.dimension == "spicy" and t.max_level is not None]
        if limits and min(limits) < 5:
            limit = min(limits)
            if r.taste is not None and r.taste.spicy > limit:
                out.append(f"매운맛 {r.taste.spicy} > 한도 {limit}")
            elif r.taste is None and r.id not in self.not_spicy:
                out.append(f"매운맛 모름(추정 없음), 한도 {limit}")
        if r.required_equipment - user.equipment:
            out.append(f"조리기구 없음: {sorted(r.required_equipment - user.equipment)}")
        if req.time_is_hard and req.max_time_min is not None and r.cook_time_min is not None \
                and r.cook_time_min > req.max_time_min:
            out.append(f"시간 {r.cook_time_min} > {req.max_time_min}")
        return out


def _uses(s: KnowledgeSnapshot, r: Recipe, targets: Iterable[str]) -> bool:
    want = set(targets)
    for line in r.ingredients:
        if line.ingredient_id is None:
            continue
        if line.ingredient_id in want or want & set(s.ancestors.get(line.ingredient_id, {})):
            return True
    return False


def _ratio(flags: Sequence[bool]) -> float | None:
    return sum(flags) / len(flags) if flags else None


def _mains(r: Recipe) -> frozenset[str]:
    roles = candidate_roles(r)
    return frozenset(line.ingredient_id for line in r.ingredients if line.role in roles and line.ingredient_id)


def evaluate_case(v2: RecommenderV2, case: Case, ranking: str, recipes: Mapping[str, Recipe],
                  origins: Mapping[str, str], checker: SafetyChecker,
                  usage: Callable[[], tuple[int, int]] = lambda: (0, 0)) -> Row:
    s = v2.knowledge.snapshot()
    req = case.req if ranking == "jev" else _with(case.req, rerank=False)
    calls0, tokens0 = usage()
    runs: list[tuple[V2Result, float]] = []
    for seed in case.seeds or (None,):
        r_req = _with(req, seed=seed) if seed is not None else req
        t = time.perf_counter()
        result = v2.recommend(case.user, r_req)
        runs.append((result, (time.perf_counter() - t) * 1000))
    calls1, tokens1 = usage()
    result = runs[0][0]
    top = [recipes[i.item.recipe_id] for i in result.items]
    k, wide = top[:TOP_K], top[:TOP_WIDE]
    violations = [f"{r.title}: {v}" for r in top for v in checker.violations(case.user, req, r)]

    soft = [p for p in case.user.preferences if not p.is_hard]
    likes = [p.target_id for p in soft if p.target_type == "ingredient" and p.polarity > 0]
    dislikes = [p.target_id for p in soft if p.target_type == "ingredient" and p.polarity < 0]
    c_like = {p.target_id for p in soft if p.target_type == "cuisine" and p.polarity > 0}
    c_dislike = {p.target_id for p in soft if p.target_type == "cuisine" and p.polarity < 0}
    known_diff = [r for r in k if r.difficulty is not None]
    m: dict[str, Any] = {
        "items": len(top),
        "empty": int(not top),
        "like_hit": _ratio([_uses(s, r, likes) for r in k]) if likes else None,
        "dislike_rate": _ratio([_uses(s, r, dislikes) for r in k]) if dislikes else None,
        "cuisine_like": _ratio([r.cuisine in c_like for r in k]) if c_like else None,
        "cuisine_dislike": _ratio([r.cuisine in c_dislike for r in k]) if c_dislike else None,
        "skill_fit": _ratio([r.difficulty <= case.user.skill_level for r in known_diff]) if known_diff else None,
        "request_fit": None,
        "ready_share": None,
        "foodsafety": _ratio([origins.get(r.id) == "식품안전나라" for r in wide]) if wide else None,
        "diversity": len(frozenset().union(*(_mains(r) for r in wide))) if wide else 0,
        "random_change": None,
        "v1_overlap": (len({r.id for r in wide} & set(case.v1_top10)) / TOP_WIDE) if case.v1_top10 else None,
        "golden_hit": (len({r.id for r in top[:3]} & set(case.golden_top3)) / len(case.golden_top3))
        if case.golden_top3 else None,
        "latency_ms": statistics.fmean(ms for _, ms in runs),
        "jev_calls": calls1 - calls0,
        "jev_input_tokens": tokens1 - tokens0,
    }
    if case.expect_title_any or case.expect_ingredients:
        m["request_fit"] = _ratio([any(w in r.title for w in case.expect_title_any)
                                   or _uses(s, r, case.expect_ingredients) for r in k])
    if case.req.mode == "pantry":
        m["ready_share"] = _ratio([i.group == "ready" for i in result.items[:TOP_K]])
    if len(runs) > 1:
        a = {i.item.recipe_id for i in runs[0][0].items}
        b = {i.item.recipe_id for i in runs[1][0].items}
        m["random_change"] = 1 - len(a & b) / len(a | b) if a | b else 0.0
    return Row(case, ranking, result.ranking, [r.title for r in k], m, violations, list(result.notes))


def _with(req: V2Request, **changes: Any) -> V2Request:
    from dataclasses import replace

    return replace(req, **changes)


METRICS = [
    ("violations", "안전 위반(반드시 0)", "low"),
    ("empty", "결과 없음 비율", "low"),
    ("like_hit", "좋아하는 재료 적중", "high"),
    ("dislike_rate", "싫어하는 재료 포함", "low"),
    ("cuisine_like", "좋아하는 음식 종류", "high"),
    ("cuisine_dislike", "싫어하는 음식 종류", "low"),
    ("skill_fit", "실력에 맞는 난이도", "high"),
    ("request_fit", "요청에 맞음(요리 찾기)", "high"),
    ("ready_share", "지금 바로 비율(내 재료로)", "high"),
    ("foodsafety", "식품안전나라 비율(상위 10)", "-"),
    ("diversity", "서로 다른 주재료 수(상위 10)", "high"),
    ("random_change", "랜덤 seed 간 변화", "high"),
    ("v1_overlap", "v1 기준 결과와 겹침(상위 10)", "-"),
    ("golden_hit", "골든셋 기대 상위 3 적중", "high"),
    ("latency_ms", "평균 응답 시간(ms)", "low"),
    ("jev_calls", "요청당 Jev 호출", "low"),
    ("jev_input_tokens", "요청당 Jev 입력 토큰", "low"),
]


def summarize(rows: Sequence[Row], ranking: str) -> dict[str, float | None]:
    mine = [r for r in rows if r.ranking == ranking]
    out: dict[str, float | None] = {"violations": float(sum(len(r.violations) for r in mine)),
                                    "fallbacks": float(sum(r.used != r.ranking for r in mine)),
                                    "cases": float(len(mine))}
    for key, _, _ in METRICS:
        if key == "violations":
            continue
        vals = [r.metrics[key] for r in mine if r.metrics.get(key) is not None]
        if key in ("jev_calls", "jev_input_tokens"):  # 요청당(랜덤은 seed 수만큼 요청)
            reqs = sum(max(1, len(r.case.seeds)) for r in mine)
            out[key] = sum(vals) / reqs if reqs else None
        else:
            out[key] = statistics.fmean(vals) if vals else None
    return out


def _fmt(v: float | None, key: str) -> str:
    if v is None:
        return "-"
    if key in ("latency_ms", "jev_input_tokens"):
        return f"{v:,.0f}"
    if key in ("violations", "jev_calls", "diversity", "cases", "fallbacks"):
        return f"{v:.1f}".rstrip("0").rstrip(".")
    return f"{v:.2f}"


def render(rows: Sequence[Row], rankings: Sequence[str], meta: Mapping[str, Any]) -> str:
    sums = {rk: summarize(rows, rk) for rk in rankings}
    lines = [
        "# 추천 v2 평가 결과",
        "",
        f"생성: `uv run python scripts/eval_v2.py` ({meta['date']}, 커밋 {meta['commit']}, 레시피 {meta['recipes']:,}개, "
        f"Jev 모델 {meta['model'] or '-'}). 기준: docs/plan.md 부록 G-13. 같은 평가 세트를 경로별로 돌린 결과다.",
        "",
        f"- 평가 세트: 기준 시나리오(bl-1) {meta['n_baseline']}개 · 테스트 페르소나 {meta['n_persona']}개 요청 · "
        f"요리 문장 {meta['n_query']}개(`data/eval/v2_queries.yaml`).",
        "- 안전 위반은 엔진 필터를 쓰지 않고 지식(closure·contains)으로 다시 판정한 수다. 0이 아니면 결함이다.",
        "- '사람 평가' 칸은 비워 두었다. 상위 5개를 보고 O(좋음)·△·X(나쁨)를 적으면 다음 평가의 정답으로 쓴다.",
        "",
        "## 요약(평균)",
        "",
        "| 지표 | 좋은 방향 | " + " | ".join(rankings) + " |",
        "|---|---|" + "---|" * len(rankings),
        "| 평가 요청 수 | - | " + " | ".join(_fmt(sums[rk]["cases"], "cases") for rk in rankings) + " |",
        "| Jev 실패로 규칙 대체 | 적게 | " + " | ".join(_fmt(sums[rk]["fallbacks"], "fallbacks") for rk in rankings) + " |",
    ]
    arrow = {"high": "높게", "low": "낮게", "-": "참고"}
    for key, label, d in METRICS:
        lines.append(f"| {label} | {arrow[d]} | " + " | ".join(_fmt(sums[rk][key], key) for rk in rankings) + " |")
    if any(r.violations for r in rows):
        lines += ["", "## 안전 위반 상세", ""]
        for r in rows:
            for v in r.violations:
                lines.append(f"- [{r.ranking}] {r.case.title}: {v}")
    for group in ("기준 시나리오", "테스트 페르소나", "요리 문장"):
        group_rows = [r for r in rows if r.case.group == group]
        if not group_rows:
            continue
        lines += ["", f"## {group}", "", "| 요청 | 경로 | 상위 5 | 요청 맞음 | 좋아함 적중 | 사람 평가 |", "|---|---|---|---|---|---|"]
        for r in group_rows:
            note = " ※규칙 대체" if r.used != r.ranking else ""
            top = " · ".join(r.titles) or "(결과 없음)"
            lines.append(f"| {r.case.title} | {r.ranking}{note} | {top} | {_fmt(r.metrics['request_fit'], 'x')} | "
                         f"{_fmt(r.metrics['like_hit'], 'x')} |  |")
    return "\n".join(lines) + "\n"


def to_json(rows: Sequence[Row], rankings: Sequence[str], meta: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "meta": dict(meta),
        "summary": {rk: summarize(rows, rk) for rk in rankings},
        "rows": [{"case": r.case.id, "group": r.case.group, "title": r.case.title, "ranking": r.ranking,
                  "used": r.used, "top5": r.titles, "metrics": r.metrics, "violations": r.violations,
                  "notes": r.notes} for r in rows],
    }
