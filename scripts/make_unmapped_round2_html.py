"""미매칭 2차 보강(um-3)의 '꼭 확인' 항목 검수 화면(docs/review/unmapped_round2_review.html)을 만든다.

    uv run python scripts/make_unmapped_round2_html.py

docs/review/unmapped_round2.yaml에서 decision이 비어 있는 E 항목(시판 제품·분류가 불확실한 재료)만 보여 준다.
일괄 승인분(decision O)은 사람 결정에 따라 이미 반영했으므로 화면에 없다.
제안 재료를 넣었을 때의 알레르기(상속 포함)는 build/um3_candidate/에 지식 사본을 만들어 컴파일한 결과다
(knowledge/와 data/는 바꾸지 않는다). 화면은 재료 검수 화면(scripts/ingredient_review_template.html)을 같이 쓴다.
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
from kb.foodsafety import ingredient_name  # noqa: E402
from kb.text import normalize_term  # noqa: E402
from kb.unmapped_review import load_proposal  # noqa: E402

ROUND2 = ROOT / "docs" / "review" / "unmapped_round2.yaml"
TEMPLATE = ROOT / "scripts" / "ingredient_review_template.html"
OUT = ROOT / "docs" / "review" / "unmapped_round2_review.html"
CANDIDATE = ROOT / "build" / "um3_candidate"
_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

# 분류 자체가 쟁점인 재료(빨강). 나머지 E는 성분을 추정한 시판 제품(노랑)
CLASSIFICATION = {
    "coconut": "코코넛을 견과류 알레르기로 볼지가 쟁점. 국내 법정 대상은 아니다. 미국 FDA는 한때 견과류로 분류했다가 "
               "2025년 지침에서 뺀 것으로 알고 있으나 확인이 필요하다. 기타 견과류 possible로 두면 견과류 알레르기 사용자에게 코코넛밀크 레시피가 제외된다.",
    "acorn_jelly": "도토리(참나무 열매)를 견과류로 볼지가 쟁점. 도토리 알레르기 보고는 드물다. "
                   "possible로 두면 견과류 알레르기 사용자에게 도토리묵 레시피가 제외된다.",
    "sea_squirt": "멍게는 조개류가 아니라 피낭동물이다. 법정 '조개류'에 넣을지, 기타 해산물로 둘지가 쟁점(지금 제안: 조개류 possible).",
    "mideodeok": "미더덕도 멍게와 같은 피낭동물. 멍게와 같은 결정을 따르는 것이 자연스럽다.",
}
# 화면 문구: 재료 검수 화면과 뜻이 달라지는 곳만 바꾼다(찾지 못하면 실패)
TEXT = [
    ("<title>재료 검수</title>", "<title>미매칭 2차 확인</title>"),
    ("<h1>draft 재료 검수</h1>", "<h1>미매칭 2차 보강 · 꼭 확인할 재료</h1>"),
    ("미매칭 보강(um-2)으로 추가한 재료와 이전부터 검수 대기 중인 재료입니다.",
     "식품안전나라 미매칭 1,193개 중 일괄 승인분은 이미 반영했고, 성분을 추정한 시판 제품과 분류가 불확실한 재료만 남겼습니다."),
    ("<b>O</b> 검수 완료(reviewed)로 바꿈(메모가 있으면 고친 뒤) · <b>X</b> 이 재료를 지움(그 표기는 다시 미매칭이 되어 알레르기 사용자에게 제외) · <b>보류</b> draft 그대로 둠.",
     "<b>O</b> 제안대로 재료를 추가하고 표기를 연결(메모가 있으면 고친 뒤) · <b>X</b> 추가하지 않음(미매칭 유지, 알레르기 사용자에게 제외) · <b>보류</b> 이번에는 반영하지 않음."),
    ('<option value="시판 제품">시판 제품</option><option value="새 재료">새 재료</option><option value="이전 draft">이전 draft</option>',
     '<option value="분류 쟁점">분류 쟁점</option><option value="시판 제품">시판 제품</option>'),
    ('const FORMAT = "ingredient-decisions/1";', 'const FORMAT = "unmapped-round2-decisions/1";'),
    ('yellow: ["확인 후 결정", "포장 표시 확인이 필요해 보류로 둔 시판 제품"]', 'yellow: ["확인 후 결정", "성분을 넓게 possible로 잡은 시판 제품"]'),
    ('const KEY = "ingredient-review/"', 'const KEY = "unmapped-round2/"'),
    ('a.download = "ingredient_decisions.json";', 'a.download = "unmapped_round2_decisions.json";'),
    ('toast("ingredient_decisions.json을', 'toast("unmapped_round2_decisions.json을'),
]


def _flow(v) -> str:
    return yaml.safe_dump(v, allow_unicode=True, default_flow_style=True, width=10**6).strip().removesuffix("...").strip()


def candidate_knowledge(pending) -> Path:
    """knowledge 사본에 확인 대기 재료를 draft로 붙인다(알레르기 미리보기용)."""
    if CANDIDATE.exists():
        shutil.rmtree(CANDIDATE)
    shutil.copytree(ROOT / "knowledge", CANDIDATE / "knowledge")
    lines = ["", "# --- um-3 꼭 확인(미리보기용 사본) ---"]
    for e in pending:
        n = e.new
        name = normalize_term(n["name"])
        lines += [f"- id: {n['id']}", f"  name: {_flow(n['name'])}"]
        aliases = [t for t in e.texts if normalize_term(t) != name]
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


def build() -> tuple[str, list[dict]]:
    pending = [e for e in load_proposal(ROUND2) if e.kind == "E" and e.decision is None]
    ck = compile_paths(candidate_knowledge(pending), ROOT / "config" / "pantry_staples.yaml")
    names = {i.id: i.name for i in ck.ingredients}
    groups = {g.id: g.display_name for g in ck.allergen_groups if g.kind == "base"}
    closure: dict[str, list[dict]] = defaultdict(list)
    for r in sorted(ck.allergen_closure, key=lambda r: r.allergen_group_id):
        if r.allergen_group_id in groups:
            closure[r.ingredient_id].append({"group": groups[r.allergen_group_id], "possible": r.certainty == "possible",
                                             "via": " → ".join(names[i] for i in r.via)})
    # 식품안전나라 레시피: 이 표기를 쓰는 레시피, 이 재료만 승인되면 미매칭이 없어지는 레시피
    term_of = {normalize_term(t): e.new["id"] for e in pending for t in e.texts}
    uses: dict[str, list[str]] = defaultdict(list)
    unlock: dict[str, int] = defaultdict(int)
    for path in sorted((ROOT / "data" / "recipes_foodsafety").glob("fs_*.yaml")):
        d = yaml.load(path.read_text(encoding="utf-8"), Loader=_LOADER)
        miss = {normalize_term(ingredient_name(i["raw_text"])) for i in d["ingredients"] if i["ingredient"] is None}
        hit = {term_of[k] for k in miss if k in term_of}
        for i in hit:
            uses[i].append(d["title"])
        if len(hit) == 1 and all(k in term_of for k in miss):
            unlock[next(iter(hit))] += 1

    rows = []
    for n, e in enumerate(sorted(pending, key=lambda e: (e.new["id"] not in CLASSIFICATION, -len(uses[e.new["id"]]))), 1):
        i = e.new
        red = i["id"] in CLASSIFICATION
        derived = [names[d] + ("(가능)" if d_c == "possible" else "") for d, d_c in
                   ((x["id"], x.get("certainty")) if isinstance(x, dict) else (x, None) for x in i.get("derived_from") or [])]
        rows.append({
            "n": n, "id": i["id"], "name": i["name"], "origin": "분류 쟁점" if red else "시판 제품",
            "category": i["category"], "conf": i.get("confidence") or "high", "processed": bool(i.get("is_processed")),
            "note": e.note or "", "aliases": e.texts, "is_a": [], "derived_from": derived,
            "allergens": closure[i["id"]], "commercial": not red,
            "engine": 0, "engineTitles": [], "fs": len(uses[i["id"]]), "fsTitles": uses[i["id"]][:5],
            "claude": (CLASSIFICATION[i["id"]] + " 보수적으로 제안대로 두는 쪽을 미리 골랐다." if red else
                       "제품마다 성분이 달라 빠질 수 있는 성분을 possible로 넓게 잡았다(판정에서는 포함으로 간주). "
                       "넓게 잡아 둔 것이라 그대로 승인해도 알레르기가 새지 않는다. 쓰는 제품의 표시를 알면 메모로 줄일 수 있다.")
                      + f" 승인하면 식품안전나라 레시피 {unlock[i['id']]}개의 미매칭이 모두 풀린다.",
            "prefill": {"decision": "O", "memo": "", "color": "red" if red else "yellow"},
        })
    payload = {"title": "미매칭 2차 확인", "rows": rows, "source": "docs/review/unmapped_round2.yaml (decision 없음 = 꼭 확인)"}
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
    red = sum(1 for r in rows if r["prefill"]["color"] == "red")
    print(f"검수 화면: {OUT.relative_to(ROOT).as_posix()} (꼭 확인 {len(rows)}개, 분류 쟁점 {red}개)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
