"""미매칭 4차 정리(um-5)의 '꼭 확인' 항목 검수 화면(docs/review/unmapped_round4_review.html)을 만든다.

    uv run python scripts/make_unmapped_round4_html.py

docs/review/unmapped_round4.yaml에서 decision이 비어 있는 항목만 보여 준다. 새 재료(E)는 build/um5_candidate/에
지식 사본을 만들어 넣었을 때의 알레르기(상속 포함)를, 이름 보정(D)은 연결 대상 재료의 알레르기를 보여 준다.
knowledge/와 data/는 바꾸지 않는다. 화면은 재료 검수 화면 템플릿(scripts/ingredient_review_template.html)을 같이 쓴다.
"""

from __future__ import annotations

import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kb import compile_paths  # noqa: E402
from kb.text import normalize_term  # noqa: E402
from kb.unmapped_review import engine_unmapped, foodsafety_unmapped, load_proposal  # noqa: E402

ROUND = ROOT / "docs" / "review" / "unmapped_round4.yaml"
TEMPLATE = ROOT / "scripts" / "ingredient_review_template.html"
OUT = ROOT / "docs" / "review" / "unmapped_round4_review.html"
CANDIDATE = ROOT / "build" / "um5_candidate"
_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

RED = {"edible_flower", "."}  # 지난 결정을 뒤집는 판단
TEXT = [
    ("<title>재료 검수</title>", "<title>미매칭 4차 확인</title>"),
    ("<h1>draft 재료 검수</h1>", "<h1>미매칭 4차 정리 · 꼭 확인할 항목</h1>"),
    ("미매칭 보강(um-2)으로 추가한 재료와 이전부터 검수 대기 중인 재료입니다.",
     "남은 미매칭 53줄을 조리 단계·원문과 함께 다시 봤습니다. 모두 지난 검수에서 보류·반영 안 함으로 정한 표기라, 바꾸려면 확인이 필요합니다."),
    ("<b>O</b> 검수 완료(reviewed)로 바꿈(메모가 있으면 고친 뒤) · <b>X</b> 이 재료를 지움(그 표기는 다시 미매칭이 되어 알레르기 사용자에게 제외) · <b>보류</b> draft 그대로 둠.",
     "<b>O</b> 제안대로 연결·추가(메모가 있으면 고친 뒤) · <b>X</b> 지금처럼 미매칭 유지(알레르기 사용자에게 제외) · <b>보류</b> 이번에는 반영하지 않음."),
    ('<option value="시판 제품">시판 제품</option><option value="새 재료">새 재료</option><option value="이전 draft">이전 draft</option>',
     '<option value="근거 있음">근거 있음</option><option value="시판·추정">시판·추정</option><option value="지난 결정 뒤집기">지난 결정 뒤집기</option>'),
    ('const FORMAT = "ingredient-decisions/1";', 'const FORMAT = "unmapped-round4-decisions/1";'),
    ('red: ["꼭 봐야 함", "판단이 필요한 쟁점이 있는 재료"]', 'red: ["꼭 봐야 함", "지난 결정을 뒤집는 판단"]'),
    ('yellow: ["확인 후 결정", "포장 표시 확인이 필요해 보류로 둔 시판 제품"]', 'yellow: ["확인 후 결정", "시판·가정식 제품 성분을 넓게 추정"]'),
    ('blue: ["내용 확인", "확신이 낮거나 알레르기가 있어 한번 읽어 보면 좋은 재료"]', 'blue: ["근거 확인", "조리 단계·원문에 근거가 있는 연결"]'),
    ('const KEY = "ingredient-review/"', 'const KEY = "unmapped-round4/"'),
    ('a.download = "ingredient_decisions.json";', 'a.download = "unmapped_round4_decisions.json";'),
    ('toast("ingredient_decisions.json을', 'toast("unmapped_round4_decisions.json을'),
]


def _flow(v) -> str:
    return yaml.safe_dump(v, allow_unicode=True, default_flow_style=True, width=10**6).strip().removesuffix("...").strip()


def candidate_knowledge(new_entries) -> Path:
    if CANDIDATE.exists():
        shutil.rmtree(CANDIDATE)
    shutil.copytree(ROOT / "knowledge", CANDIDATE / "knowledge")
    lines = ["", "# --- um-5 꼭 확인(미리보기용 사본) ---"]
    for e in new_entries:
        n = e.new
        lines += [f"- id: {n['id']}", f"  name: {_flow(n['name'])}"]
        aliases = [t for t in e.texts if normalize_term(t) != normalize_term(n["name"])]
        if aliases:
            lines.append(f"  aliases: {_flow(aliases)}")
        for k in ("derived_from", "allergens"):
            if n.get(k):
                lines.append(f"  {k}: {_flow(n[k])}")
        if n.get("is_processed"):
            lines.append("  is_processed: true")
        lines += [f"  category: {n['category']}", "  status: draft"]
    path = CANDIDATE / "knowledge" / "ingredients" / "kimchi_processed.yaml"
    path.write_text(path.read_text(encoding="utf-8").rstrip("\n") + "\n".join(lines) + "\n", encoding="utf-8")
    return CANDIDATE / "knowledge"


