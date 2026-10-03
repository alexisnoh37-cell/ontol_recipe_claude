"""kb 컴파일 결과를 엔진 입력으로 바꾸는 테스트용 연결부(변환 본체는 storage/engine_source.py).

tests/allergy/는 사람 승인 후 수정 금지다. 엔진 내부 구성(설정 로딩 등)이 바뀌면
알레르기 테스트가 아니라 이 파일을 고친다. 이 파일을 고쳐 테스트가 약해지면 안 된다.
"""

from __future__ import annotations

from collections.abc import Iterable

from engine.model import Recipe
from engine.recommend import Recommender
from kb import CompiledKnowledge
from kb.datacheck import check_recipes
from storage import engine_source
from storage.engine_source import CONFIG_DIR, recipe_from_spec, snapshot_from_compiled

__all__ = ["CONFIG_DIR", "build_recommender", "recipe_from_spec", "recipe_load_issue_codes", "snapshot_from_compiled"]


def build_recommender(
    ck: CompiledKnowledge, recipes: Iterable[Recipe], *, serve_draft_recipes: bool = False
) -> Recommender:
    """실제 config/(weights.yaml, engine.yaml)를 읽는다. 테스트는 draft 제공 여부를 명시적으로 정한다(기본 False).

    변환·조립은 storage.engine_source(API·골든셋·벤치와 같은 함수)를 그대로 쓴다.
    """
    return engine_source.build_recommender(ck, recipes, serve_draft_recipes=serve_draft_recipes)


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
