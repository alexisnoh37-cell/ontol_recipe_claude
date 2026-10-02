"""kb 컴파일 결과를 엔진 입력으로 바꾸는 테스트용 연결부.

tests/allergy/는 사람 승인 후 수정 금지다. 엔진 내부 구성(설정 로딩 등)이 바뀌면
알레르기 테스트가 아니라 이 파일을 고친다. 이 파일을 고쳐 테스트가 약해지면 안 된다.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from engine.config import load_engine_config
from engine.memory import InMemoryKnowledgeRepository, InMemoryRecipeRepository
from engine.model import AllergenHit, ContainsHit, KnowledgeSnapshot, Recipe, RecipeIngredient, Substitute, Taste
from engine.recommend import Recommender
from kb import CompiledKnowledge
from kb.datacheck import RecipeSpec, check_recipes

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"


def snapshot_from_compiled(ck: CompiledKnowledge) -> KnowledgeSnapshot:
    ancestors: dict[str, dict[str, int]] = {}
    for a in ck.ancestors:
        ancestors.setdefault(a.ingredient_id, {})[a.ancestor_id] = a.depth
    contains: dict[str, dict[str, ContainsHit]] = {}
    for c in ck.contains:
        contains.setdefault(c.ingredient_id, {})[c.contained_id] = ContainsHit(c.certainty, c.via)
    closure: dict[str, dict[str, AllergenHit]] = {g.id: {} for g in ck.allergen_groups}
    for r in ck.allergen_closure:
        closure[r.allergen_group_id][r.ingredient_id] = AllergenHit(r.certainty, r.via)
    substitutes: dict[str, list[Substitute]] = {}
    for r in ck.relations:
        if r.type == "substitute":
            substitutes.setdefault(r.from_id, []).append(Substitute(r.from_id, r.to_id, frozenset(r.context), r.ratio))
    return KnowledgeSnapshot(
        ingredient_names={i.id: i.name for i in ck.ingredients},
        alias_index={a.alias_norm: a.ingredient_id for a in ck.aliases},
        ancestors=ancestors,
        contains=contains,
        allergen_closure=closure,
        substitutes={k: tuple(v) for k, v in substitutes.items()},
        pantry_staples=frozenset(ck.pantry_staples),
        concept_ids=ck.concept_ids,
    )


def recipe_from_spec(spec: RecipeSpec) -> Recipe:
    """레시피 시드(RecipeSpec) → 엔진 Recipe. 1-5에서 API·DB 로더가 같은 변환을 쓰게 되면 위치를 옮긴다."""
    return Recipe(
        id=spec.id,
        title=spec.title,
        cuisine=spec.cuisine,
        difficulty=spec.difficulty or 1,
        cook_time_min=spec.cook_time_min,
        ingredients=tuple(
            RecipeIngredient(n, line.ingredient, line.role, line.optional, line.raw_text)
            for n, line in enumerate(spec.ingredients, start=1)
        ),
        taste=Taste(**spec.taste.model_dump()) if spec.taste else Taste(),
        required_equipment=frozenset(e.name for e in spec.equipment if e.required),
        techniques=frozenset(s.technique for s in spec.steps if s.technique),
        status=spec.status,
    )


def build_recommender(
    ck: CompiledKnowledge, recipes: Iterable[Recipe], *, serve_draft_recipes: bool = False
) -> Recommender:
    """실제 config/(weights.yaml, engine.yaml)를 읽는다. draft 제공 여부만 인자로 덮어쓴다."""
    return Recommender(
        InMemoryKnowledgeRepository(snapshot_from_compiled(ck)),
        InMemoryRecipeRepository(recipes),
        load_engine_config(CONFIG_DIR, serve_draft_recipes=serve_draft_recipes),
    )


def recipe_load_issue_codes(ck: CompiledKnowledge, recipe: Recipe) -> list[str]:
    """레시피를 적재 전 검증(scripts/validate_data.py와 같은 검사)에 통과시켰을 때의 오류 코드.

    레시피 시드 형식은 Phase 1-3에서 확정한다. 형식이 바뀌면 여기만 고친다.
    """
    seed = {
        "id": recipe.id,
        "title": recipe.title,
        "cuisine": recipe.cuisine,
        "difficulty": recipe.difficulty,
        "cook_time_min": recipe.cook_time_min,
        "source": "test",
        "status": recipe.status,
        "ingredients": [
            {"ingredient": line.ingredient_id, "raw_text": line.raw_text or str(line.ingredient_id),
             "role": line.role, "optional": line.optional}
            for line in recipe.ingredients
        ],
        "taste": {k: getattr(recipe.taste, k) for k in ("spicy", "salty", "sweet", "sour", "umami", "savory")},
    }
    return [issue.code for issue in check_recipes(ck, [(recipe.id, seed)])]
