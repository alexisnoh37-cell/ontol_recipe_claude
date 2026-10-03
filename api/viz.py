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

from storage.engine_source import EngineData

RecipeScope = Literal["none", "published", "all"]

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
