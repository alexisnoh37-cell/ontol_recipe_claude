"""API 표시 계층: id → 이름, 안내 문구, 성분표 확인 표시, 제외 사유 요약, 별칭 검색.

판정은 하지 않는다. 엔진 결과(RecommendResult)와 컴파일된 지식을 화면용으로 바꿀 뿐이다.
레시피별 안내는 데이터가 바뀌지 않는 동안 같으므로 Catalog를 만들 때 한 번 계산한다.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from engine.korean import josa
from engine.model import KnowledgeSnapshot, RecommendItem, RecommendResult
from kb.datacheck import RecipeSpec
from kb.text import normalize_term
from storage.engine_source import CONFIG_DIR, EngineData, snapshot_from_compiled

TASTE_DIMENSIONS = ("spicy", "salty", "sweet", "sour", "umami", "savory")


def load_display(config_dir: Path = CONFIG_DIR) -> dict[str, Any]:
    return yaml.safe_load((config_dir / "display.yaml").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class LabelCheck:
    ingredient_id: str
    name: str
    possible_groups: tuple[str, ...]  # 포함 가능(possible)인 기본 알레르기 그룹 표시 이름
    low_confidence: bool

    def text(self) -> str:
        why = []
        if self.possible_groups:
            why.append("·".join(self.possible_groups) + " 포함 가능")
        if self.low_confidence:
            why.append("성분 정보 확인 필요")
        return f"{self.name}({', '.join(why)})"


@dataclass(frozen=True)
class RecipeDisplay:
    notices: tuple[str, ...]
    label_check: tuple[LabelCheck, ...]


class Catalog:
    """한 번 불러온 EngineData 위의 조회·표시 도우미."""

    def __init__(self, data: EngineData, display: dict[str, Any]):
        ck = data.knowledge
        self.data = data
        self.display = display
        self.snapshot: KnowledgeSnapshot = snapshot_from_compiled(ck)
        self.names = dict(self.snapshot.ingredient_names)
        self.ingredients = {i.id: i for i in ck.ingredients}
        self.groups = {g.id: g for g in ck.allergen_groups}
        self.members: dict[str, list[str]] = {}
        for m in ck.group_members:
            self.members.setdefault(m.bundle_id, []).append(m.member_id)
        self.vocab = ck.vocab
        self.recipes: dict[str, RecipeSpec] = {r.id: r for r in data.recipes}
        self._aliases = [(a.alias_norm, a.alias, a.ingredient_id, a.is_primary) for a in ck.aliases]
        self._recipe_display = {r.id: self._build_recipe_display(r) for r in data.recipes}

    # --- 알레르기 그룹 -----------------------------------------------------------------------------

    def group_kind(self, group_id: str) -> str:
        g = self.groups[group_id]
        if g.kind == "bundle":
            return "bundle"
        return "official" if g.official else "custom"

    def allergen_groups(self) -> list[dict[str, Any]]:
        order = {"official": 0, "custom": 1, "bundle": 2}
        kinds = self.display["allergen_group_kinds"]
        notices = self.display.get("allergen_group_notices") or {}
        out = []
        for g in self.groups.values():
            kind = self.group_kind(g.id)
            out.append({
                "id": g.id, "display_name": g.display_name, "kind": g.kind, "official": g.official,
                "source": g.source, "category": kind, "category_label": kinds[kind],
                "members": [{"id": m, "display_name": self.groups[m].display_name}
                            for m in sorted(self.members.get(g.id, []))],
                "notice": notices.get(g.id),
            })
        return sorted(out, key=lambda x: (order[x["category"]], x["id"]))

    # --- 재료 검색 ------------------------------------------------------------------------------------

    def search(self, q: str, *, limit: int = 20, include_concepts: bool = False) -> list[dict[str, Any]]:
        """이름·별칭 검색. 정확히 일치 → 앞부분 일치 → 포함 순, 같은 순위면 대표 이름·짧은 별칭 먼저.

        concept(해산물 등 넓은 분류)는 보유 재료로 쓸 수 없어 기본으로 뺀다(선호 대상 검색에서만 포함).
        """
        key = normalize_term(q)
        if not key:
            return []
        best: dict[str, tuple[tuple, str]] = {}
        for norm, alias, ing_id, primary in self._aliases:
            if not include_concepts and ing_id in self.snapshot.concept_ids:
                continue
            if norm == key:
                rank = 0
            elif norm.startswith(key):
                rank = 1
            elif key in norm:
                rank = 2
            else:
                continue
            sort_key = (rank, not primary, len(norm), norm)
            if ing_id not in best or sort_key < best[ing_id][0]:
                best[ing_id] = (sort_key, alias)
        ranked = sorted(best.items(), key=lambda kv: (kv[1][0], kv[0]))[:limit]
        out = []
        for ing_id, (_, alias) in ranked:
            i = self.ingredients[ing_id]
            out.append({
                "id": ing_id, "name": i.name, "matched": alias, "category": i.category,
                "is_concept": i.kind == "concept", "is_pantry_staple": i.is_pantry_staple,
            })
        return out

    # --- 레시피 표시 ----------------------------------------------------------------------------------

    def _build_recipe_display(self, r: RecipeSpec) -> RecipeDisplay:
        ids = [line.ingredient for line in r.ingredients if line.ingredient]
        notices: list[str] = []
        recipe_notice = (self.display.get("recipe_notices") or {}).get(r.id)
        if recipe_notice:
            notices.append(recipe_notice)
        for target, text in (self.display.get("ingredient_notices") or {}).items():
            if any(i == target or target in self.snapshot.contains.get(i, {}) for i in ids):
                notices.append(text)
        checks: list[LabelCheck] = []
        for i in dict.fromkeys(ids):  # 순서 유지 중복 제거
            possible = tuple(
                self.groups[g].display_name
                for g, hits in self.snapshot.allergen_closure.items()
                if self.groups[g].kind == "base" and i in hits and hits[i].certainty == "possible"
            )
            low = self.ingredients[i].confidence == "low"
            if possible or low:
                checks.append(LabelCheck(i, self.names[i], possible, low))
        return RecipeDisplay(tuple(notices), tuple(checks))

    def recipe_display(self, recipe_id: str) -> RecipeDisplay:
        return self._recipe_display[recipe_id]

    def item(self, item: RecommendItem) -> dict[str, Any]:
        spec = self.recipes.get(item.recipe_id)
        disp = self.recipe_display(item.recipe_id)
        labels = self.display["breakdown_labels"]
        return {
            "recipe_id": item.recipe_id,
            "title": item.title,
            "cuisine": spec.cuisine if spec else None,
            "difficulty": spec.difficulty if spec else None,
            "cook_time_min": spec.cook_time_min if spec else None,
            "score": item.score,
            "breakdown": [{"key": k, "label": labels.get(k, k), "value": v} for k, v in item.breakdown.items()],
            "missing": [{"id": m, "name": self.names.get(m, m)} for m in item.missing],
            "missing_text": _missing_text([self.names.get(m, m) for m in item.missing]),
            "substitutions": [
                {"need_id": s.need_id, "need_name": self.names[s.need_id], "use_id": s.use_id,
                 "use_name": self.names[s.use_id],
                 "text": f"{self.names[s.need_id]} 대신 {josa(self.names[s.use_id], '을')} 쓸 수 있습니다"}
                for s in item.substitutions
            ],
            "notes": list(item.notes),
            "notices": list(disp.notices),
            "label_check": {
                "message": self.display["label_check"],
                "ingredients": [{"id": c.ingredient_id, "name": c.name, "possible_groups": list(c.possible_groups),
                                 "low_confidence": c.low_confidence, "text": c.text()} for c in disp.label_check],
            } if disp.label_check else None,
        }

    def exclusion_summary(self, result: RecommendResult, examples: int = 3) -> list[dict[str, Any]]:
        """사유별 제외 레시피 수와 예시 제목. 한 레시피가 사유 여러 개면 사유마다 센다(엔진 요약과 같음)."""
        labels = self.display["exclusion_labels"]
        titles: dict[str, list[str]] = {}
        for e in result.exclusions:
            title = self.recipes[e.recipe_id].title if e.recipe_id in self.recipes else e.recipe_id
            bucket = titles.setdefault(e.reason.value, [])
            if title not in bucket:
                bucket.append(title)
        return [{"reason": reason, "label": labels.get(reason, reason), "count": count,
                 "examples": titles.get(reason, [])[:examples]}
                for reason, count in sorted(result.exclusion_summary.items(), key=lambda kv: (-kv[1], kv[0]))]


def _missing_text(names: Iterable[str]) -> str | None:
    names = list(names)
    if not names:
        return None
    return f"{josa(', '.join(names), '이')} 없습니다"
