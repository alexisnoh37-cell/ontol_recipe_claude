"""골든셋 평가 (docs/plan.md 7-3): 페르소나를 엔진에 돌려 상위 3개 적중률을 잰다.

expected_top3는 사람이 채운다. 비어 있는 페르소나는 적중률 계산에서 빼고 "미기입"으로 센다.
페르소나별 적중률 = (기대 레시피 중 상위 3개에 든 수) ÷ min(3, 기대 레시피 수). 전체는 기입된 페르소나의 평균.

엔진은 실제 knowledge/, config/, data/recipes/(기본 설정: published만)로 만든다.
kb → 엔진 변환은 storage.engine_source(API·벤치와 같은 함수)를 쓴다.
페르소나 로딩(Persona, load_personas)은 viz-2에서 storage.personas로 옮기고 여기서 다시 내보낸다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.model import RecommendItem, RecommendResult
from engine.recommend import Recommender
from storage.engine_source import load_files
from storage.personas import PERSONAS, Persona, load_personas  # noqa: F401 - 기존 import 경로 유지

ROOT = Path(__file__).resolve().parents[2]
TOP_K = 3


def build_engine() -> tuple[Recommender, dict[str, str]]:
    """실제 데이터로 만든 엔진과 재료 id → 이름."""
    data = load_files(ROOT)
    return data.recommender(serve_draft_recipes=False), {i.id: i.name for i in data.knowledge.ingredients}


def hit_rate(expected: tuple[str, ...], items: tuple[RecommendItem, ...], k: int = TOP_K) -> float | None:
    """기대 레시피가 없으면 None(미기입)."""
    if not expected:
        return None
    top = {i.recipe_id for i in items[:k]}
    return len(top & set(expected)) / min(k, len(expected))


@dataclass(frozen=True)
class PersonaResult:
    persona: Persona
    result: RecommendResult
    hit_rate: float | None


def evaluate(recommender: Recommender, personas: list[Persona]) -> list[PersonaResult]:
    return [PersonaResult(p, r := recommender.recommend(p.user, p.request), hit_rate(p.expected_top3, r.items))
            for p in personas]


def overall(results: list[PersonaResult]) -> float | None:
    rates = [r.hit_rate for r in results if r.hit_rate is not None]
    return sum(rates) / len(rates) if rates else None


# --- 결과 스냅샷(수정 전후 비교용) -------------------------------------------------------------------


def snapshot(results: list[PersonaResult], top_n: int = 5) -> dict[str, Any]:
    """비교용으로 저장하는 평가 결과(JSON 직렬화 가능)."""
    return {
        "overall": overall(results),
        "personas": {
            r.persona.id: {
                "hit_rate": r.hit_rate,
                "top": [{"recipe_id": i.recipe_id, "title": i.title, "score": i.score, "breakdown": dict(i.breakdown),
                         "missing": list(i.missing)} for i in r.result.items[:top_n]],
            }
            for r in results
        },
    }


def save_snapshot(results: list[PersonaResult], path: Path, label: str) -> None:
    path.write_text(json.dumps({"label": label, **snapshot(results)}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def load_snapshot(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# --- 초안 표(docs/review/golden_draft.md) ------------------------------------------------------------


def _profile(p: Persona, names: dict[str, str]) -> list[str]:
    raw = p.raw
    lines = [f"- 실력 {raw['skill_level']}, 보유 재료: " + ", ".join(names.get(i, i) for i in raw["pantry"])]
    if raw.get("allergen_groups"):
        lines.append("- 알레르기: " + ", ".join(raw["allergen_groups"]))
    for x in raw.get("preferences", []):
        target = names.get(x["target"], x["target"]) if x["type"] == "ingredient" else x["target"]
        sign = "선호" if x["polarity"] > 0 else "불선호"
        lines.append(f"- {sign}: {target} (강도 {x.get('strength', 1.0)}{', 절대' if x.get('hard') else ''})")
    for t in raw.get("tastes", []):
        parts = []
        if t.get("preferred_level") is not None:
            parts.append(f"선호 {t['preferred_level']}")
        if t.get("max_level") is not None:
            parts.append(f"한도 {t['max_level']}")
        lines.append(f"- 맛 {t['dimension']}: " + ", ".join(parts))
    req = raw.get("request") or {}
    lines.append(f"- 조리기구: {', '.join(raw.get('equipment', [])) or '없음'} / 희망 시간: "
                 + (f"{req['max_time_min']}분" + (" (절대)" if req.get("time_is_hard") else "") if req.get("max_time_min") else "없음"))
    return lines


def _rate(value: float | None) -> str:
    return "미기입" if value is None else f"{value:.2f}"


def _top_cell(top: list[dict[str, Any]], expected: tuple[str, ...]) -> str:
    """상위 목록. 기대 레시피는 굵게, 상위 3개와 4~5위 사이는 구분선."""
    cells = []
    for n, i in enumerate(top, start=1):
        title = f"**{i['title']}**" if i["recipe_id"] in expected else i["title"]
        cells.append(f"{n}. {title} ({i['score']:.3f})")
    return "<br>".join(cells) or "(결과 없음)"


def render_draft(results: list[PersonaResult], names: dict[str, str], top_n: int = 5,
                 baseline: dict[str, Any] | None = None) -> str:
    now = snapshot(results, top_n)
    before = baseline or {}
    lines = [
        "# 골든셋 평가",
        "",
        "> `uv run python scripts/eval_golden.py --draft`로 생성한다. 페르소나 원본은 `tests/golden/personas.yaml`.",
        "> \"상위 3개 안에 나와야 할 레시피\"(expected_top3)는 사람이 정한다. 표에서 기대 레시피는 **굵게** 표시한다.",
        "> 점수: S = 0.30·I + 0.20·K + 0.15·T + 0.15·P + 0.10·D + 0.10·M (config/weights.yaml). 다양성 보정 적용 후 순위.",
        "",
    ]
    if before:
        lines += [
            f"## 적중률: 수정 전 → 수정 후",
            "",
            f"- 수정 전: {before.get('label', '')}",
            f"- 전체 상위 3개 적중률: **{_rate(before.get('overall'))} → {_rate(now['overall'])}**",
            "",
            "| 페르소나 | 기대 레시피 | 적중률 전 | 적중률 후 | 수정 전 상위 5개 | 수정 후 상위 5개 |",
            "|---|---|---|---|---|---|",
        ]
        for r in results:
            p = r.persona
            old = before["personas"].get(p.id, {"hit_rate": None, "top": []})
            lines.append(f"| {p.name} (`{p.id}`) | {', '.join(p.expected_top3) or ' '} | {_rate(old['hit_rate'])} | "
                         f"{_rate(r.hit_rate)} | {_top_cell(old['top'], p.expected_top3)} | "
                         f"{_top_cell(now['personas'][p.id]['top'], p.expected_top3)} |")
    else:
        lines += [
            f"전체 상위 3개 적중률: **{_rate(now['overall'])}**",
            "",
            "| 페르소나 | 기대 레시피 | 적중률 | 현재 엔진 상위 5개 |",
            "|---|---|---|---|",
        ]
        for r in results:
            p = r.persona
            lines.append(f"| {p.name} (`{p.id}`) | {', '.join(p.expected_top3) or ' '} | {_rate(r.hit_rate)} | "
                         f"{_top_cell(now['personas'][p.id]['top'], p.expected_top3)} |")
    lines += ["", "## 페르소나별 상세(현재 엔진)", ""]
    for r in results:
        p = r.persona
        lines += [f"### {p.name} (`{p.id}`)", "", p.description, "", *_profile(p, names), "",
                  "상위 3개 안에 나와야 할 레시피(사람 기입): " + (", ".join(p.expected_top3) if p.expected_top3 else "______")
                  + f" · 적중률 {_rate(r.hit_rate)}", "",
                  "| 순위 | 레시피 | 점수 | I | K | T | P | D | M | 부족 재료 |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for n, i in enumerate(r.result.items[:top_n], start=1):
            b = i.breakdown
            missing = ", ".join(names.get(m, m) for m in i.missing) or "-"
            title = f"**{i.title}**" if i.recipe_id in p.expected_top3 else i.title
            lines.append(f"| {n} | {title} (`{i.recipe_id}`) | {i.score:.3f} | "
                         + " | ".join(f"{b[c]:.2f}" for c in "IKTPDM") + f" | {missing} |")
        ranks = {i.recipe_id: n for n, i in enumerate(r.result.items, start=1)}
        outside = [e for e in p.expected_top3 if e not in [i.recipe_id for i in r.result.items[:3]]]
        if outside:
            lines += ["", "상위 3개 밖 기대 레시피: " + ", ".join(
                f"`{e}`({ranks[e]}위)" if e in ranks else f"`{e}`(상위 10개 밖 또는 후보·필터 제외)" for e in outside)]
        summary = ", ".join(f"{k} {v}" for k, v in sorted(r.result.exclusion_summary.items())) or "없음"
        lines += ["", f"후보 {len(r.result.items)}개 표시(최대 10) · 제외된 레시피(사유별): {summary}", ""]
    return "\n".join(lines).rstrip() + "\n"
