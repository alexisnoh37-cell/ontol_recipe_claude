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

from api.viz import ing, rcp, use_link
from engine.browse import BrowseItem, BrowseResult
from engine.candidates import owned_ingredients
from engine.korean import josa
from engine.model import ExclusionReason, KnowledgeSnapshot, RecommendItem, RecommendResult
from kb.datacheck import RecipeSpec
from kb.text import normalize_term
from storage.engine_source import CONFIG_DIR, EngineData, snapshot_from_compiled

TASTE_DIMENSIONS = ("spicy", "salty", "sweet", "sour", "umami", "savory")


def load_display(config_dir: Path = CONFIG_DIR) -> dict[str, Any]:
    return yaml.safe_load((config_dir / "display.yaml").read_text(encoding="utf-8"))


def commercial_products(display: dict[str, Any]) -> tuple[str, frozenset[str]]:
    """시판 제품 안내(config/display.yaml commercial_product_notice): (문구, 대상 재료 id)."""
    c = display.get("commercial_product_notice") or {}
    return c.get("text") or "", frozenset(c.get("ingredients") or ())


REQUIRED_ROLES = ("main", "sub", "seasoning")  # 꼭 필요한 재료(기본 양념은 보유로 간주되어 missing에 오지 않음)


@dataclass(frozen=True)
class RecipeDisplay:
    notices: tuple[str, ...]
    label_check: tuple[str, ...]  # 성분표 확인 대상 재료 id(가공품이면서 confidence: low, 선택·고명 포함)
    required_ids: frozenset[str]  # 선택이 아닌 main·sub·seasoning 줄에 쓰인 재료
    commercial: tuple[str, ...] = ()  # 시판 제품 안내 대상 재료 id(선택·고명 포함, 원문 순서)


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
        self.commercial_text, self.commercial_ids = commercial_products(display)
        unknown = self.commercial_ids - set(self.ingredients)
        if unknown:  # 설정 오타로 안내가 조용히 사라지지 않게
            raise ValueError(f"config/display.yaml commercial_product_notice: 모르는 재료 {sorted(unknown)}")
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
        # 1-6 결정: 가공품(is_processed)이면서 confidence: low인 재료만. 소금·설탕 같은 단순 재료는 대상 아님
        checks = tuple(i for i in dict.fromkeys(ids)
                       if self.ingredients[i].is_processed and self.ingredients[i].confidence == "low")
        required = frozenset(line.ingredient for line in r.ingredients
                             if line.ingredient and not line.optional and line.role in REQUIRED_ROLES)
        commercial = tuple(i for i in dict.fromkeys(ids) if i in self.commercial_ids)
        return RecipeDisplay(tuple(notices), checks, required, commercial)

    def commercial_notice(self, disp: RecipeDisplay) -> dict[str, Any] | None:
        """재료 목록 위에 보여 줄 시판 제품 안내. 알레르기 설정과 무관하게 붙인다(um-2)."""
        if not disp.commercial:
            return None
        return {"text": self.commercial_text,
                "ingredients": [{"id": i, "name": self.names[i]} for i in disp.commercial]}

    def recipe_display(self, recipe_id: str) -> RecipeDisplay:
        return self._recipe_display[recipe_id]

    def recipe_detail(self, recipe_id: str, *, pantry: frozenset[str] | None, has_allergy: bool) -> dict[str, Any]:
        """레시피 상세: 역할별 전체 재료와 조리 단계. pantry를 주면 줄마다 보유 여부를 붙인다.

        보유 판정은 추천 엔진과 같은 기준(owned_ingredients: 보유 재료·기본 양념과 그 is_a 조상)이다.
        대체재는 사용자의 알레르기·불선호 확인이 필요해 여기서는 보지 않는다(추천 카드의 대체 안내를 따른다).
        """
        r = self.recipes[recipe_id]
        disp = self.recipe_display(recipe_id)
        owned = None if pantry is None else owned_ingredients(self.snapshot, pantry)
        role_labels = self.display["role_labels"]
        lines = []
        for line in r.ingredients:
            ing = line.ingredient
            lines.append({
                "id": ing,
                "name": self.names.get(ing, ing) if ing else line.raw_text,
                "raw_text": line.raw_text,
                "role": line.role,
                "role_label": role_labels.get(line.role, line.role),
                "optional": line.optional,
                "amount": line.amount,
                "unit": line.unit,
                "unmapped": ing is None,
                "is_pantry_staple": ing in self.snapshot.pantry_staples if ing else False,
                "have": None if owned is None else (ing is not None and ing in owned),
            })
        return {
            "recipe_id": r.id,
            "title": r.title,
            "cuisine": r.cuisine,
            "difficulty": r.difficulty,
            "cook_time_min": r.cook_time_min,
            "servings": r.servings,
            "status": r.status,
            "ingredients": lines,
            "steps": [s.text for s in r.steps],
            "commercial_notice": self.commercial_notice(disp),
            "notices": list(disp.notices),
            "label_check": {
                "message": self.display["label_check"],
                "ingredients": [{"id": i, "name": self.names[i]} for i in disp.label_check],
                "text": f"{self.display['label_check']}: " + ", ".join(self.names[i] for i in disp.label_check),
            } if has_allergy and disp.label_check else None,
        }

    def browse(self, result: BrowseResult, *, has_allergy: bool) -> dict[str, Any]:
        """재료로 레시피 찾기 결과 → 화면용. 그래프 강조용 노드·링크 id(api.viz 규칙)를 함께 싣는다."""
        named = lambda ids: [{"id": i, "name": self.names.get(i, i)} for i in ids]  # noqa: E731
        return {
            "selected": named(result.selected),
            "has_allergy": has_allergy,
            "cookable": [self._browse_item(i) for i in result.cookable],
            "near": [self._browse_item(i) for i in result.near],
            "allergy_notice": self.display["browse_allergy_notice"] if has_allergy else None,
        }

    def _browse_item(self, it: BrowseItem) -> dict[str, Any]:
        r = it.recipe
        spec = self.recipes[r.id]
        lines = {line.line_no: line for line in r.ingredients}
        labels = self.display["exclusion_labels"]

        def line_out(n: int) -> dict[str, Any]:
            line = lines[n]
            ing_id = line.ingredient_id
            return {"line_no": n, "id": ing_id, "name": self.names.get(ing_id, ing_id) if ing_id else line.raw_text,
                    "raw_text": line.raw_text, "role": line.role, "optional": line.optional}

        warnings = []
        for e in it.allergy:
            if e.reason == ExclusionReason.ALLERGEN and e.target:
                hit = (f"{self.groups[e.target].display_name}: {self.names.get(e.ingredient_id, e.ingredient_id)}"
                       + (" (포함 가능)" if e.certainty == "possible" else ""))
            else:
                hit = e.detail or labels.get(e.reason.value, e.reason.value)
            warnings.append({"reason": e.reason.value, "label": labels.get(e.reason.value, e.reason.value),
                             "group": e.target if e.reason == ExclusionReason.ALLERGEN else None,
                             "group_name": self.groups[e.target].display_name
                             if e.reason == ExclusionReason.ALLERGEN and e.target else None,
                             "ingredient_id": e.ingredient_id, "certainty": e.certainty, "text": hit})
        lacking = set(it.missing) | set(it.optional_missing)
        return {
            "recipe_id": r.id,
            "title": r.title,
            "cuisine": r.cuisine,
            "difficulty": spec.difficulty,
            "cook_time_min": spec.cook_time_min,
            "status": spec.status,
            "used": [{"id": i, "name": self.names.get(i, i)} for i in it.used],
            "missing": [line_out(n) for n in it.missing],
            "optional_missing": [line_out(n) for n in it.optional_missing],
            "missing_count": len(it.missing),
            "allergy_warnings": warnings,
            "graph": {
                "recipe": rcp(r.id),
                "used_nodes": [ing(i) for i in it.used],
                "owned_links": [use_link(r.id, line.line_no) for line in r.ingredients
                                if line.ingredient_id and line.line_no not in lacking],
                "missing_links": [use_link(r.id, n) for n in it.missing if lines[n].ingredient_id],
                "missing_nodes": [ing(lines[n].ingredient_id) for n in it.missing if lines[n].ingredient_id],
            },
        }

    def item(self, item: RecommendItem, *, has_allergy: bool) -> dict[str, Any]:
        """has_allergy: 사용자에게 알레르기 설정이 있을 때만 성분표 확인 표시를 붙인다(1-6 결정)."""
        spec = self.recipes.get(item.recipe_id)
        disp = self.recipe_display(item.recipe_id)
        labels = self.display["breakdown_labels"]
        named = lambda ids: [{"id": i, "name": self.names.get(i, i)} for i in ids]  # noqa: E731
        # 부족 재료 표시 구분(1-6, 판정 무관): 꼭 필요한 재료 = 선택이 아닌 main·sub·seasoning,
        # 있으면 좋은 재료 = 고명(garnish)과 선택(optional) 재료
        required = [m for m in item.missing if m in disp.required_ids]
        nice = [m for m in item.missing if m not in disp.required_ids]
        nice += [m for m in item.optional_missing if m not in nice and m not in required]
        optional_notes = {f"{josa(self.names[m], '은')} 선택 재료라 빼고 조리할 수 있습니다"
                          for m in item.optional_missing}
        return {
            "recipe_id": item.recipe_id,
            "title": item.title,
            "cuisine": spec.cuisine if spec else None,
            "difficulty": spec.difficulty if spec else None,
            "cook_time_min": spec.cook_time_min if spec else None,
            "score": item.score,
            "breakdown": [{"key": k, "label": labels.get(k, k), "value": v} for k, v in item.breakdown.items()],
            "missing": named(item.missing),
            "required_missing": named(required),
            "nice_to_have": named(nice),
            "missing_text": _missing_text([self.names.get(m, m) for m in required]),
            "nice_to_have_text": (", ".join(self.names.get(m, m) for m in nice) + " (없어도 조리할 수 있습니다)")
            if nice else None,
            "substitutions": [
                {"need_id": s.need_id, "need_name": self.names[s.need_id], "use_id": s.use_id,
                 "use_name": self.names[s.use_id],
                 "text": f"{self.names[s.need_id]} 대신 {josa(self.names[s.use_id], '을')} 쓸 수 있습니다"}
                for s in item.substitutions
            ],
            "notes": [n for n in item.notes if n not in optional_notes],
            "commercial_notice": self.commercial_notice(disp),
            "notices": list(disp.notices),
            "label_check": {
                "message": self.display["label_check"],
                "ingredients": named(disp.label_check),
                "text": f"{self.display['label_check']}: " + ", ".join(self.names[i] for i in disp.label_check),
            } if has_allergy and disp.label_check else None,
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
