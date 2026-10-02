"""골든셋 평가 (docs/plan.md 7-3): 페르소나를 엔진에 돌려 상위 3개 적중률을 잰다.

expected_top3는 사람이 채운다. 비어 있는 페르소나는 적중률 계산에서 빼고 "미기입"으로 센다.
페르소나별 적중률 = (기대 레시피 중 상위 3개에 든 수) ÷ min(3, 기대 레시피 수). 전체는 기입된 페르소나의 평균.

엔진은 실제 knowledge/, config/, data/recipes/(기본 설정: published만)로 만든다.
kb → 엔진 변환은 tests/support/engine_fixtures를 쓴다(1-5에서 위치를 옮기면 함께 바꾼다).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from engine.config import EngineConfig
from engine.model import (
    Preference,
    RecommendItem,
    RecommendRequest,
    RecommendResult,
    TastePreference,
    UserContext,
)
from engine.recommend import Recommender
from kb import compile_paths
from kb.recipes import load_recipe_specs
from tests.support.engine_fixtures import build_recommender, recipe_from_spec

ROOT = Path(__file__).resolve().parents[2]
PERSONAS = Path(__file__).resolve().parent / "personas.yaml"
TOP_K = 3


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    description: str
    user: UserContext
    request: RecommendRequest
    expected_top3: tuple[str, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict, compare=False)


def load_personas(path: Path = PERSONAS) -> list[Persona]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    out = []
    for p in data["personas"]:
        prefs = tuple(
            Preference(x["type"], x["target"], x["polarity"], float(x.get("strength", 1.0)), bool(x.get("hard", False)))
            for x in p.get("preferences", [])
        )
        tastes = tuple(
            TastePreference(x["dimension"], x.get("preferred_level"), x.get("max_level")) for x in p.get("tastes", [])
        )
        user = UserContext(
            skill_level=p["skill_level"],
            allergen_groups=frozenset(p.get("allergen_groups", [])),
            preferences=prefs,
            tastes=tastes,
            pantry=frozenset(p["pantry"]),
            equipment=frozenset(p.get("equipment", [])),
        )
        req = p.get("request") or {}
        request = RecommendRequest(max_time_min=req.get("max_time_min"), time_is_hard=bool(req.get("time_is_hard", False)),
                                   limit=10)
        out.append(Persona(p["id"], p["name"], p["description"], user, request,
                           tuple(p.get("expected_top3") or ()), raw=p))
    return out


def build_engine() -> tuple[Recommender, dict[str, str]]:
    """실제 데이터로 만든 엔진과 재료 id → 이름."""
    ck = compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")
    specs = load_recipe_specs(ck, ROOT / "data" / "recipes", ROOT)
    return build_recommender(ck, [recipe_from_spec(s) for s in specs]), {i.id: i.name for i in ck.ingredients}


def without_diversity(recommender: Recommender) -> Recommender:
    """비교용: 다양성 한도를 사실상 끈 같은 엔진(1-4에서 다양성 한도 결정을 돕기 위한 참고 자료)."""
    weights = copy.deepcopy(dict(recommender.config.weights))
    weights["diversity"] = {**weights["diversity"], "max_same_cuisine": 10**6, "max_same_main_ingredient": 10**6}
    return Recommender(recommender.knowledge, recommender.recipes,
                       EngineConfig(weights=weights, serve_draft_recipes=recommender.config.serve_draft_recipes))


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


def render_draft(results: list[PersonaResult], names: dict[str, str], top_n: int = 5,
                 no_diversity: list[PersonaResult] | None = None) -> str:
    lines = [
        "# 골든셋 초안",
        "",
        "> `uv run python scripts/eval_golden.py --draft`로 생성한다. 페르소나 원본은 `tests/golden/personas.yaml`.",
        "> **\"상위 3개 안에 나와야 할 레시피\"는 사람이 채운다**(personas.yaml의 `expected_top3`). 아래 엔진 결과는 참고용이다.",
        "> 점수: S = 0.30·I + 0.20·K + 0.15·T + 0.15·P + 0.10·D + 0.10·M (config/weights.yaml). 다양성 보정 적용 후 순위.",
        "",
        "| 페르소나 | 상위 3개 안에 나와야 할 레시피(사람 기입) | 현재 엔진 상위 5개 | 참고: 다양성 보정 없을 때 상위 5개 |",
        "|---|---|---|---|",
    ]

    def top_cell(result: RecommendResult) -> str:
        return "<br>".join(f"{n}. {i.title} ({i.score:.3f})" for n, i in enumerate(result.items[:top_n], start=1)) or "(결과 없음)"

    plain = {r.persona.id: r.result for r in no_diversity or []}
    for r in results:
        p = r.persona
        expected = ", ".join(p.expected_top3) if p.expected_top3 else " "
        alt = plain.get(p.id)
        if alt is None:
            alt_cell = "-"
        elif [i.recipe_id for i in alt.items[:top_n]] == [i.recipe_id for i in r.result.items[:top_n]]:
            alt_cell = "(같음)"
        else:
            alt_cell = top_cell(alt)
        lines.append(f"| {p.name} (`{p.id}`) | {expected} | {top_cell(r.result)} | {alt_cell} |")
    lines += ["", "다양성 보정: 상위 10개 안에 같은 음식 종류·같은 주재료가 3개를 넘지 않게 뒤로 미룬다(config/weights.yaml diversity).",
              "한도 조정 여부는 이 골든셋 결과를 보고 사람이 정한다."]
    lines += ["", "## 페르소나별 상세", ""]
    for r in results:
        p = r.persona
        lines += [f"### {p.name} (`{p.id}`)", "", p.description, "", *_profile(p, names), "",
                  "상위 3개 안에 나와야 할 레시피(사람 기입): " + (", ".join(p.expected_top3) if p.expected_top3 else "______"), "",
                  "| 순위 | 레시피 | 점수 | I | K | T | P | D | M | 부족 재료 |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for n, i in enumerate(r.result.items[:top_n], start=1):
            b = i.breakdown
            missing = ", ".join(names.get(m, m) for m in i.missing) or "-"
            lines.append(f"| {n} | {i.title} (`{i.recipe_id}`) | {i.score:.3f} | "
                         + " | ".join(f"{b[c]:.2f}" for c in "IKTPDM") + f" | {missing} |")
        summary = ", ".join(f"{k} {v}" for k, v in sorted(r.result.exclusion_summary.items())) or "없음"
        lines += ["", f"후보 {len(r.result.items)}개 표시(최대 10) · 제외된 레시피(사유별): {summary}", ""]
    return "\n".join(lines).rstrip() + "\n"
