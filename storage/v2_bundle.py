"""추천 v2를 다른 앱(다른 언어)으로 옮길 때 쓰는 데이터 묶음 (docs/integration/README.md, docs/integration/v2_logic_spec.md).

엔진이 판단에 쓰는 입력을 언어와 무관한 JSON으로 내보낸다. scripts/export_v2_bundle.py(실제 데이터)와
scripts/make_shared_cases.py(공용 시험 세트)가 같은 형식을 쓴다. 형식이 바뀌면 FORMAT_VERSION을 올린다.

  knowledge  컴파일된 지식(요청 처리 중 그래프 탐색 없이 조회만): 재료 이름, 별칭 색인, is_a 조상(깊이),
             포함 관계(certainty·경로), 알레르기 closure(certainty·경로), 대체재, 기본 양념, 분류(concept) 노드,
             알레르기 그룹 목록(이름·종류·묶음 구성)
  recipes    레시피(재료 줄·역할·선택 여부, 음식 종류, 난이도, 조리시간, 맛, 필수 조리기구, 조리 기법, 검수 상태)
  config     점수 가중치(config/weights.yaml), 엔진 옵션(config/engine.yaml), v2 설정(config/v2.yaml)
  derived    매운맛 추정 결과(맛 정보는 없지만 매운맛 0으로 보는 레시피 id, D9). 옮기는 쪽이 다시 계산해 맞춰 볼 수 있다
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from engine.model import KnowledgeSnapshot, Recipe

FORMAT_VERSION = 1
TASTE_KEYS = ("spicy", "salty", "sweet", "sour", "umami", "savory")


def knowledge_to_json(s: KnowledgeSnapshot, ck: Any = None) -> dict[str, Any]:
    """ck: kb CompiledKnowledge(알레르기 그룹 이름·종류·묶음 구성을 쓴다). 없으면 closure 키만으로 그룹 목록을 만든다."""
    members: dict[str, list[str]] = {}
    for m in getattr(ck, "group_members", ()) or ():
        members.setdefault(m.bundle_id, []).append(m.member_id)
    group_rows = [{"id": g.id, "name": g.display_name, "kind": g.kind, "members": sorted(members.get(g.id, []))}
                  for g in sorted(getattr(ck, "allergen_groups", ()) or (), key=lambda g: g.id)]
    return {
        "ingredient_names": dict(sorted(s.ingredient_names.items())),
        "alias_index": dict(sorted(s.alias_index.items())),
        "ancestors": {k: dict(sorted(v.items())) for k, v in sorted(s.ancestors.items()) if v},
        "contains": {k: {t: {"certainty": h.certainty, "via": list(h.via)} for t, h in sorted(v.items())}
                     for k, v in sorted(s.contains.items()) if v},
        "allergen_closure": {g: {i: {"certainty": h.certainty, "via": list(h.via)} for i, h in sorted(v.items())}
                             for g, v in sorted(s.allergen_closure.items())},
        "allergen_groups": group_rows or [{"id": g, "name": g, "kind": "base", "members": []}
                                          for g in sorted(s.allergen_closure)],
        "substitutes": {k: [{"to": x.to_id, "context": sorted(x.context), "ratio": x.ratio} for x in v]
                        for k, v in sorted(s.substitutes.items())},
        "pantry_staples": sorted(s.pantry_staples),
        "concept_ids": sorted(s.concept_ids),
        # 화면 표시용: 성분표 확인 안내(label_check = 가공품이면서 confidence low인 재료)와 분류
        "ingredient_meta": {i.id: {"category": i.category, "is_processed": bool(i.is_processed),
                                   "confidence": i.confidence}
                            for i in sorted(getattr(ck, "ingredients", ()) or (), key=lambda i: i.id)},
    }


def recipe_to_json(r: Recipe) -> dict[str, Any]:
    return {
        "id": r.id,
        "title": r.title,
        "cuisine": r.cuisine,
        "difficulty": r.difficulty,
        "cook_time_min": r.cook_time_min,
        "status": r.status,
        "taste": None if r.taste is None else {k: getattr(r.taste, k) for k in TASTE_KEYS},
        "required_equipment": sorted(r.required_equipment),
        "techniques": sorted(r.techniques),
        "ingredients": [{"line": line.line_no, "ingredient": line.ingredient_id, "role": line.role,
                         "optional": line.optional, "raw_text": line.raw_text} for line in r.ingredients],
    }


def config_to_json(weights: Mapping[str, Any], engine: Mapping[str, Any], v2: Mapping[str, Any],
                   display: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """display: config/display.yaml(면책 문구, 성분표 확인 문구, 레시피·재료별 안내, 시판 제품 안내). 판정과 무관한
    화면 문구지만 같은 안내를 보여 주려면 필요하다. v2의 display(항목 이름·안내 코드 문구)도 그대로 들어 있다."""
    out = {"weights": dict(weights), "engine": dict(engine), "v2": dict(v2)}
    if display is not None:
        out["display"] = dict(display)
    return out


def dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=False) + "\n"


def write_files(out_dir: Path, files: Mapping[str, Any], meta: Mapping[str, Any]) -> dict[str, Any]:
    """files: 파일 이름 → JSON 객체. manifest.json에 형식 버전·메타·파일별 SHA-256을 쓴다(줄바꿈 LF, UTF-8)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, obj in files.items():
        data = dumps(obj).encode("utf-8")
        (out_dir / name).write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    manifest = {"format_version": FORMAT_VERSION, **meta, "files": hashes}
    (out_dir / "manifest.json").write_bytes(dumps(manifest).encode("utf-8"))
    return manifest


