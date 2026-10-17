"""식품안전나라 원본(fetch_foodsafety.py 결과) → 레시피 YAML + 미매칭 검수표 (docs/plan.md 5-3-1).

    uv run python scripts/convert_foodsafety.py
      입력: data/external/foodsafety/raw/COOKRCP01.json
      출력: data/recipes_foodsafety/fs_<일련번호>.yaml (커밋 대상 D3 보완 3, 기존 fs_*.yaml은 다시 만든다)
            docs/review/foodsafety_unmatched.md (미매칭 재료 빈도, 레시피별 미매칭 수)

모든 레시피는 source: foodsafety, status: draft, confidence: low, cuisine: 미분류, role: sub.
재료는 별칭 색인 정확 일치만 매핑한다(kb/foodsafety.py). 출력 YAML은 scripts/validate_data.py
--recipes-dir data/recipes_foodsafety로 검사할 수 있다(draft의 미매칭은 허용된다, plan 5-4).
종료 코드: 0 성공, 1 변환 결과가 검증 규칙에 맞지 않음, 2 설정 오류.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from kb import KnowledgeError, compile_paths  # noqa: E402
from kb.datacheck import check_recipes  # noqa: E402
from kb.foodsafety import SERVICE_ID, SOURCE_LABEL, Conversion, convert_rows, ingredient_name  # noqa: E402
from kb.text import normalize_term  # noqa: E402

DEFAULT_RAW = ROOT / "data" / "external" / "foodsafety" / "raw" / f"{SERVICE_ID}.json"
DEFAULT_OUT = ROOT / "data" / "recipes_foodsafety"
DEFAULT_REVIEW = ROOT / "docs" / "review" / "foodsafety_unmatched.md"
TOP_TERMS = 300
HEADER = "# 식품안전나라 레시피 변환 결과 (draft, 개인용)"


def write_recipes(conv: Conversion, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("fs_*.yaml"):
        old.unlink()  # 원본에서 언제든 다시 만들 수 있는 생성물
    for r in conv.recipes:
        text = yaml.safe_dump(r, allow_unicode=True, sort_keys=False, width=200)
        (out_dir / f"{r['id']}.yaml").write_text(
            f"# 자동 변환(scripts/convert_foodsafety.py). 출처: {SOURCE_LABEL}. 개인용, 재배포 금지. 검수 전(draft).\n" + text,
            encoding="utf-8")


def review_markdown(conv: Conversion, fetched_on: str | None) -> str:
    lines_total = sum(len(r["ingredients"]) for r in conv.recipes)
    unmatched_lines = [(r, i) for r in conv.recipes for i in r["ingredients"] if i["ingredient"] is None]
    fully = sum(1 for r in conv.recipes if all(i["ingredient"] for i in r["ingredients"]))
    terms: Counter[str] = Counter()
    example: dict[str, str] = {}
    recipes_of: dict[str, set[str]] = defaultdict(set)
    for r, i in unmatched_lines:
        name = ingredient_name(i["raw_text"])
        key = normalize_term(name)
        terms[key] += 1
        example.setdefault(key, name)
        recipes_of[key].add(r["id"])
    titles = Counter(r["title"] for r in conv.recipes)

    pct = (len(unmatched_lines) / lines_total * 100) if lines_total else 0.0
    out = [
        HEADER, "",
        f"> 생성: `uv run python scripts/convert_foodsafety.py`. 원본 내려받은 날: {fetched_on or '-'}. "
        f"출처: {SOURCE_LABEL}. 이용 범위: 개인용(D3 보완 2), 원본·변환 YAML은 git에 올리지 않는다.",
        "", "## 요약", "",
        f"- 변환한 레시피: {len(conv.recipes)}개, 재료정보가 없어 건너뜀: {len(conv.skipped)}개",
        f"- 재료 줄: {lines_total}개, 미매칭: {len(unmatched_lines)}개({pct:.1f}%)",
        f"- 미매칭 없는 레시피: {fully}개 (나머지는 알레르기 사용자에게 제외 대상)",
        f"- 서로 다른 미매칭 표기: {len(terms)}개",
        "- 모든 레시피: status draft, confidence low, cuisine 미분류, role sub, 조리시간·난이도·맛 없음 → 적재 불가(plan 5-4)",
        "", "## 건너뛴 레시피", "",
    ]
    out += [f"- `{rid}` {name}: {why}" for rid, name, why in conv.skipped] or ["- 없음"]
    dup = sorted(t for t, n in titles.items() if n > 1)
    out += ["", "## 같은 이름의 레시피(중복 의심)", ""]
    out += [f"- {t}: " + ", ".join(f"`{r['id']}`" for r in conv.recipes if r["title"] == t) for t in dup] or ["- 없음"]
    out += ["", f"## 자주 나오는 미매칭 재료 (상위 {TOP_TERMS}개)", "",
            "별칭 보강(`knowledge/`에 draft로 추가) 후보. 이름은 양 표기 앞까지 자른 값이다.", "",
            "| 순위 | 표기 | 횟수 | 레시피 수 |", "| --- | --- | --- | --- |"]
    for n, (key, count) in enumerate(terms.most_common(TOP_TERMS), start=1):
        out.append(f"| {n} | {example[key]} | {count} | {len(recipes_of[key])} |")
    out += ["", "## 미매칭이 적은 레시피 (1~2개)", "", "별칭 몇 개만 보강하면 매핑이 끝나는 레시피.", "",
            "| id | 이름 | 미매칭 표기 |", "| --- | --- | --- |"]
    for r in conv.recipes:
        miss = [i["raw_text"] for i in r["ingredients"] if i["ingredient"] is None]
        if 0 < len(miss) <= 2:
            out.append(f"| `{r['id']}` | {r['title']} | " + " / ".join(m.replace("|", "/") for m in miss) + " |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--raw", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
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
    conv = convert_rows(raw["rows"], alias_index, ck.concept_ids)

    # 미매칭(unmapped)은 예상된 결과. 그 밖의 오류는 변환기 결함이다
    issues = [i for i in check_recipes(ck, [(r["id"], r) for r in conv.recipes]) if i.code != "unmapped"]
    if issues:
        print(f"변환 결과 검증 오류 {len(issues)}건(미매칭 제외):", file=sys.stderr)
        for i in issues[:20]:
            print(f"  {i}", file=sys.stderr)
        return 1

    write_recipes(conv, args.out_dir)
    args.review.write_text(review_markdown(conv, raw.get("fetched_on")), encoding="utf-8")
    lines = sum(len(r["ingredients"]) for r in conv.recipes)
    miss = sum(1 for r in conv.recipes for i in r["ingredients"] if i["ingredient"] is None)
    print(f"레시피 {len(conv.recipes)}개 → {args.out_dir} (건너뜀 {len(conv.skipped)}개)")
    print(f"재료 줄 {lines}개 중 미매칭 {miss}개, 검수표: {args.review}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
