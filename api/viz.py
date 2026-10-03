"""시각화 표시 계층 (docs/plan.md 부록 D): 컴파일된 지식+레시피 → 3D 그래프 노드·간선.

판정은 하지 않는다. 컴파일 결과 행(relations, ingredient_allergens, group_members, allergen_closure)과
레시피 시드를 그대로 노드·간선으로 옮길 뿐이다. 층(layer)도 여기서 구조로 정한다(화면이 규칙을 갖지 않음).

  1층 알레르기 그룹(기본·묶음)
  2층 derived_from이 없는 재료(원천 재료·분류 concept)
  3층 derived_from이 하나라도 있는 재료(가공품. is_processed가 아니어도 3층, 화면이 "가공품 아님" 표시)
  4층 레시피

노드 id는 종류 접두어(ing:, ag:, rcp:)를 붙여 재료·레시피 id 충돌을 막는다. 링크 id는 trace의 path_links가 가리킨다.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal

from engine.candidates import CANDIDATE_ROLES
from engine.config import COMPONENTS
from engine.model import Exclusion, ExclusionReason, RecommendResult
from engine.trace import RecommendTrace
from storage.engine_source import EngineData

RecipeScope = Literal["none", "published", "all"]

# 한 레시피에 제외 사유가 여러 개일 때 화면 색을 정하는 대표 사유 순서(표시 전용)
REASON_PRIORITY = (
    ExclusionReason.ALLERGEN, ExclusionReason.UNMAPPED_INGREDIENT, ExclusionReason.HARD_DISLIKE_INGREDIENT,
    ExclusionReason.HARD_DISLIKE_CUISINE, ExclusionReason.SPICY_LIMIT, ExclusionReason.EQUIPMENT, ExclusionReason.TIME,
)

LAYERS = (
    {"layer": 1, "label": "알레르기 그룹"},
    {"layer": 2, "label": "원천 재료·분류"},
    {"layer": 3, "label": "가공품"},
    {"layer": 4, "label": "레시피"},
)


def ing(i: str) -> str:
    return f"ing:{i}"


def ag(g: str) -> str:
    return f"ag:{g}"


def rcp(r: str) -> str:
    return f"rcp:{r}"


def isa_link(child: str, parent: str) -> str:
    return f"isa:{child}>{parent}"


def der_link(product: str, source: str) -> str:
    return f"der:{product}>{source}"


def alg_link(ingredient: str, group: str) -> str:
    return f"alg:{ingredient}>{group}"


def mem_link(bundle: str, member: str) -> str:
    return f"mem:{bundle}>{member}"


def use_link(recipe: str, line_no: int) -> str:
    return f"use:{recipe}#{line_no}"


class GraphCatalog:
    """EngineData 하나 위의 그래프 응답. 데이터 reload 때 새로 만든다(요청 중에는 캐시만 읽음)."""

    def __init__(self, data: EngineData):
        ck = data.knowledge
        self.data = data
        self.groups = {g.id: g for g in ck.allergen_groups}
        self.members: dict[str, list[str]] = {}
        for m in ck.group_members:
            self.members.setdefault(m.bundle_id, []).append(m.member_id)

        aliases: dict[str, list[str]] = {}
        for a in ck.aliases:
            if not a.is_primary:
                aliases.setdefault(a.ingredient_id, []).append(a.alias)
        has_source = {r.from_id for r in ck.relations if r.type == "derived_from"}
        # 재료 노드 정보용: 기본 그룹 closure(묶음은 구성원의 합이라 중복)
        base_hits: dict[str, list[dict[str, str]]] = {}
        for c in ck.allergen_closure:
            if self.groups[c.allergen_group_id].kind == "base":
                base_hits.setdefault(c.ingredient_id, []).append({"group": ag(c.allergen_group_id), "certainty": c.certainty})

        self._knowledge_nodes: list[dict[str, Any]] = []
        for g in ck.allergen_groups:
            self._knowledge_nodes.append({
                "id": ag(g.id), "kind": "allergen_group", "layer": 1, "name": g.display_name,
                "group_kind": g.kind, "category": self.group_category(g.id), "official": g.official,
                "members": [ag(m) for m in sorted(self.members.get(g.id, []))],
                "status": g.status, "confidence": g.confidence,
            })
        for i in ck.ingredients:
            self._knowledge_nodes.append({
                "id": ing(i.id), "kind": "ingredient", "layer": 3 if i.id in has_source else 2, "name": i.name,
                "category": i.category, "is_concept": i.kind == "concept", "is_processed": i.is_processed,
                "is_pantry_staple": i.is_pantry_staple, "status": i.status, "confidence": i.confidence,
                "aliases": sorted(aliases.get(i.id, [])), "allergens": base_hits.get(i.id, []),
            })

        self._knowledge_links: list[dict[str, Any]] = []
        for r in ck.relations:
            if r.type == "is_a":
                self._knowledge_links.append({"id": isa_link(r.from_id, r.to_id), "source": ing(r.from_id),
                                              "target": ing(r.to_id), "type": "is_a"})
            elif r.type == "derived_from":
                self._knowledge_links.append({"id": der_link(r.from_id, r.to_id), "source": ing(r.from_id),
                                              "target": ing(r.to_id), "type": "derived_from", "certainty": r.certainty})
        for a in ck.ingredient_allergens:
            self._knowledge_links.append({"id": alg_link(a.ingredient_id, a.allergen_group_id),
                                          "source": ing(a.ingredient_id), "target": ag(a.allergen_group_id),
                                          "type": "allergen", "certainty": a.certainty})
        for m in ck.group_members:
            self._knowledge_links.append({"id": mem_link(m.bundle_id, m.member_id), "source": ag(m.bundle_id),
                                          "target": ag(m.member_id), "type": "bundle_member"})
        self._cache: dict[tuple[str, int | None], tuple[dict[str, Any], str]] = {}

        # trace 표시용 조회 색인(요청 중 그래프 탐색 없이 링크 id를 찾는다)
        self._link_ids = {lk["id"] for lk in self._knowledge_links}
        self._lines: dict[tuple[str, str], list[int]] = {}  # (레시피, 재료) → line_no
        for r in data.recipes:
            for n, line in enumerate(r.ingredients, start=1):
                if line.ingredient is not None:
                    self._lines.setdefault((r.id, line.ingredient), []).append(n)
        self._closure = {(c.allergen_group_id, c.ingredient_id): c for c in ck.allergen_closure}
        self._isa = {(r.from_id, r.to_id) for r in ck.relations if r.type == "is_a"}

    def group_category(self, group_id: str) -> str:
        g = self.groups[group_id]
        if g.kind == "bundle":
            return "bundle"
        return "official" if g.official else "custom"

    def graph(self, recipes: RecipeScope = "published", max_recipes: int | None = None) -> tuple[dict[str, Any], str]:
        """(응답 본문, ETag). 같은 인자면 처음 만든 결과를 그대로 돌려준다."""
        key = (recipes, max_recipes)
        if key not in self._cache:
            body = self._build(recipes, max_recipes)
            blob = json.dumps(body, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self._cache[key] = (body, '"' + hashlib.sha256(blob).hexdigest()[:20] + '"')
        return self._cache[key]

    def _build(self, scope: RecipeScope, max_recipes: int | None) -> dict[str, Any]:
        specs = [] if scope == "none" else [r for r in self.data.recipes if scope == "all" or r.status == "published"]
        if max_recipes is not None:
            specs = specs[:max_recipes]
        nodes = list(self._knowledge_nodes)
        links = list(self._knowledge_links)
        for r in specs:
            nodes.append({
                "id": rcp(r.id), "kind": "recipe", "layer": 4, "name": r.title, "cuisine": r.cuisine,
                "difficulty": r.difficulty, "cook_time_min": r.cook_time_min,
                "spicy": r.taste.spicy if r.taste else 0, "status": r.status, "confidence": r.confidence,
                "required_equipment": sorted(e.name for e in r.equipment if e.required),
                "has_unmapped": any(line.ingredient is None for line in r.ingredients),
            })
            for n, line in enumerate(r.ingredients, start=1):  # line_no는 엔진 recipe_from_spec과 같은 번호
                if line.ingredient is None:
                    continue
                links.append({"id": use_link(r.id, n), "source": rcp(r.id), "target": ing(line.ingredient),
                              "type": "uses", "role": line.role, "optional": line.optional, "line_no": n})
        return {
            "knowledge_hash": self.data.knowledge.source_hash,
            "layers": list(LAYERS),
            "nodes": nodes,
            "links": links,
            "stats": {"nodes": len(nodes), "links": len(links), "recipes": len(specs)},
        }

    # --- trace 표시(부록 D-3) -------------------------------------------------------------------------

    def pair_link(self, a: str, b: str) -> str | None:
        """via의 연속 두 재료를 잇는 링크 id. contains·closure 경로는 is_a 위·아래, derived_from 원천 방향으로만 움직인다."""
        for link in (isa_link(a, b), isa_link(b, a), der_link(a, b)):
            if link in self._link_ids:
                return link
        return None

    def via_links(self, via: tuple[str, ...]) -> list[str]:
        return [x for x in (self.pair_link(a, b) for a, b in zip(via, via[1:])) if x]

    def source_group(self, target: str, ingredient_id: str, via: tuple[str, ...]) -> str:
        """묶음 그룹으로 제외되었을 때 실제로 걸린 기본 그룹(컴파일된 closure 행 조회). 기본 그룹이면 그대로."""
        if self.groups[target].kind != "bundle":
            return target
        members = sorted(self.members.get(target, []))
        same = [m for m in members if (row := self._closure.get((m, ingredient_id))) and row.via == via]
        hit = same or [m for m in members if (m, ingredient_id) in self._closure]
        return hit[0] if hit else target

    def exclusion(self, e: Exclusion, labels: dict[str, str]) -> dict[str, Any]:
        out: dict[str, Any] = {
            "recipe": rcp(e.recipe_id), "reason": e.reason.value, "label": labels.get(e.reason.value, e.reason.value),
            "ingredient": ing(e.ingredient_id) if e.ingredient_id else None, "target": e.target, "target_node": None,
            "source_group": None, "certainty": e.certainty, "via": [ing(x) for x in e.via], "path_links": [],
            "detail": e.detail,
        }
        uses = [use_link(e.recipe_id, n) for n in self._lines.get((e.recipe_id, e.ingredient_id or ""), [])]
        if e.reason == ExclusionReason.ALLERGEN and e.target and e.ingredient_id:
            base = self.source_group(e.target, e.ingredient_id, e.via)
            out["target_node"], out["source_group"] = ag(e.target), ag(base)
            path = [alg_link(e.via[-1], base)] if e.via else []
            if base != e.target:
                path.insert(0, mem_link(e.target, base))
            out["path_links"] = path + list(reversed(self.via_links(e.via))) + uses
        elif e.reason == ExclusionReason.HARD_DISLIKE_INGREDIENT and e.target:
            out["target_node"] = ing(e.target)
            out["path_links"] = list(reversed(self.via_links(e.via))) + uses
        elif e.reason == ExclusionReason.UNMAPPED_INGREDIENT:
            out["path_links"] = uses
        return out

    def trace(self, result: RecommendResult, t: RecommendTrace, *, weights: dict[str, float],
              labels: dict[str, str], limit: int) -> dict[str, Any]:
        """엔진 trace → 화면 데이터. 판정은 하지 않고 id 접두어, 링크 id, 라벨만 붙인다."""
        from_pantry = set(t.pantry) | {a for a, srcs in t.owned_from.items() if any(s in t.pantry for s in srcs)}
        owned: list[dict[str, Any]] = [{"node": ing(i), "because": "pantry", "from": []} for i in sorted(t.pantry)]
        owned += [{"node": ing(i), "because": "staple", "from": []}
                  for i in sorted(t.pantry_staples - t.pantry)]
        seen = set(t.pantry) | set(t.pantry_staples)
        owned += [{"node": ing(a), "because": "ancestor", "from": [ing(s) for s in srcs]}
                  for a, srcs in t.owned_from.items() if a not in seen]
        all_owned = seen | set(t.owned_from)
        owned_links = sorted(isa_link(c, p) for c, p in self._isa if c in all_owned and p in all_owned)

        candidates = []
        for c in t.candidates:
            lines = []
            for m in c.lines:
                iid = m.line.ingredient_id
                basis = m.line.role in CANDIDATE_ROLES and (
                    m.status == "substitute" or (m.status == "owned" and iid in from_pantry))
                lines.append({
                    "line_no": m.line.line_no, "node": ing(iid) if iid else None, "role": m.line.role,
                    "optional": m.line.optional, "status": m.status, "basis": basis,
                    "use": ing(m.substitute.to_id) if m.substitute else None,
                    "link": use_link(c.recipe.id, m.line.line_no) if iid else None,
                })
            candidates.append({"recipe": rcp(c.recipe.id), "lines": lines})

        excluded: dict[str, str] = {}
        for e in sorted(result.exclusions, key=lambda e: REASON_PRIORITY.index(e.reason)):
            excluded.setdefault(rcp(e.recipe_id), e.reason.value)

        score_rank = {s.candidate.recipe.id: n for n, s in enumerate(t.ranked, start=1)}
        scored = []
        for n, s in enumerate(t.ordered, start=1):
            rid = s.candidate.recipe.id
            scored.append({
                "recipe": rcp(rid), "score": round(s.score, 3),
                "breakdown": {k: round(v, 3) for k, v in s.breakdown.items()},
                "weighted": {k: round(weights[k] * s.breakdown[k], 3) for k in COMPONENTS},
                "score_rank": score_rank[rid], "final_rank": n, "moved_by_diversity": score_rank[rid] != n,
                "shown": n <= limit,
            })

        return {
            "user": {"allergen_groups": [ag(g) for g in t.allergen_groups],
                     "hard_dislikes": [ing(i) for i in t.hard_ingredients],
                     "spicy_max": t.spicy_max, "max_time_min": t.max_time_min},
            "pantry": {"input": [ing(i) for i in sorted(t.pantry)], "staples": [ing(i) for i in sorted(t.pantry_staples)],
                       "owned": owned, "owned_links": owned_links},
            "candidates": candidates,
            "exclusions": [self.exclusion(e, labels) for e in result.exclusions],
            "excluded": excluded,
            "scored": scored,
            "weights": dict(weights),
            "limit": limit,
        }
