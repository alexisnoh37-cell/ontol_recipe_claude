"""식품안전나라 레시피 정적 HTML 뷰어 (docs/plan.md 5-3-1, 개인용).

    uv run python scripts/make_foodsafety_viewer.py
      입력: data/external/foodsafety/raw/COOKRCP01.json (scripts/fetch_foodsafety.py 결과)
      출력: data/recipes_foodsafety/viewer.html (gitignore. 브라우저로 파일을 직접 연다)

변환 규칙은 scripts/convert_foodsafety.py와 같다(kb/foodsafety.py). 재료마다 정규 재료 매칭 여부를 표시하고,
원본의 사진·영양 정보·저감 조리 팁도 함께 보여 준다. 사진은 식품안전나라 서버에서 직접 불러온다(인터넷 필요).
레시피 본문이 들어 있으므로 외부에 올리거나 공유하지 않는다(D3 보완 2).
종료 코드: 0 성공, 2 설정 오류.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kb import KnowledgeError, compile_paths  # noqa: E402
from kb.foodsafety import MANUAL_COUNT, NAME_OVERRIDES, SOURCE_LABEL, SERVICE_ID, clean_step, convert_row  # noqa: E402
from kb.youtube_seed import load_name_overrides  # noqa: E402

DEFAULT_RAW = ROOT / "data" / "external" / "foodsafety" / "raw" / f"{SERVICE_ID}.json"
DEFAULT_OUT = ROOT / "data" / "recipes_foodsafety" / "viewer.html"
TEMPLATE = Path(__file__).resolve().parent / "foodsafety_viewer_template.html"
NUTRITION = (("INFO_ENG", "열량", "kcal"), ("INFO_CAR", "탄수화물", "g"), ("INFO_PRO", "단백질", "g"),
             ("INFO_FAT", "지방", "g"), ("INFO_NA", "나트륨", "mg"))


def _num(value: Any) -> float | None:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def viewer_records(rows: list[dict[str, Any]], alias_index: dict[str, str], concept_ids: frozenset[str],
                   names: dict[str, str], overrides: dict[str, dict] | None = None) -> list[dict[str, Any]]:
    """원본 행 → 뷰어용 레코드. 재료정보가 없어 변환되지 않는 행은 뺀다(convert_foodsafety와 같은 기준)."""
    out = []
    for row in rows:
        recipe = convert_row(row, alias_index, concept_ids, overrides)
        if recipe is None:
            continue
        steps = []
        for n in range(1, MANUAL_COUNT + 1):
            text = clean_step(str(row.get(f"MANUAL{n:02d}") or ""))
            if text:
                steps.append({"t": text, "img": str(row.get(f"MANUAL_IMG{n:02d}") or "").strip()})
        ings = [{"t": i["raw_text"], "id": i["ingredient"], "name": names.get(i["ingredient"] or "", "")}
                for i in recipe["ingredients"]]
        out.append({
            "id": recipe["id"],
            "seq": int(recipe["id"][3:]),
            "title": recipe["title"],
            "pat": str(row.get("RCP_PAT2") or "").strip() or "기타",
            "way": str(row.get("RCP_WAY2") or "").strip() or "기타",
            "img": str(row.get("ATT_FILE_NO_MK") or row.get("ATT_FILE_NO_MAIN") or "").strip(),
            "thumb": str(row.get("ATT_FILE_NO_MAIN") or row.get("ATT_FILE_NO_MK") or "").strip(),
            "tag": str(row.get("HASH_TAG") or "").strip(),
            "tip": str(row.get("RCP_NA_TIP") or "").strip(),
            "nut": [[label, _num(row.get(key)), unit] for key, label, unit in NUTRITION],
            "ings": ings,
            "miss": sum(1 for i in ings if i["id"] is None),
            "steps": steps,
        })
    out.sort(key=lambda r: r["seq"])
    return out


def render(records: list[dict[str, Any]], fetched_on: str | None) -> str:
    data = json.dumps({"source": SOURCE_LABEL, "fetched_on": fetched_on, "recipes": records},
                      ensure_ascii=False, separators=(",", ":"))
    # <script type="application/json"> 안에서 "</script>"로 끝나지 않도록
    data = data.replace("</", "<\\/").replace("<!--", "<\\!--")
    return TEMPLATE.read_text(encoding="utf-8").replace("/*__DATA__*/", data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--knowledge-dir", type=Path, default=ROOT / "knowledge")
    parser.add_argument("--pantry", type=Path, default=ROOT / "config" / "pantry_staples.yaml")
    args = parser.parse_args(argv)

    if not args.raw.is_file():
        print(f"원본이 없습니다: {args.raw} (먼저 scripts/fetch_foodsafety.py)", file=sys.stderr)
        return 2
    try:
        ck = compile_paths(args.knowledge_dir, args.pantry)
    except (FileNotFoundError, KnowledgeError) as exc:
        print(f"지식 컴파일 실패: {exc}", file=sys.stderr)
        return 2
    raw = json.loads(args.raw.read_text(encoding="utf-8"))
    alias_index = {a.alias_norm: a.ingredient_id for a in ck.aliases}
    names = {i.id: i.name for i in ck.ingredients}
    records = viewer_records(raw["rows"], alias_index, ck.concept_ids, names, load_name_overrides(ROOT, ck, NAME_OVERRIDES))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render(records, raw.get("fetched_on")), encoding="utf-8")
    print(f"레시피 {len(records)}개 → {args.out} ({args.out.stat().st_size / 1e6:.1f}MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
