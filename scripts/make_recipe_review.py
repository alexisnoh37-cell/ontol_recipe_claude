"""레시피 검수표(docs/review/recipes_review.md)를 시드와 컴파일된 지식으로부터 만든다.

    uv run python scripts/make_recipe_review.py

data/recipes/*.yaml이나 knowledge/를 고친 뒤 다시 실행한다. 검수표는 손으로 고치지 않는다(덮어씀).
"걸리는 알레르기 그룹"은 allergen_closure를 조회해 계산한다(선택 재료·고명·양념 포함, 엔진 필터와 같은 기준).
confidence: low 레시피를 맨 위에 모은다.
"""

from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kb import CompiledKnowledge, KnowledgeError, compile_paths  # noqa: E402
from kb.datacheck import RecipeSpec  # noqa: E402
from kb.recipes import RecipeSeedError, load_recipe_specs  # noqa: E402

OUT = ROOT / "docs" / "review" / "recipes_review.md"
COLUMNS = ["제목(id)", "종류", "난이도", "맛(매움/짠맛/단맛)", "주재료", "선택재료", "걸리는 알레르기 그룹", "confidence"]
ROLE_NAMES = {"main": "주", "sub": "부", "seasoning": "양념", "garnish": "고명"}


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def allergen_hits(ck: CompiledKnowledge, recipe: RecipeSpec) -> dict[str, tuple[str, list[str]]]:
    """기본 그룹 id → (가장 강한 certainty, 걸린 재료 id 목록)."""
    base = {g.id for g in ck.allergen_groups if g.kind == "base"}
    closure: dict[str, dict[str, str]] = defaultdict(dict)  # 재료 → {그룹: certainty}
    for row in ck.allergen_closure:
        if row.allergen_group_id in base:
            closure[row.ingredient_id][row.allergen_group_id] = row.certainty
    causes: dict[str, list[str]] = defaultdict(list)
    for line in recipe.ingredients:
        for group in closure.get(line.ingredient or "", {}):
            if line.ingredient not in causes[group]:
                causes[group].append(line.ingredient)
    # 원인 재료 중 하나라도 definite면 definite
    return {
        group: ("definite" if any(closure[c][group] == "definite" for c in ids) else "possible", ids)
        for group, ids in causes.items()
    }


