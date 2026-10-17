"""세 출처 미매칭 보강 검수표(docs/review/unmapped_review.md) 생성 로직.

제안 데이터(docs/review/unmapped_proposal.yaml)를 읽어
1. 지식 원본에 메모리 안에서만 얹어 컴파일해 본다(별칭 충돌·없는 id 검사, 새 재료의 알레르기 계산). 파일은 바꾸지 않는다.
2. 엔진 레시피(자취요리신·살림팝 원본)와 식품안전나라 변환 결과의 미매칭 표기를 세어 항목마다 영향을 계산한다.
3. 엔진 레시피 영향 순으로 정렬한 검수표를 만든다. 이미 적힌 승인 열은 다시 만들어도 유지한다.

분류(kind)의 뜻은 제안 데이터 머리말에 있다. 알레르기 판정 규칙은 바꾸지 않는다(미매칭은 계속 제외).
"""

from __future__ import annotations

import copy
import dataclasses
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from kb import CompiledKnowledge, compile
from kb.foodsafety import ingredient_name
from kb.load import load_sources
from kb.text import normalize_term

KINDS = ("A", "B", "C", "D", "E")
KIND_NAMES = {"A": "별칭", "B": "새 재료", "C": "보류", "D": "이름 다듬기", "E": "시판 제품"}
ENGINE_DATASETS = (("simplecooking", "자취요리신"), ("sallimpop", "살림팝"))
FS_MIN_COUNT = 5  # 식품안전나라만 나오는 표기는 이 횟수 이상만 검수표에 올린다(fs-3과 같은 기준)
PROPOSAL = Path("docs/review/unmapped_proposal.yaml")
OUT = Path("docs/review/unmapped_review.md")
_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


class ProposalError(ValueError):
    pass


@dataclass
class Entry:
    index: int
    kind: str
    terms: list[Any]  # str 또는 {text, form}
    target: str | None = None
    new: dict | None = None
    note: str | None = None
    confidence: str | None = None

    @property
    def texts(self) -> list[str]:
        return [t["text"] if isinstance(t, dict) else t for t in self.terms]

    @property
    def key(self) -> str:
        return self.texts[0]

    @property
    def maps_to(self) -> str | None:
        """승인 시 연결되는 재료 id(C는 None, D의 '재료에서 뺌'도 None)."""
        if self.new:
            return self.new["id"]
        return self.target


@dataclass
class Usage:
    lines: int = 0
    recipes: set[str] = field(default_factory=set)
    example: str | None = None


@dataclass
class Unmapped:
    """출처 하나의 미매칭: 표기(정규화) → 사용 현황, 레시피 → 미매칭 표기 집합."""

    terms: dict[str, Usage]
    by_recipe: dict[str, set[str]]
    recipe_count: int
    line_count: int


def load_proposal(path: Path) -> list[Entry]:
    data = yaml.load(path.read_text(encoding="utf-8"), Loader=_LOADER)
    entries = []
    seen: dict[str, int] = {}
    for i, raw in enumerate(data["entries"]):
        unknown = set(raw) - {"kind", "terms", "target", "new", "note", "confidence"}
        if unknown:
            raise ProposalError(f"항목 {i}: 알 수 없는 키 {sorted(unknown)}")
        # 공백만 다른 표기는 같은 키라 하나만 남긴다(별칭 색인은 공백을 무시한다).
        terms, keys = [], set()
        for t in raw["terms"]:
            k = normalize_term(t["text"] if isinstance(t, dict) else t)
            if k not in keys:
                keys.add(k)
                terms.append(t)
        e = Entry(i, raw["kind"], terms, raw.get("target"), raw.get("new"), raw.get("note"), raw.get("confidence"))
        if e.kind not in KINDS:
            raise ProposalError(f"항목 {i}: kind '{e.kind}'")
        if not e.terms:
            raise ProposalError(f"항목 {i}: terms가 비었습니다")
        if e.kind in ("B",) and not e.new:
            raise ProposalError(f"항목 {i} ({e.key}): B는 new가 필요합니다")
        if e.kind == "A" and not e.target:
            raise ProposalError(f"항목 {i} ({e.key}): A는 target이 필요합니다")
        if e.kind == "E" and not (e.new or e.target):
            raise ProposalError(f"항목 {i} ({e.key}): E는 new 또는 target이 필요합니다")
        if e.kind == "C" and (e.new or e.target):
            raise ProposalError(f"항목 {i} ({e.key}): C에는 target·new를 쓰지 않습니다")
        for t in e.texts:
            k = normalize_term(t)
            if k in seen:
                raise ProposalError(f"표기 '{t}'가 항목 {seen[k]}과 {i}에 함께 있습니다")
            seen[k] = i
        entries.append(e)
    return entries


