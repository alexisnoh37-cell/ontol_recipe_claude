"""draft 재료 검수 화면(docs/review/ingredient_review.html)을 만든다. 판단은 사람이 화면에서 한다.

    uv run python scripts/make_ingredient_review_html.py

knowledge의 status: draft 재료마다 별칭, is_a·derived_from 관계, 상속까지 포함한 알레르기와 경로(컴파일 결과),
쓰이는 레시피(엔진 시드·식품안전나라)를 모아 한 파일짜리 HTML로 만든다(인터넷 없이 열림).
미리 채울 판단은 docs/review/ingredient_prefill.yaml(규칙은 그 파일 머리말). 화면에서 O·X·보류와 메모를 고친 뒤
'결과 내보내기'로 받은 JSON을 다음 단계에서 knowledge에 반영한다. knowledge/와 data/는 바꾸지 않는다.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kb import compile_paths  # noqa: E402
from kb.unmapped_review import PROPOSAL, load_proposal  # noqa: E402

TEMPLATE = ROOT / "scripts" / "ingredient_review_template.html"
PREFILL = ROOT / "docs" / "review" / "ingredient_prefill.yaml"
OUT = ROOT / "docs" / "review" / "ingredient_review.html"
_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def recipe_usage(folder: Path) -> dict[str, list[tuple[str, str]]]:
    """재료 id → [(레시피 id, 제목)] (파일 이름 순)."""
    out: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for path in sorted(folder.glob("*.yaml")):
        d = yaml.load(path.read_text(encoding="utf-8"), Loader=_LOADER)
        for i in dict.fromkeys(line.get("ingredient") for line in d["ingredients"]):
            if i:
                out[i].append((d["id"], d["title"]))
    return out


def build() -> tuple[str, list[dict]]:
    """(HTML, 행 데이터)."""
    ck = compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")
    names = {i.id: i.name for i in ck.ingredients}
    groups = {g.id: g.display_name for g in ck.allergen_groups if g.kind == "base"}
    aliases: dict[str, list[str]] = defaultdict(list)
    for a in ck.aliases:
        if not a.is_primary:
            aliases[a.ingredient_id].append(a.alias + (f" ({a.form})" if a.form else ""))
    rel: dict[str, dict[str, list[str]]] = defaultdict(lambda: {"is_a": [], "derived_from": []})
    for r in ck.relations:
        if r.type == "is_a":
            rel[r.from_id]["is_a"].append(names[r.to_id])
        elif r.type == "derived_from":
            rel[r.from_id]["derived_from"].append(names[r.to_id] + ("(가능)" if r.certainty == "possible" else ""))
    closure: dict[str, list[dict]] = defaultdict(list)
    for r in sorted(ck.allergen_closure, key=lambda r: r.allergen_group_id):
        if r.allergen_group_id in groups:
            closure[r.ingredient_id].append({
                "group": groups[r.allergen_group_id], "possible": r.certainty == "possible",
                "via": " → ".join(names[i] for i in r.via),
            })
    engine = recipe_usage(ROOT / "data" / "recipes")
    fs = recipe_usage(ROOT / "data" / "recipes_foodsafety")
    um_kind = {e.new["id"]: e.kind for e in load_proposal(ROOT / PROPOSAL) if e.new}
    display = yaml.safe_load((ROOT / "config" / "display.yaml").read_text(encoding="utf-8"))
    commercial = set((display.get("commercial_product_notice") or {}).get("ingredients") or ())
    overrides = yaml.safe_load(PREFILL.read_text(encoding="utf-8"))["overrides"]

    drafts = [i for i in ck.ingredients if i.status == "draft"]
    unknown = set(overrides) - {i.id for i in drafts}
    if unknown:
        raise SystemExit(f"{PREFILL.name}에 draft가 아닌 재료가 있습니다: {sorted(unknown)}")
    drafts.sort(key=lambda i: (-len(engine[i.id]), -len(fs[i.id]), i.id))
    data = []
    for n, i in enumerate(drafts, 1):
        kind = um_kind.get(i.id)
        origin = {"E": "시판 제품", "B": "새 재료"}.get(kind, "이전 draft")
        if i.id in overrides:
            o = overrides[i.id]
            prefill = {"decision": o["decision"], "memo": o.get("memo") or "", "color": o["color"]}
            claude = o.get("claude") or ""
        elif kind == "E" or i.id in commercial:
            prefill = {"decision": "보류", "memo": "포장 알레르기 표시를 확인한 뒤 확인한 성분으로 고쳐 승인", "color": "yellow"}
            claude = "제품마다 성분이 달라 알레르기 목록이 추정이다. 확인 전에는 draft로 둔다(draft여도 추천 엔진은 그대로 쓴다)."
        elif i.confidence == "low" or closure[i.id]:
            prefill = {"decision": "O", "memo": "", "color": "blue"}
            claude = "확신이 낮거나 알레르기가 있는 재료. 알레르기와 메모를 한번 읽어 보고 승인."
        else:
            prefill = {"decision": "O", "memo": "", "color": "white"}
            claude = "알레르기 없는 단순 재료(확신 높음)."
        data.append({
            "n": n, "id": i.id, "name": i.name, "origin": origin, "category": i.category or "",
            "conf": i.confidence, "processed": i.is_processed, "note": i.note or "",
            "aliases": aliases[i.id], "is_a": rel[i.id]["is_a"], "derived_from": rel[i.id]["derived_from"],
            "allergens": closure[i.id], "commercial": i.id in commercial,
            "engine": len(engine[i.id]), "engineTitles": [t for _, t in engine[i.id][:8]],
            "fs": len(fs[i.id]), "fsTitles": [t for _, t in fs[i.id][:5]],
            "claude": claude, "prefill": prefill,
        })
    payload = {"title": "draft 재료 검수", "rows": data, "source": "knowledge/ingredients (status: draft)"}
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", blob), data


def main() -> int:
    html, data = build()
    OUT.write_text(html, encoding="utf-8")
    colors = {c: sum(1 for d in data if d["prefill"]["color"] == c) for c in ("red", "yellow", "blue", "white")}
    print(f"검수 화면: {OUT.relative_to(ROOT).as_posix()} (재료 {len(data)}개, 색 {colors})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
