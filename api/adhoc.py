"""외부 레시피 일회성 분석 (docs/plan.md 부록 E).

AI가 만든 레시피처럼 DB에 없는 레시피의 재료 원문을 정규 재료 id로 매핑하고, 컴파일된 지식(별칭 색인, ancestors,
derived_from 행, 기본 그룹 allergen_closure)을 조회해 재료·알레르기 구조를 돌려준다. 저장하지 않는다.

  - 재료 줄 분리는 식품안전나라 변환과 같은 결정적 규칙(kb.foodsafety.ingredient_segments). 버린 항목은 응답에 남긴다.
  - 매핑은 별칭 색인 정확 일치만(LLM·유사도 없음). concept 노드에 맞은 줄은 레시피 재료로 쓸 수 없어 미매칭과 같이 다룬다(A1).
  - 사용자를 주면 임시 Recipe를 만들어 엔진의 UserConstraints.check로 판정한다(추천 필터와 같은 기준).
  - 겹쳐 그릴 그래프 노드·간선은 GET /graph와 같은 모양이다. 미매칭 줄은 온톨로지에 연결되지 않은 노드로 둔다.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Literal

from api.viz import GraphCatalog, ag, ing, rcp, use_link
from engine.filters import UserConstraints
from engine.model import Exclusion, KnowledgeSnapshot, Recipe, RecipeIngredient, RecommendRequest, UserContext
from kb.foodsafety import ingredient_name, ingredient_segments
from kb.text import normalize_term

LineStatus = Literal["mapped", "concept", "unmapped"]

ADHOC_CUISINE = "외부 입력"
ADHOC_ROLE = "sub"  # 원문에서 역할을 추론하지 않는다. 알레르기 판정은 역할과 무관하게 모든 줄을 본다
CHECKED = ("알레르기", "미매칭 재료", "절대 불선호 재료")
NOT_CHECKED = ("매운맛 한도", "조리기구", "조리시간", "음식 종류")


@dataclass(frozen=True)
class AdhocLine:
    line_no: int
    raw_text: str
    name: str
    status: LineStatus
    ingredient_id: str | None  # mapped일 때만
    concept_id: str | None  # concept일 때만


def recipe_id(title: str, text: str) -> str:
    """같은 입력이면 같은 id(화면이 이전 겹쳐 보기를 알아보고, 제외 로그를 묶어 볼 수 있게)."""
    digest = hashlib.sha256(f"{title}\n{text}".encode()).hexdigest()[:10]
    return f"adhoc_{digest}"


def parse_lines(snapshot: KnowledgeSnapshot, title: str, text: str) -> tuple[list[AdhocLine], list[str]]:
    """재료 원문 → (줄 목록, 버린 항목). 이름 → 원문 전체 순으로 별칭 색인 정확 일치를 찾는다."""
    skipped: list[str] = []
    lines: list[AdhocLine] = []
    for n, seg in enumerate(ingredient_segments(text, title, skipped), start=1):
        name = ingredient_name(seg)
        found = None
        for key in (normalize_term(name), normalize_term(seg)):
            found = snapshot.alias_index.get(key)
            if found is not None:
                break
        if found is None:
            lines.append(AdhocLine(n, seg, name, "unmapped", None, None))
        elif found in snapshot.concept_ids:
            lines.append(AdhocLine(n, seg, name, "concept", None, found))
        else:
            lines.append(AdhocLine(n, seg, name, "mapped", found, None))
    return lines, skipped


def to_recipe(rid: str, title: str, lines: list[AdhocLine]) -> Recipe:
    """엔진 필터에 넣을 임시 레시피. concept·미매칭 줄은 ingredient_id None(미매칭)이다."""
    return Recipe(
        id=rid, title=title, cuisine=ADHOC_CUISINE, difficulty=1, cook_time_min=0,
        ingredients=tuple(RecipeIngredient(line.line_no, line.ingredient_id, ADHOC_ROLE, False, line.raw_text)
                          for line in lines),
    )


def raw_node(rid: str, line_no: int) -> str:
    return f"raw:{rid}#{line_no}"


def unmapped_link(rid: str, line_no: int) -> str:
    return f"unm:{rid}#{line_no}"


def analyze(graph: GraphCatalog, snapshot: KnowledgeSnapshot, *, title: str, text: str,
            user: UserContext | None, exclusion_labels: dict[str, str]) -> tuple[dict[str, Any], list[Exclusion]]:
    """(응답 본문, 제외 기록). 재료를 하나도 찾지 못하거나 모르는 알레르기 그룹·재료면 ValueError."""
    lines, skipped = parse_lines(snapshot, title, text)
    if not lines:
        raise ValueError("재료를 찾지 못했습니다. 재료를 줄이나 쉼표로 나눠 적어 주세요.")
    rid = recipe_id(title, text)
    names = snapshot.ingredient_names
    group_name = {g: graph.groups[g].display_name for g in graph.groups}

    def ingredient_ref(i: str) -> dict[str, Any]:
        return {"id": i, "name": names.get(i, i), "node": ing(i)}

    out_lines = []
    for line in lines:
        item: dict[str, Any] = {
            "line_no": line.line_no, "raw_text": line.raw_text, "name": line.name, "status": line.status,
            "ingredient": ingredient_ref(line.ingredient_id) if line.ingredient_id else None,
            "concept": ingredient_ref(line.concept_id) if line.concept_id else None,
            "is_a": [], "derived_from": [], "allergens": [],
        }
        if line.ingredient_id:
            iid = line.ingredient_id
            ancestors = snapshot.ancestors.get(iid, {})
            item["is_a"] = [{**ingredient_ref(a), "depth": d}
                            for a, d in sorted(ancestors.items(), key=lambda x: (x[1], x[0])) if a != iid]
            item["derived_from"] = [{**ingredient_ref(s), "certainty": c} for s, c in graph.sources.get(iid, [])]
            item["allergens"] = [{**hit, "group_id": hit["group"][3:], "group_name": group_name[hit["group"][3:]]}
                                 for hit in graph.base_hits.get(iid, [])]
        out_lines.append(item)

    allergens = graph.lines_allergens((line.line_no, line.ingredient_id, ADHOC_ROLE, False) for line in lines)
    counts = {
        "lines": len(lines),
        "mapped": sum(1 for line in lines if line.status == "mapped"),
        "concept": sum(1 for line in lines if line.status == "concept"),
        "unmapped": sum(1 for line in lines if line.status == "unmapped"),
    }

    judgement = None
    exclusions: list[Exclusion] = []
    if user is not None:
        constraints = UserConstraints(snapshot, user, RecommendRequest())  # 모르는 그룹·재료면 ValueError
        exclusions = constraints.check(to_recipe(rid, title, lines))
        index: dict[tuple[str, str], list[int]] = {}
        for line in lines:
            if line.ingredient_id:
                index.setdefault((rid, line.ingredient_id), []).append(line.line_no)
        rendered = []
        for e in exclusions:
            row = graph.exclusion(e, exclusion_labels, lines=index)
            if e.ingredient_id is None:  # 미매칭 줄: 원문으로 해당 줄의 미매칭 노드·간선을 가리킨다
                row["lines"] = [line.line_no for line in lines
                                if line.ingredient_id is None and f"미매칭 재료: {line.raw_text}" == e.detail]
                row["path_links"] = [unmapped_link(rid, n) for n in row["lines"]]
            rendered.append(row)
        judgement = {
            "excluded": bool(exclusions),
            "allergen_groups": [{"id": g, "name": group_name.get(g, g), "node": ag(g)}
                                for g in constraints.allergen_groups],
            "hard_dislikes": [ingredient_ref(i) for i in constraints.hard_ingredients],
            "exclusions": rendered,
            "checked": list(CHECKED),
            "not_checked": list(NOT_CHECKED),
        }

    notice = []
    if counts["unmapped"] or counts["concept"]:
        notice.append("정규 재료에 매핑되지 않은 줄은 알레르기를 판정하지 못했습니다. 알레르기가 있는 사용자에게는 "
                      "이 레시피가 제외됩니다(안전 규칙). 분류(concept)에 맞은 줄은 더 구체적인 재료로 적어 주세요.")
    notice.append("저장하지 않는 일회성 분석입니다. 역할(주재료·양념 등)과 선택 재료 여부는 추론하지 않습니다.")

    return {
        "recipe_id": rid,
        "title": title,
        "lines": out_lines,
        "skipped": skipped,
        "allergens": [{**a, "group_id": a["group"][3:], "group_name": group_name[a["group"][3:]]} for a in allergens],
        "counts": counts,
        "judgement": judgement,
        "graph": overlay(rid, title, lines, allergens),
        "notice": notice,
    }, exclusions


def overlay(rid: str, title: str, lines: list[AdhocLine], allergens: list[dict[str, Any]]) -> dict[str, Any]:
    """기존 그래프 위에 겹쳐 그릴 노드·간선. 레시피 노드는 4층(kind recipe, adhoc), 미매칭 줄은 연결 없는 노드."""
    node = rcp(rid)
    nodes: list[dict[str, Any]] = [{
        "id": node, "kind": "recipe", "layer": 4, "name": title, "cuisine": ADHOC_CUISINE, "adhoc": True,
        "difficulty": None, "cook_time_min": None, "spicy": None, "status": "adhoc", "confidence": None,
        "required_equipment": [], "has_unmapped": any(line.ingredient_id is None for line in lines),
        "allergens": allergens,
    }]
    links: list[dict[str, Any]] = []
    for line in lines:
        if line.ingredient_id:
            links.append({"id": use_link(rid, line.line_no), "source": node, "target": ing(line.ingredient_id),
                          "type": "uses", "role": ADHOC_ROLE, "optional": False, "line_no": line.line_no})
            continue
        nodes.append({
            "id": raw_node(rid, line.line_no), "kind": "unmapped", "layer": 4, "name": line.name,
            "raw_text": line.raw_text, "line_no": line.line_no,
            "concept": ing(line.concept_id) if line.concept_id else None, "allergens": [],
        })
        links.append({"id": unmapped_link(rid, line.line_no), "source": node, "target": raw_node(rid, line.line_no),
                      "type": "unmapped", "line_no": line.line_no})
    return {"nodes": nodes, "links": links}