def render(ck: CompiledKnowledge, recipes: list[RecipeSpec]) -> str:
    names = {i.id: i.name for i in ck.ingredients}
    group_names = {g.id: g.display_name for g in ck.allergen_groups}

    def allergy_cell(r: RecipeSpec) -> str:
        hits = allergen_hits(ck, r)
        parts = []
        for group, (certainty, causes) in sorted(hits.items(), key=lambda x: (x[1][0] != "definite", group_names[x[0]])):
            label = group_names[group] if certainty == "definite" else f"{group_names[group]}(가능)"
            parts.append(f"{label}: {', '.join(names[c] for c in causes)}")
        return "<br>".join(parts) if parts else "없음"

    def row(r: RecipeSpec) -> str:
        mains = ", ".join(names[i.ingredient] for i in r.ingredients if i.role == "main" and i.ingredient)
        optional = ", ".join(names[i.ingredient] for i in r.ingredients if i.optional and i.ingredient) or "-"
        taste = f"{r.taste.spicy}/{r.taste.salty}/{r.taste.sweet}" if r.taste else "-"
        conf = r.confidence + (f" ({r.note})" if r.note else "")
        cells = [f"{r.title} (`{r.id}`)", r.cuisine, str(r.difficulty), taste, mains, optional, allergy_cell(r), conf]
        return "| " + " | ".join(_cell(c) for c in cells) + " |"

    header = "| " + " | ".join(COLUMNS) + " |\n|" + "---|" * len(COLUMNS)
    low = [r for r in recipes if r.confidence == "low"]
    by_cuisine: dict[str, list[RecipeSpec]] = defaultdict(list)
    for r in recipes:
        if r.confidence != "low":
            by_cuisine[r.cuisine].append(r)
    counts = Counter(r.cuisine for r in recipes)
    kimchi_like = {"kimchi", "kkakdugi", "young_radish_kimchi"}

    lines = [
        "# 레시피 검수표",
        "",
        "> `scripts/make_recipe_review.py`가 `data/recipes/*.yaml`과 컴파일된 지식으로 생성한다. 손으로 고치지 않는다.",
        "> 레시피는 에이전트가 작성한 초안이다. 사람이 검수해 승인한 레시피만 `status: published`로 바꾼다.",
        "",
        f"레시피 {len(recipes)}개: " + ", ".join(f"{c} {n}" for c, n in sorted(counts.items(), key=lambda x: -x[1]))
        + " / 상태: " + ", ".join(f"{k} {v}" for k, v in sorted(Counter(r.status for r in recipes).items())),
        "",
        "## 보는 법",
        "",
        "- 맛은 0~5 강도(매움/짠맛/단맛). 신맛·감칠맛·고소한 맛은 아래 상세에 있다.",
        "- 난이도 1~3(1 초급). 주재료는 role이 main인 재료. 선택재료는 optional 재료(역할 무관).",
        "- 걸리는 알레르기 그룹: 기본 그룹만 표시하고 `그룹: 원인 재료` 형식. `(가능)`은 포함 가능(possible).",
        "  엔진은 possible도, 선택 재료·고명도 제외 대상으로 본다. 묶음 그룹(갑각류 등)은 기본 그룹의 합이다.",
        "- 조리기구는 기본 도구(냄비, 프라이팬)를 `required: false`로, 오븐처럼 없으면 못 만드는 것만 `required: true`로 두었다.",
        "",
        "## 확인 포인트",
        "",
        "- 김치류가 들어간 레시피: "
        + ", ".join(f"{r.title}({'새우 걸림' if 'shrimp' in allergen_hits(ck, r) else '새우 안 걸림'})"
                    for r in recipes if any(i.ingredient in kimchi_like for i in r.ingredients)),
        "- 매운맛 강도, 난이도, 주재료와 선택재료 구분이 상식에 맞는지.",
        "",
        f"## confidence: low ({len(low)})",
        "",
        header,
        *[row(r) for r in low],
        "",
    ]
    for cuisine in sorted(by_cuisine, key=lambda c: -counts[c]):
        items = by_cuisine[cuisine]
        lines += [f"## {cuisine} ({len(items)})", "", header, *[row(r) for r in items], ""]

    lines += ["## 부록: 레시피 상세", ""]
    for r in recipes:
        t = r.taste
        lines += [
            f"### {r.title} (`{r.id}`)",
            "",
            f"- {r.cuisine}, 난이도 {r.difficulty}, {r.cook_time_min}분, {r.servings}인분, confidence {r.confidence}"
            + (f", 메모: {r.note}" if r.note else ""),
            f"- 맛: 매움 {t.spicy}, 짠맛 {t.salty}, 단맛 {t.sweet}, 신맛 {t.sour}, 감칠맛 {t.umami}, 고소함 {t.savory}" if t else "- 맛: 없음",
            "- 조리기구: " + (", ".join(f"{e.name}({'필수' if e.required else '선택'})" for e in r.equipment) or "없음"),
            "- 재료: " + "; ".join(
                f"{ROLE_NAMES[i.role]}{'·선택' if i.optional else ''} {i.raw_text} → "
                + (f"`{i.ingredient}`" if i.ingredient else "**미매칭**")
                for i in r.ingredients
            ),
            "- 조리: " + " ".join(f"{n}) {s.text}" + (f" [{s.technique}]" if s.technique else "")
                                  for n, s in enumerate(r.steps, start=1)),
            "",
        ]
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    try:
        ck = compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")
        recipes = load_recipe_specs(ck, ROOT / "data" / "recipes", ROOT)
    except (KnowledgeError, RecipeSeedError) as exc:
        print(exc, file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(ck, recipes), encoding="utf-8")
    print(f"검수표 생성: {OUT.relative_to(ROOT).as_posix()} (레시피 {len(recipes)}개)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