def candidate_knowledge(root: Path, entries: list[Entry]) -> CompiledKnowledge:
    """C를 뺀 모든 제안을 반영한 지식(메모리 안에서만). 충돌·없는 id가 있으면 KnowledgeError."""
    src = load_sources(root / "knowledge", root / "config" / "pantry_staples.yaml")
    docs = [(name, copy.deepcopy(items)) for name, items in src.ingredients]
    by_id = {item["id"]: item for _, items in docs for item in (items or [])}
    added = []
    for e in entries:
        if e.kind in ("A", "E") and e.target:
            item = by_id.get(e.target)
            if item is None:
                raise ProposalError(f"항목 {e.index} ({e.key}): 없는 재료 '{e.target}'")
            item.setdefault("aliases", []).extend(copy.deepcopy(e.terms))
        if e.new:
            if e.new["id"] in by_id:
                raise ProposalError(f"항목 {e.index} ({e.key}): 이미 있는 재료 id '{e.new['id']}'")
            item = {k: copy.deepcopy(v) for k, v in e.new.items()}
            name_key = normalize_term(item["name"])
            aliases = [t for t in e.terms if normalize_term(t["text"] if isinstance(t, dict) else t) != name_key]
            if aliases:
                item["aliases"] = copy.deepcopy(aliases)
            item["status"] = "draft"
            if e.note:
                item["note"] = e.note
            added.append(item)
            by_id[item["id"]] = item
    new_ids = {e.new["id"] for e in entries if e.new}
    for e in entries:
        if e.kind == "D" and e.target and e.target not in by_id:
            raise ProposalError(f"항목 {e.index} ({e.key}): 없는 재료 '{e.target}'")
        if e.kind == "D" and e.target in new_ids and not any(x.new and x.new["id"] == e.target for x in entries):
            raise ProposalError(f"항목 {e.index} ({e.key}): '{e.target}'를 정의한 항목이 없습니다")
    docs.append(("docs/review/unmapped_proposal.yaml", added))
    return compile(dataclasses.replace(src, ingredients=tuple(docs)))


def _alias_index(ck: CompiledKnowledge) -> dict[str, str]:
    return {a.alias_norm: a.ingredient_id for a in ck.aliases if a.ingredient_id not in ck.concept_ids}


def engine_unmapped(root: Path, ck: CompiledKnowledge) -> Unmapped:
    """자취요리신·살림팝 원본 재료 이름 중 지금 지식으로 매핑되지 않는 것(변환기 kb.youtube_seed와 같은 기준)."""
    index = _alias_index(ck)
    terms: dict[str, Usage] = defaultdict(Usage)
    by_recipe: dict[str, set[str]] = {}
    recipes = lines = 0
    for name, _ in ENGINE_DATASETS:
        for path in sorted((root / "data" / f"{name}_recipe_dataset" / "recipes" / name).glob("*.yaml")):
            src = yaml.load(path.read_text(encoding="utf-8"), Loader=_LOADER)
            recipes += 1
            keys = set()
            for line in src["ingredients"]:
                lines += 1
                k = normalize_term(line["name"])
                if k in index:
                    continue
                u = terms[k]
                u.lines += 1
                u.recipes.add(src["id"])
                u.example = u.example or f"{line['raw_text']} [{src['title']}]"
                keys.add(k)
            if keys:
                by_recipe[src["id"]] = keys
    return Unmapped(dict(terms), by_recipe, recipes, lines)