# --- 읽기(공용 시험 세트를 Python 엔진으로 다시 돌릴 때, 옮기는 쪽의 참고 구현) ---------------------------------


def knowledge_from_json(k: Mapping[str, Any]) -> KnowledgeSnapshot:
    from engine.model import AllergenHit, ContainsHit, Substitute

    return KnowledgeSnapshot(
        ingredient_names=dict(k["ingredient_names"]),
        alias_index=dict(k["alias_index"]),
        ancestors={i: {a: int(d) for a, d in v.items()} for i, v in k["ancestors"].items()},
        contains={i: {t: ContainsHit(h["certainty"], tuple(h["via"])) for t, h in v.items()}
                  for i, v in k["contains"].items()},
        allergen_closure={g: {i: AllergenHit(h["certainty"], tuple(h["via"])) for i, h in v.items()}
                          for g, v in k["allergen_closure"].items()},
        substitutes={need: tuple(Substitute(need, x["to"], frozenset(x["context"]), x["ratio"]) for x in v)
                     for need, v in k["substitutes"].items()},
        pantry_staples=frozenset(k["pantry_staples"]),
        concept_ids=frozenset(k["concept_ids"]),
    )


def recipe_from_json(r: Mapping[str, Any]) -> Recipe:
    from engine.model import RecipeIngredient, Taste

    return Recipe(
        id=r["id"], title=r["title"], cuisine=r["cuisine"], difficulty=r["difficulty"],
        cook_time_min=r["cook_time_min"], status=r["status"],
        taste=None if r["taste"] is None else Taste(**r["taste"]),
        required_equipment=frozenset(r["required_equipment"]), techniques=frozenset(r["techniques"]),
        ingredients=tuple(RecipeIngredient(x["line"], x["ingredient"], x["role"], x["optional"], x["raw_text"])
                          for x in r["ingredients"]),
    )


def recommender_from_json(knowledge: Mapping[str, Any], recipes: Iterable[Mapping[str, Any]],
                          config: Mapping[str, Any], *, judge: Any = None, reranker: Any = None):
    """JSON 묶음만으로 RecommenderV2를 조립한다(파일이 스스로 완결되어 있는지 확인하는 데도 쓴다)."""
    from engine.config import EngineConfig
    from engine.memory import InMemoryKnowledgeRepository, InMemoryRecipeRepository
    from engine.v2.config import V2Config
    from engine.v2.recommend import RecommenderV2

    eng = config["engine"]
    engine_config = EngineConfig(weights=config["weights"], serve_draft_recipes=bool(eng.get("serve_draft_recipes")),
                                 browse_max_missing=int(eng.get("browse_max_missing", 2)))
    return RecommenderV2(InMemoryKnowledgeRepository(knowledge_from_json(knowledge)),
                         InMemoryRecipeRepository(recipe_from_json(r) for r in recipes), engine_config,
                         V2Config.from_mapping(config["v2"]), reranker, judge)
