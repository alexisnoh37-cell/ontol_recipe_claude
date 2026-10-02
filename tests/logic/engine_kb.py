"""tests/logic 엔진 단위 테스트용 작은 지식과 레시피. 지식은 kb.compile을 통과시켜 만든다."""

from __future__ import annotations

from engine.model import Recipe, RecipeIngredient, Taste
from kb import CompiledKnowledge, compile
from tests.support.kb_builders import ing, sources

INGREDIENTS = [
    ing("meat", name="육류", kind="concept"),
    ing("pork", name="돼지고기", is_a=["meat"]),
    ing("pork_belly", name="삼겹살", is_a=["pork"]),
    ing("onion", name="양파"),
    ing("tofu", name="두부"),
    ing("egg", name="계란", aliases=["달걀"], allergens=[{"group": "egg", "certainty": "definite"}]),
    ing("garlic", name="마늘", aliases=["다진 마늘"]),
    ing("milk", name="우유", allergens=[{"group": "milk", "certainty": "definite"}]),
    ing("butter", name="버터", derived_from=["milk"], is_processed=True),
    ing("cooking_oil", name="식용유"),
    ing("salt", name="소금"),
]

SUBSTITUTES = [{"from": "cooking_oil", "to": "butter", "context": ["볶음"], "status": "draft"}]


def compile_logic_kb() -> CompiledKnowledge:
    return compile(sources(INGREDIENTS, substitutes=SUBSTITUTES, staples=["salt", "garlic"]))


def recipe(id: str, *lines: tuple, cuisine: str = "한식", spicy: int = 0, equipment: tuple[str, ...] = (),
           techniques: tuple[str, ...] = (), cook_time_min: int = 20) -> Recipe:
    """lines: (재료 id 또는 None, role[, optional])"""
    ingredients = tuple(
        RecipeIngredient(n, line[0], line[1], line[2] if len(line) > 2 else False, line[0] or "미상 재료")
        for n, line in enumerate(lines, start=1)
    )
    return Recipe(id=id, title=id, cuisine=cuisine, difficulty=1, cook_time_min=cook_time_min,
                  ingredients=ingredients, taste=Taste(spicy=spicy), required_equipment=frozenset(equipment),
                  techniques=frozenset(techniques))
