"""미매칭 보강 검수용 HTML(docs/review/unmapped_review.html)을 만든다. 판단은 사람이 화면에서 한다.

    uv run python scripts/make_unmapped_review_html.py

검수표(kb.unmapped_review와 같은 계산)에 두 외부 검토(docs/review/external/)의 승인 열과
미리 채울 판단(docs/review/unmapped_prefill.yaml)을 합쳐 한 파일짜리 HTML로 만든다(인터넷 없이 열림).
화면에서 O·X·보류와 메모를 고친 뒤 '결과 내보내기'로 받은 JSON을 다음 단계에서 검수표에 반영한다.
knowledge/와 data/는 바꾸지 않는다.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kb import compile  # noqa: E402
from kb.load import load_sources  # noqa: E402
from kb.unmapped_review import (  # noqa: E402
    KIND_NAMES,
    PROPOSAL,
    _proposal_text,
    build_rows,
    candidate_knowledge,
    engine_unmapped,
    foodsafety_unmapped,
    load_proposal,
)

TEMPLATE = ROOT / "scripts" / "unmapped_review_template.html"
PREFILL = ROOT / "docs" / "review" / "unmapped_prefill.yaml"
REVIEWS = {
    "gemini": ROOT / "docs" / "review" / "external" / "unmapped_review_gemini.md",
    "reviewed": ROOT / "docs" / "review" / "external" / "unmapped_review_reviewed.md",
}
OUT = ROOT / "docs" / "review" / "unmapped_review.html"


def review_column(path: Path) -> dict[int, tuple[str, str]]:
    """검토본 표의 (번호 → (첫 표기, 승인 열))."""
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if re.match(r"^\| \d+ \|", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            out[int(cells[0])] = (cells[1].split(" · ")[0], cells[-1])
    return out


def verdict(text: str) -> str:
    """승인 열 → O | X | M(수정 지시) | ?"""
    t = text.strip()
    if t.startswith("수정"):
        return "M"
    if t.startswith("O"):
        return "O"
    if t.startswith("X"):
        return "X"
    return "?"


def prefill(kind: str, key: str, g: str, r: str, overrides: dict) -> dict:
    if key in overrides:
        o = overrides[key]
        return {"decision": o["decision"], "memo": o.get("memo") or "", "color": o["color"], "claude": o.get("claude") or ""}
    vg, vr = verdict(g), verdict(r)
    if kind == "C":
        return {"decision": "O", "memo": "", "color": "white",
                "claude": "보류(미매칭 유지)에 동의. 두 검토의 O·X는 모두 '미매칭 유지'라 결과가 같다."}
    if vg == vr == "O" and g == "O" and r == "O":
        return {"decision": "O", "memo": "", "color": "white", "claude": "세 의견 모두 O."}
    if vg == vr == "M":
        memo = re.sub(r"^수정:\s*", "", r)
        return {"decision": "O", "memo": memo, "color": "blue", "claude": "두 검토 모두 수정 지시. reviewed본 문구로 채움."}
    raise SystemExit(f"'{key}': 두 검토 의견이 갈립니다(G={g!r}, R={r!r}). {PREFILL.name}에 판단을 적어 주세요.")


def build() -> tuple[str, list[dict]]:
    """(HTML, 행 데이터)."""
    entries = load_proposal(ROOT / PROPOSAL)
    ck_now = compile(load_sources(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml"))
    ck_new = candidate_knowledge(ROOT, entries)
    eng = engine_unmapped(ROOT, ck_now)
    fs = foodsafety_unmapped(ROOT)
    rows = build_rows(entries, ck_new, eng, fs)
    names = {i.id: i.name for i in ck_new.ingredients}
    reviews = {k: review_column(p) for k, p in REVIEWS.items()}
    overrides = yaml.safe_load(PREFILL.read_text(encoding="utf-8"))["overrides"]
    used = set()
    data = []
    for n, row in enumerate(rows, 1):
        e = row.entry
        g_key, g = reviews["gemini"][n]
        r_key, r = reviews["reviewed"][n]
        if g_key != e.key or r_key != e.key:
            raise SystemExit(f"{n}번 행이 검토본과 다릅니다({e.key} / {g_key} / {r_key}). 검수표가 바뀌었으면 검토본 대조를 다시 해야 합니다.")
        p = prefill(e.kind, e.key, g, r, overrides)
        used.add(e.key)
        data.append({
            "n": n,
            "key": e.key,
            "terms": e.texts,
            "kind": e.kind,
            "kindName": KIND_NAMES[e.kind],
            "proposal": _proposal_text(e, names).replace("`", ""),
            "allergens": [] if e.kind == "C" or not row.allergens or row.allergens == "없음" else row.allergens.split(", "),
            "noAllergen": e.kind != "C" and row.allergens == "없음",
            "conf": (e.new or {}).get("confidence") or e.confidence or "",
            "eng": len(row.engine.recipes),
            "unlock": row.unlock,
            "engLines": row.engine.lines,
            "fsLines": row.fs.lines,
            "example": row.engine.example or row.fs.example or "",
            "note": e.note or "",
            "gemini": g,
            "reviewed": r,
            "claude": p.pop("claude"),
            "prefill": p,
        })
    unknown = set(overrides) - used
    if unknown:
        raise SystemExit(f"{PREFILL.name}에 검수표에 없는 키가 있습니다: {sorted(unknown)}")
    payload = {"title": "미매칭 보강 검수", "rows": data, "source": "docs/review/unmapped_review.md"}
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/null", blob), data


def main() -> int:
    html, data = build()
    OUT.write_text(html, encoding="utf-8")
    colors = {c: sum(1 for d in data if d["prefill"]["color"] == c) for c in ("red", "yellow", "blue", "white")}
    print(f"검수 화면: {OUT.relative_to(ROOT).as_posix()} ({len(data)}행, 색 {colors})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