def usage(ck) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, set[str]]]:
    """표기(정규화) → 식품안전나라 레시피 제목, 엔진 레시피 제목. 레시피 id → 미매칭 표기 집합(변환기와 같은 기준)."""
    titles = {}
    for folder in (ROOT / "data" / "recipes_foodsafety", ROOT / "data" / "recipes"):
        for path in folder.glob("*.yaml"):
            d = yaml.load(path.read_text(encoding="utf-8"), Loader=_LOADER)
            if isinstance(d, dict) and "id" in d:
                titles[d["id"]] = d.get("title", d["id"])
    fs: dict[str, list[str]] = defaultdict(list)
    eng: dict[str, list[str]] = defaultdict(list)
    left: dict[str, set[str]] = {}
    for source, out in ((foodsafety_unmapped(ROOT), fs), (engine_unmapped(ROOT, ck), eng)):
        for rid, terms in source.by_recipe.items():
            left[rid] = set(terms)
            for t in terms:
                out[t].append(titles.get(rid, rid))
    return fs, eng, left


def build() -> tuple[str, list[dict]]:
    pending = [e for e in load_proposal(ROUND) if e.decision is None]
    ck = compile_paths(candidate_knowledge([e for e in pending if e.new]), ROOT / "config" / "pantry_staples.yaml")
    names = {i.id: i.name for i in ck.ingredients}
    groups = {g.id: g.display_name for g in ck.allergen_groups if g.kind == "base"}
    closure: dict[str, list[dict]] = defaultdict(list)
    for r in sorted(ck.allergen_closure, key=lambda r: r.allergen_group_id):
        if r.allergen_group_id in groups:
            closure[r.ingredient_id].append({"group": groups[r.allergen_group_id], "possible": r.certainty == "possible",
                                             "via": " → ".join(names[i] for i in r.via)})
    fs, eng, left = usage(compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml"))

    rows = []
    for e in pending:
        keys = {normalize_term(t) for t in e.texts}
        fs_titles = sorted({t for k in keys for t in fs.get(k, [])})
        eng_titles = sorted({t for k in keys for t in eng.get(k, [])})
        # 이 항목만 승인되면 미매칭이 없어지는 레시피
        unlock = sum(1 for miss in left.values() if miss and miss <= keys)
        if e.new:
            ids, rid, name = [e.new["id"]], e.new["id"], e.new["name"]
            derived = [names.get(x["id"] if isinstance(x, dict) else x, "?") + ("(가능)" if isinstance(x, dict) and x.get("certainty") == "possible" else "")
                       for x in e.new.get("derived_from") or []]
            category = e.new["category"]
        else:
            ids = [p["id"] for p in e.split] if e.split else ([e.target] if e.target else [])
            rid = e.key
            target = ("뺌(재료 아님)" if e.drop else " + ".join(names[i] for i in ids))
            name = f"'{e.key}' → {target}"
            derived, category = [], "이름 보정(연결)"
        allergens, seen = [], set()
        for i in ids:
            for a in closure[i]:
                if a["group"] not in seen:
                    seen.add(a["group"])
                    allergens.append(a)
        color = "red" if (rid in RED) else ("yellow" if e.kind == "E" or e.target in ("instant_noodle_product", "stock_unspecified") else "blue")
        origin = {"red": "지난 결정 뒤집기", "yellow": "시판·추정", "blue": "근거 있음"}[color]
        claude = (e.note or "") + f" 승인하면 미매칭이 모두 풀리는 레시피 {unlock}개."
        rows.append({
            "n": 0, "id": rid, "name": name, "origin": origin, "category": category,
            "conf": (e.new or {}).get("confidence") or ("low" if color != "blue" else "high"),
            "processed": bool((e.new or {}).get("is_processed")), "note": e.note or "",
            "aliases": e.texts, "is_a": [], "derived_from": derived, "allergens": allergens,
            "commercial": color == "yellow", "engine": len(eng_titles), "engineTitles": eng_titles[:8],
            "fs": len(fs_titles), "fsTitles": fs_titles[:5], "claude": claude,
            "prefill": {"decision": "O", "memo": "", "color": color},
        })
    order = {"red": 0, "yellow": 1, "blue": 2}
    rows.sort(key=lambda r: order[r["prefill"]["color"]])
    for n, r in enumerate(rows, 1):
        r["n"] = n
    payload = {"title": "미매칭 4차 확인", "rows": rows, "source": "docs/review/unmapped_round4.yaml (decision 없음 = 꼭 확인)"}
    html = TEMPLATE.read_text(encoding="utf-8")
    for old, new in TEXT:
        if old not in html:
            raise SystemExit(f"템플릿에서 문구를 찾지 못했습니다: {old[:40]}")
        html = html.replace(old, new)
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return html.replace("/*__DATA__*/null", blob), rows


def main() -> int:
    html, rows = build()
    OUT.write_text(html, encoding="utf-8")
    colors = {c: sum(1 for r in rows if r["prefill"]["color"] == c) for c in ("red", "yellow", "blue")}
    print(f"검수 화면: {OUT.relative_to(ROOT).as_posix()} (꼭 확인 {len(rows)}개, 색 {colors})")
    for r in rows:
        print(f"  {r['prefill']['color']:6} {r['name']} | 식안 {r['fs']} 엔진 {r['engine']} | {r['claude'][-22:]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
