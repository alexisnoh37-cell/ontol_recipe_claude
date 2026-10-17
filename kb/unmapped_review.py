"""미매칭 보강 제안·결정(docs/review/unmapped_proposal.yaml) 읽기와 세 출처 미매칭 집계.

um-1(2026-10-17)에서 이 제안으로 검수표(docs/review/unmapped_review.md)와 검수 화면(unmapped_review.html)을 만들었고,
사람 결정(decision)을 um-2에서 knowledge·원본 이름 보정표(data/recipe_name_overrides.yaml)·식품안전나라 변환 규칙에
반영했다. 검수표와 화면은 반영 전 기준의 기록이라 다시 만들지 않는다(생성 도구는 반영 뒤 삭제).
지금은 반영 결과가 결정과 같은지 확인하는 테스트(tests/kb/test_unmapped_review.py)와 남은 미매칭 집계에 쓴다.

분류(kind): A 별칭 · B 새 재료 · C 보류 · D 이름 다듬기 · E 시판 제품. 뜻은 제안 데이터 머리말에 있다.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from kb import CompiledKnowledge
from kb.foodsafety import ingredient_name
from kb.text import normalize_term
from kb.youtube_seed import alias_index, load_name_overrides

KINDS = ("A", "B", "C", "D", "E")
KIND_NAMES = {"A": "별칭", "B": "새 재료", "C": "보류", "D": "이름 다듬기", "E": "시판 제품"}
ENGINE_DATASETS = (("simplecooking", "자취요리신"), ("sallimpop", "살림팝"))
PROPOSAL = Path("docs/review/unmapped_proposal.yaml")
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
    decision: str | None = None  # 사람 결정(um-2): O | X
    split: list | None = None  # D: 한 줄을 여러 재료로 나눔
    drop: str | None = None  # D: 재료에서 뺌 사유(duplicate:<재료 id> | water | not_ingredient)

    @property
    def texts(self) -> list[str]:
        return [t["text"] if isinstance(t, dict) else t for t in self.terms]

    @property
    def key(self) -> str:
        return self.texts[0]


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
        unknown = set(raw) - {"kind", "terms", "target", "new", "note", "confidence", "decision", "split", "drop"}
        if unknown:
            raise ProposalError(f"항목 {i}: 알 수 없는 키 {sorted(unknown)}")
        # 공백만 다른 표기는 같은 키라 하나만 남긴다(별칭 색인은 공백을 무시한다).
        terms, keys = [], set()
        for t in raw["terms"]:
            k = normalize_term(t["text"] if isinstance(t, dict) else t)
            if k not in keys:
                keys.add(k)
                terms.append(t)
        e = Entry(i, raw["kind"], terms, raw.get("target"), raw.get("new"), raw.get("note"), raw.get("confidence"),
                  raw.get("decision"), raw.get("split"), raw.get("drop"))
        if e.kind not in KINDS:
            raise ProposalError(f"항목 {i}: kind '{e.kind}'")
        if not e.terms:
            raise ProposalError(f"항목 {i}: terms가 비었습니다")
        if e.decision not in (None, "O", "X"):
            raise ProposalError(f"항목 {i} ({e.key}): decision '{e.decision}'")
        if e.kind == "B" and not e.new:
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


def engine_unmapped(root: Path, ck: CompiledKnowledge) -> Unmapped:
    """자취요리신·살림팝 원본 재료 이름 중 지금 지식과 이름 보정표로 매핑되지 않는 것(변환기 kb.youtube_seed와 같은 기준)."""
    index = alias_index(ck)
    overrides = load_name_overrides(root, ck)
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
                if k in index or k in overrides:
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