def foodsafety_unmapped(root: Path) -> Unmapped:
    """식품안전나라 변환 결과(data/recipes_foodsafety/)에서 ingredient가 null인 줄. 표기는 양 표기 앞 이름."""
    terms: dict[str, Usage] = defaultdict(Usage)
    by_recipe: dict[str, set[str]] = {}
    recipes = lines = 0
    for path in sorted((root / "data" / "recipes_foodsafety").glob("*.yaml")):
        d = yaml.load(path.read_text(encoding="utf-8"), Loader=_LOADER)
        recipes += 1
        keys = set()
        for line in d["ingredients"]:
            lines += 1
            if line.get("ingredient") is not None:
                continue
            k = normalize_term(ingredient_name(line["raw_text"]))
            u = terms[k]
            u.lines += 1
            u.recipes.add(d["id"])
            u.example = u.example or f"{line['raw_text']} [{d['title']}]"
            keys.add(k)
        if keys:
            by_recipe[d["id"]] = keys
    return Unmapped(dict(terms), by_recipe, recipes, lines)


@dataclass
class Row:
    entry: Entry
    engine: Usage
    unlock: int  # 이 항목만 해결하면 미매칭이 0이 되는 엔진 레시피 수
    fs: Usage
    allergens: str


def _resolved_keys(entries: list[Entry], kinds: set[str]) -> set[str]:
    """kinds를 모두 승인했을 때 해결되는 표기. D가 B·E의 새 재료를 가리키면 그 항목 kind도 승인되어야 한다."""
    defined = {e.new["id"]: e.kind for e in entries if e.new}
    out = set()
    for e in entries:
        if e.kind not in kinds or e.kind == "C":
            continue
        if e.kind == "D" and e.target in defined and defined[e.target] not in kinds:
            continue
        out.update(normalize_term(t) for t in e.texts)
    return out


def simulate(u: Unmapped, resolved: set[str]) -> tuple[int, int]:
    """(남는 미매칭 줄, 미매칭 없는 레시피 수)."""
    left_lines = sum(v.lines for k, v in u.terms.items() if k not in resolved)
    clean = u.recipe_count - sum(1 for keys in u.by_recipe.values() if keys - resolved)
    return left_lines, clean


def allergen_text(ck: CompiledKnowledge, ingredient_id: str | None) -> str:
    if ingredient_id is None:
        return ""
    # 묶음(갑각류·생선 전체 등)은 기본 그룹의 합이라 기본 그룹만 보인다.
    names = {g.id: g.display_name for g in ck.allergen_groups if g.kind == "base"}
    rows = sorted((r for r in ck.allergen_closure if r.ingredient_id == ingredient_id and r.allergen_group_id in names),
                  key=lambda r: r.allergen_group_id)
    if not rows:
        return "없음"
    return ", ".join(names[r.allergen_group_id] + ("(가능)" if r.certainty == "possible" else "") for r in rows)


def build_rows(entries: list[Entry], ck: CompiledKnowledge, eng: Unmapped, fs: Unmapped) -> list[Row]:
    rows = []
    for e in entries:
        keys = {normalize_term(t) for t in e.texts}
        eu, fu = Usage(), Usage()
        for k in (normalize_term(t) for t in e.texts):  # 표기 순서대로(예시 원문을 결정적으로 고른다)
            for src, dst in ((eng.terms.get(k), eu), (fs.terms.get(k), fu)):
                if src:
                    dst.lines += src.lines
                    dst.recipes |= src.recipes
                    dst.example = dst.example or src.example
        unlock = sum(1 for rk in eng.by_recipe.values() if rk <= keys)
        rows.append(Row(e, eu, unlock, fu, allergen_text(ck, e.maps_to)))
    rows.sort(key=lambda r: (-len(r.engine.recipes), -r.unlock, -r.engine.lines, -r.fs.lines, r.entry.index))
    return rows


def unclassified(entries: list[Entry], eng: Unmapped, fs: Unmapped) -> tuple[list[str], list[str]]:
    """(분류 안 된 엔진 표기, 분류 안 된 식품안전나라 표기(FS_MIN_COUNT 이상))."""
    known = {normalize_term(t) for e in entries for t in e.texts}
    e_left = sorted(k for k in eng.terms if k not in known)
    f_left = sorted(k for k, v in fs.terms.items() if v.lines >= FS_MIN_COUNT and k not in known and k not in eng.terms)
    return e_left, f_left


