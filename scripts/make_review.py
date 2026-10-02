"""식재료 검수표(docs/review/ingredients_review.md)를 컴파일 결과로부터 만든다.

    uv run python scripts/make_review.py

knowledge/*.yaml을 고친 뒤 다시 실행한다. 검수표는 손으로 고치지 않는다(다음 생성 때 덮어씀).
confidence: low 항목을 맨 위에 모으고, 나머지는 카테고리별로 나눈다.
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

from kb import CompiledKnowledge, KnowledgeError, compile_paths  # noqa: E402

OUT = ROOT / "docs" / "review" / "ingredients_review.md"
COLUMNS = ["id", "이름", "상위 개념", "파생 원천", "걸리는 알레르기(상속 포함)", "메모"]


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def render(ck: CompiledKnowledge) -> str:
    names = {i.id: i.name for i in ck.ingredients}
    group_names = {g.id: g.display_name for g in ck.allergen_groups}
    base_groups = [g for g in ck.allergen_groups if g.kind == "base"]

    parents: dict[str, list[str]] = defaultdict(list)
    sources: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for r in ck.relations:
        if r.type == "is_a":
            parents[r.from_id].append(r.to_id)
        elif r.type == "derived_from":
            sources[r.from_id].append((r.to_id, r.certainty or "definite"))
    allergies: dict[str, list[tuple[str, str]]] = defaultdict(list)
    base_ids = {g.id for g in base_groups}
    for row in ck.allergen_closure:
        if row.allergen_group_id in base_ids:
            allergies[row.ingredient_id].append((row.allergen_group_id, row.certainty))

    def mark(name: str, certainty: str) -> str:
        return name if certainty == "definite" else f"{name}(가능)"

    def row(i) -> str:
        parent = ", ".join(names[p] for p in sorted(parents[i.id]))
        src = ", ".join(
            mark(names[s], c) for s, c in sorted(sources[i.id], key=lambda x: (x[1] != "definite", names[x[0]]))
        )
        alg = ", ".join(
            mark(group_names[g], c)
            for g, c in sorted(allergies[i.id], key=lambda x: (x[1] != "definite", group_names[x[0]]))
        )
        memo = []
        if i.kind == "concept":
            memo.append("[분류 노드]")
        if i.is_pantry_staple:
            memo.append("[기본 양념]")
        if i.note:
            memo.append(i.note)
        cells = [f"`{i.id}`", i.name, parent, src, alg or "-", " ".join(memo)]
        return "| " + " | ".join(_cell(c) for c in cells) + " |"

    header = "| " + " | ".join(COLUMNS) + " |\n|" + "---|" * len(COLUMNS)
    low = [i for i in ck.ingredients if i.confidence == "low"]
    rest = [i for i in ck.ingredients if i.confidence != "low"]
    by_category: dict[str, list] = defaultdict(list)
    for i in rest:
        by_category[i.category or "(분류 없음)"].append(i)
    category_order = list(ck.vocab["categories"]) + ["(분류 없음)"]

    lines = [
        "# 식재료 검수표",
        "",
        "> `scripts/make_review.py`가 컴파일 결과로부터 생성합니다. 이 파일을 직접 고치지 말고 `knowledge/`를 고친 뒤 다시 생성하세요.",
        "",
        f"- 재료 {len(ck.ingredients)}개(분류 노드 {len(ck.concept_ids)}개), 그중 `confidence: low` {len(low)}개",
        f"- 알레르기 그룹: 기본 {len(base_groups)}개(법정 {sum(g.official for g in base_groups)}개, 자체 "
        f"{sum(not g.official for g in base_groups)}개), 묶음 {len(ck.allergen_groups) - len(base_groups)}개",
        f"- source_hash `{ck.source_hash[:12]}`",
        "",
        "## 읽는 법",
        "",
        "- **상위 개념**: is_a 부모. 부모의 알레르기를 그대로 물려받습니다.",
        "- **파생 원천**: derived_from. `(가능)`은 제품에 따라 들어갈 수 있다는 뜻(possible)입니다.",
        "- **걸리는 알레르기**: 상속까지 계산한 기본 그룹 목록(묶음 그룹은 생략). `(가능)`도 알레르기 판정에서는 제외 대상입니다.",
        "- 확인할 것: 원천이 빠졌거나 틀린 가공품, `(가능)`이어야 하는데 확정이거나 그 반대인 것, 별칭으로 묶으면 안 되는 것.",
        "",
        "## 컴파일 경고",
        "",
    ]
    lines += [f"- `{w.code}` {w.where}: {w.message}" for w in ck.warnings] or ["- 없음"]
    lines += ["", f"## 1. 확신 낮음 (`confidence: low`) — {len(low)}개", "", header]
    lines += [row(i) for i in low]
    lines += ["", f"## 2. 나머지 — {len(rest)}개 (카테고리별)", ""]
    for category in category_order:
        items = by_category.get(category)
        if not items:
            continue
        lines += [f"### {category} ({len(items)})", "", header]
        lines += [row(i) for i in items]
        lines.append("")
    lines += ["## 부록: 알레르기 그룹", "", "| id | 이름 | 종류 | 법정 | 재료 수(상속 포함) |", "|---|---|---|---|---|"]
    counts = defaultdict(int)
    for r in ck.allergen_closure:
        counts[r.allergen_group_id] += 1
    for g in ck.allergen_groups:
        kind = "기본" if g.kind == "base" else "묶음"
        lines.append(f"| `{g.id}` | {g.display_name} | {kind} | {'예' if g.official else '아니오'} | {counts[g.id]} |")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    try:
        ck = compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")
    except KnowledgeError as exc:
        print(exc, file=sys.stderr)
        return 1
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(ck), encoding="utf-8")
    print(f"검수표 생성: {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
