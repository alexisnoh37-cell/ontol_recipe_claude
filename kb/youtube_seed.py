"""YouTube 레시피 데이터셋(data/<name>_recipe_dataset/) → 레시피 시드 형식(data/recipes/README.md) 변환.

자취요리신(scripts/convert_simplecooking.py)과 살림팝(scripts/convert_sallimpop.py)이 같은 원본 형식이라 이 모듈을 함께 쓴다.
원본 YAML은 읽기만 한다. 결과는 data/recipes/<id>.yaml(draft)과 데이터셋 폴더의 CONVERSION.md(원본과 달라진 점)이다.

변환 규칙(2026-10-16 사람 결정, docs/decisions.md D3 예외):
- id(id_overrides 제외), 제목, 사실값(양·단위·맛·시간·난이도·인분), raw_text, 조리 단계, status(draft), confidence, note는 그대로 둔다.
- 재료 이름은 컴파일된 지식의 이름·별칭(공백 무시)으로만 매핑한다. 없거나 concept이면 null(미매칭).
  추측 매핑은 하지 않는다. 미매칭 레시피는 알레르기 사용자에게 제외된다.
- source는 영상 URL 문자열로 바꾼다(시드 형식의 source는 문자열).
- 시드 id 규칙(영문 소문자로 시작)에 맞지 않는 id는 id_overrides로 바꾼다(원본 id는 note에 남김).
- vocab.yaml에 없는 cuisine은 cuisine_overrides로 바꾸고, vocab에 없는 선택(required: false) 조리기구는 뺀다.
  둘 다 note에 원래 값을 남긴다.
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from kb import CompiledKnowledge, KnowledgeError, compile_paths
from kb.text import normalize_term


@dataclass(frozen=True)
class YoutubeDataset:
    name: str  # 폴더 이름(data/<name>_recipe_dataset/recipes/<name>/)
    label: str  # 한국어 채널 이름(기록·머리말)
    script: str  # 변환 스크립트 경로(머리말에 남김)
    id_overrides: dict[str, str] = field(default_factory=dict)  # 원본 id → 시드 id
    cuisine_overrides: dict[str, str] = field(default_factory=dict)  # 원본 id → vocab cuisine(검수 필요)

    def dataset_dir(self, root: Path) -> Path:
        return root / "data" / f"{self.name}_recipe_dataset"

    def source_dir(self, root: Path) -> Path:
        return self.dataset_dir(root) / "recipes" / self.name

    def report_path(self, root: Path) -> Path:
        return self.dataset_dir(root) / "CONVERSION.md"

    @property
    def header(self) -> str:
        return (f"# 레시피 시드 (형식: data/recipes/README.md). {self.label} YouTube 데이터셋에서 변환한 초안(draft, 검수 전).\n"
                f"# 원본: data/{self.name}_recipe_dataset/, 변환: {self.script}\n")


def alias_index(ck: CompiledKnowledge) -> dict[str, str]:
    return {a.alias_norm: a.ingredient_id for a in ck.aliases if a.ingredient_id not in ck.concept_ids}


def convert(ds: YoutubeDataset, ck: CompiledKnowledge, src: dict,
            index: dict[str, str]) -> tuple[dict, list[str], list[str]]:
    """(시드 dict, 미매칭 재료 이름, 원본과 달라진 점)."""
    changes: list[str] = []
    rid = ds.id_overrides.get(src["id"], src["id"])
    if rid != src["id"]:
        changes.append(f"id '{src['id']}'→'{rid}'(시드 id 형식, 원본 파일 이름은 그대로)")
    cuisine = src["cuisine"]
    if cuisine not in ck.vocab["cuisines"]:
        cuisine = ds.cuisine_overrides[src["id"]]
        changes.append(f"cuisine '{src['cuisine']}'→'{cuisine}'(vocab에 없음, 검수 필요)")
    equipment = []
    for e in src["equipment"]:
        if e["name"] in ck.vocab["equipment"]:
            equipment.append({"name": e["name"], "required": e["required"]})
        elif e["required"]:
            raise SystemExit(f"{src['id']}: vocab에 없는 필수 조리기구 '{e['name']}'")
        else:
            changes.append(f"조리기구 '{e['name']}'(선택) 제외(vocab에 없음)")
    unmapped: list[str] = []
    ingredients = []
    for line in src["ingredients"]:
        ing_id = index.get(normalize_term(line["name"]))
        if ing_id is None:
            unmapped.append(line["name"])
        ingredients.append({
            "ingredient": ing_id,
            "raw_text": line["raw_text"],
            "role": line["role"],
            "optional": line["optional"],
            "amount": line["amount"],
            "unit": line["unit"],
        })
    note = "; ".join(x for x in [src["note"], *changes] if x) or None
    out = {
        "id": rid,
        "title": src["title"],
        "cuisine": cuisine,
        "difficulty": src["difficulty"],
        "cook_time_min": src["cook_time_min"],
        "servings": src["servings"],
        "source": src["source"]["video_url"],
        "status": src["status"],
        "confidence": src["confidence"],
        "note": note,
        "ingredients": ingredients,
        "taste": src["taste"],
        "equipment": equipment,
        "steps": [{"text": s["text"], "technique": s["technique"]} for s in src["steps"]],
    }
    return out, unmapped, changes


def render_report(ds: YoutubeDataset, rows: list[tuple[dict, list[str], list[str]]]) -> str:
    total = len(rows)
    full = sum(not u for _, u, _ in rows)
    freq = Counter(name for _, u, _ in rows for name in u)
    lines = [
        f"# {ds.label} 데이터 변환 기록",
        "",
        f"> `{ds.script}`가 생성한다. 손으로 고치지 않는다.",
        "",
        f"원본 `recipes/{ds.name}/*.yaml` {total}개를 `data/recipes/<id>.yaml`(draft)로 변환했다. 원본 파일은 바꾸지 않는다.",
        "",
        "## 원본과 같은 것",
        "",
        "id·파일 이름(아래 표의 id 변경 제외), 제목, 난이도, 시간, 인분, status(draft), confidence, note(아래 추가분 제외), 재료 원문(raw_text)·역할·선택 여부·양·단위, 맛, 조리 단계와 기법.",
        "",
        "## 형식 때문에 달라진 것 (전체 공통)",
        "",
        "| 원본 | 변환본 | 이유 |",
        "| --- | --- | --- |",
        "| `ingredients[].name`(한국어 이름) | `ingredients[].ingredient`(knowledge id 또는 null) | 시드는 정규 id를 쓴다. 이름·별칭(공백 무시)이 정확히 맞을 때만 매핑, 그 외 null(미매칭) |",
        "| `source`(객체: 채널·영상 제목·URL·날짜) | `source`(영상 URL 문자열) | 시드 형식의 source는 문자열. 나머지 출처 정보는 원본에 있다 |",
        "",
        "## 레시피별로 달라진 것",
        "",
    ]
    changed = [(r["id"], r["title"], c) for r, _, c in rows if c]
    if changed:
        lines += ["| id | 제목 | 변경 |", "| --- | --- | --- |"]
        lines += [f"| `{i}` | {t} | {'; '.join(c)} |" for i, t, c in changed]
    else:
        lines.append("없음")
    lines += [
        "",
        "## 재료 매핑",
        "",
        f"- 모든 재료가 매핑된 레시피: {full}/{total}",
        f"- 미매칭 재료가 있는 레시피: {total - full}/{total} (알레르기가 있는 사용자에게 제외됨)",
        "",
        "미매칭 재료(등장 레시피 수). 상표 제품·시판 소스·가공품은 성분을 추측하지 않고 미매칭으로 둔다. 연결하려면 knowledge에 노드나 별칭을 검수해 추가한 뒤 다시 변환한다.",
        "",
        "| 재료 이름 | 레시피 수 |",
        "| --- | --- |",
    ]
    lines += [f"| {name} | {n} |" for name, n in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))]
    dups = []
    for r, _, _ in rows:
        ids = Counter(i["ingredient"] for i in r["ingredients"] if i["ingredient"])
        for ing_id, n in sorted(ids.items()):
            if n > 1:
                raws = " / ".join(i["raw_text"] for i in r["ingredients"] if i["ingredient"] == ing_id)
                dups.append(f"| `{r['id']}` | `{ing_id}` | {raws} |")
    lines += ["", "## 같은 재료 id로 매핑된 줄", "",
              "원본에서 이름이 달라 따로 적힌 줄이 같은 knowledge id로 매핑된 경우. 한 줄로 합칠지 검수한다(변환은 원본 줄을 그대로 둔다).", ""]
    lines += ["| id | 재료 id | 원문 |", "| --- | --- | --- |", *dups] if dups else ["없음"]
    return "\n".join(lines) + "\n"


def run(ds: YoutubeDataset, root: Path) -> int:
    """변환 실행(스크립트 진입점). 다른 출처의 기존 레시피와 id가 겹치면 덮어쓰지 않고 멈춘다."""
    try:
        ck = compile_paths(root / "knowledge", root / "config" / "pantry_staples.yaml")
    except KnowledgeError as exc:
        print(exc, file=sys.stderr)
        return 1
    index = alias_index(ck)
    out_dir = root / "data" / "recipes"
    rows = []
    for path in sorted(ds.source_dir(root).glob("*.yaml")):
        src = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert src["id"] == path.stem, path
        rows.append(convert(ds, ck, src, index))

    ours = {r["id"] for r, _, _ in rows}
    for path in out_dir.glob("*.yaml"):
        if path.stem in ours and ds.header.splitlines()[0] not in path.read_text(encoding="utf-8"):
            raise SystemExit(f"{path}: 기존 레시피와 id가 겹칩니다(덮어쓰지 않음)")
    for out, _, _ in rows:
        body = yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=120)
        (out_dir / f"{out['id']}.yaml").write_text(ds.header + body, encoding="utf-8")
    report = ds.report_path(root)
    report.write_text(render_report(ds, rows), encoding="utf-8")
    full = sum(not u for _, u, _ in rows)
    print(f"변환: {len(rows)}개 → {out_dir.relative_to(root).as_posix()} (완전 매핑 {full}개), "
          f"기록: {report.relative_to(root).as_posix()}")
    return 0