def read_approvals(path: Path) -> dict[str, str]:
    """기존 검수표의 승인 열(대표 표기 → 값). 다시 만들어도 사람이 적은 값을 잃지 않게 한다."""
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\| (\d+) \| (.+?) \|", line)
        if m:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            key = re.sub(r"\s*\(외 \d+\)$", "", cells[1].split(" · ")[0]).strip()
            if cells[-1]:
                out[key] = cells[-1]
    return out


def _cell(text: Any) -> str:
    return str(text or "").replace("|", "／").replace("\n", " ")


def _proposal_text(e: Entry, names: dict[str, str]) -> str:
    if e.kind == "C":
        return "미매칭 유지"
    if e.new:
        n = e.new
        rel = []
        if n.get("is_a"):
            rel.append("is_a " + ", ".join(n["is_a"]))
        if n.get("derived_from"):
            parts = []
            for d in n["derived_from"]:
                did, cert = (d["id"], d.get("certainty", "definite")) if isinstance(d, dict) else (d, "definite")
                parts.append(names.get(did, did) + ("(가능)" if cert == "possible" else ""))
            rel.append("← " + ", ".join(parts))
        return f"새 재료 `{n['id']}` {n['name']} [{n['category']}]" + (" " + "; ".join(rel) if rel else "")
    if e.target is None:
        return "재료에서 뺌"
    form = {t["form"] for t in e.terms if isinstance(t, dict) and t.get("form")}
    prefix = "이름 고침 → " if e.kind == "D" else "별칭 → "
    return f"{prefix}{names.get(e.target, e.target)} (`{e.target}`)" + (f" form {', '.join(sorted(form))}" if form else "")


def render(root: Path, entries: list[Entry], ck: CompiledKnowledge, eng: Unmapped, fs: Unmapped,
           approvals: dict[str, str]) -> str:
    names = {i.id: i.name for i in ck.ingredients}
    rows = build_rows(entries, ck, eng, fs)
    e_left, f_left = unclassified(entries, eng, fs)
    out = [
        "# 미매칭 보강 검수표 (세 출처, 검수 대기)",
        "",
        "> 생성: `uv run python scripts/make_unmapped_review.py`(제안 데이터 `docs/review/unmapped_proposal.yaml`). "
        "다시 만들어도 승인 열은 유지된다. **knowledge와 변환 결과는 아직 바꾸지 않았다.** 승인(O)한 항목만 다음 단계에서 반영한다.",
        "",
        "## 검수 방법",
        "",
        "- 표는 **엔진 레시피(자취요리신·살림팝, 추천에 쓰임) 영향 순**이다. 엔진 레시피 수 → 단독 해결 수 → 엔진 줄 수 → 식품안전나라 줄 수.",
        "- 마지막 '승인' 열에 `O`(그대로 반영), `X`(반영 안 함, 미매칭 유지), 또는 고칠 내용을 적는다.",
        "- 분류: **A 별칭**(기존 재료에 표기 추가) · **B 새 재료**(draft로 추가) · **C 보류**(미매칭 유지) · "
        "**D 이름 다듬기**(원본 이름의 자막 문구·크기·오타를 변환 단계에서 고침, knowledge 무변경) · "
        "**E 시판 제품**(제품마다 성분이 달라 알레르기를 넓게 '가능'으로 잡음).",
        "- **'연결 시 알레르기'가 핵심 확인 항목이다.** 승인하면 그 재료의 알레르기로 판정된다. "
        "빠진 성분이 있으면 그 알레르기 사용자에게 위험하므로, 확신이 없으면 X(미매칭 유지)가 더 안전하다. "
        "특히 E는 포장 표시를 확인할 수 없으면 X를 권한다.",
        "- '(가능)'은 포함 가능(possible)이며 판정에서는 포함으로 간주한다. conf `low`는 성분·분류가 확실하지 않은 항목이다.",
        "- '단독 해결'은 이 항목만 승인해도 미매칭이 0이 되는 엔진 레시피 수다. 식품안전나라는 그래프 표시 전용이라 추천에는 쓰이지 않는다.",
        "",
        "## 효과 (모두 승인한다고 가정한 시뮬레이션)",
        "",
        f"엔진 레시피 {eng.recipe_count}개(재료 줄 {eng.line_count}), 식품안전나라 {fs.recipe_count}개(재료 줄 {fs.line_count}). "
        "미매칭이 하나라도 남은 레시피는 알레르기가 있는 사용자에게 계속 제외된다.",
        "",
        "| 승인 범위 | 엔진 미매칭 줄 | 엔진 미매칭 없는 레시피 | 식품안전나라 미매칭 줄 | 식품안전나라 미매칭 없는 레시피 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for label, kinds in (("현재", set()), ("A", {"A"}), ("A+B", {"A", "B"}), ("A+B+D", {"A", "B", "D"}),
                         ("A+B+D+E", {"A", "B", "D", "E"})):
        resolved = _resolved_keys(entries, kinds)
        el, ec = simulate(eng, resolved)
        fl, fc = simulate(fs, resolved)
        out.append(f"| {label} | {el} ({el / eng.line_count:.1%}) | {ec} / {eng.recipe_count} | "
                   f"{fl} ({fl / fs.line_count:.1%}) | {fc} / {fs.recipe_count} |")
    counts = Counter(r.entry.kind for r in rows)
    out += [
        "",
        "엔진 레시피는 C(보류)만 남는다. 식품안전나라는 1~4회 나오는 표기(긴 꼬리)를 이번 표에 넣지 않아 미매칭이 더 줄지 않는다(추천에는 쓰이지 않음).",
        "",
        "## 항목 수",
        "",
        "| 분류 | 항목 | 엔진 레시피에 나오는 항목 |",
        "| --- | --- | --- |",
    ]
    for k in KINDS:
        out.append(f"| {k} {KIND_NAMES[k]} | {counts[k]} | {sum(1 for r in rows if r.entry.kind == k and r.engine.recipes)} |")
    out += [
        "",
        "## 검수표",
        "",
        "| # | 표기 | 분류 | 제안 | 연결 시 알레르기 | conf | 엔진 레시피 | 단독 해결 | 엔진 줄 | 식품안전나라 줄 | 예시 원문 | 메모 | 승인 |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for n, r in enumerate(rows, 1):
        e = r.entry
        conf = (e.new or {}).get("confidence") or e.confidence or ""
        terms = " · ".join(e.texts)
        example = r.engine.example or r.fs.example or ""
        out.append("| " + " | ".join([
            str(n), _cell(terms), f"{e.kind} {KIND_NAMES[e.kind]}", _cell(_proposal_text(e, names)),
            _cell(r.allergens if e.kind != "C" else "—"), conf, str(len(r.engine.recipes)), str(r.unlock),
            str(r.engine.lines), str(r.fs.lines), _cell(example), _cell(e.note), _cell(approvals.get(e.key, "")),
        ]) + " |")
    out += ["", "## 분류 안 된 표기", ""]
    if not e_left and not f_left:
        out.append("없음(엔진 레시피의 모든 미매칭 표기, 식품안전나라 5회 이상 표기를 모두 분류했다).")
    else:
        if e_left:
            out.append(f"- 엔진 레시피: {', '.join(e_left)}")
        if f_left:
            out.append(f"- 식품안전나라({FS_MIN_COUNT}회 이상): {', '.join(f_left)}")
    out += [
        "",
        f"식품안전나라에서 {FS_MIN_COUNT}회 미만 나오고 엔진 레시피에는 없는 표기 "
        f"{sum(1 for k, v in fs.terms.items() if v.lines < FS_MIN_COUNT and k not in eng.terms)}개는 이번 표에 넣지 않았다"
        "(전체 목록은 `docs/review/foodsafety_unmatched.md`).",
        "",
    ]
    return "\n".join(out)


def make(root: Path) -> str:
    entries = load_proposal(root / PROPOSAL)
    ck_now = compile(load_sources(root / "knowledge", root / "config" / "pantry_staples.yaml"))
    ck_new = candidate_knowledge(root, entries)
    eng = engine_unmapped(root, ck_now)
    fs = foodsafety_unmapped(root)
    return render(root, entries, ck_new, eng, fs, read_approvals(root / OUT))
