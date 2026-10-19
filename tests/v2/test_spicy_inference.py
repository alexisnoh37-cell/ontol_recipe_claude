"""맛 정보가 없는 레시피의 매운맛 추정(engine/v2/spicy.py, decisions D9)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from engine.model import Recipe, RecipeIngredient, TastePreference, UserContext
from engine.v2.config import load_v2_config
from engine.v2.model import V2Request
from engine.v2.recommend import RecommenderV2
from engine.v2.spicy import inferred_not_spicy
from storage.engine_source import load_files, snapshot_from_compiled
from tests.support.engine_fixtures import CONFIG_DIR, build_recommender

MARKERS = frozenset({"gochujang", "kimchi"})
TITLE_MARKERS = ("매콤", "고추")


def unknown(id: str, title: str, *lines: tuple) -> Recipe:
    """맛·난이도·조리시간을 모르는 레시피(식품안전나라처럼). lines: (재료 id 또는 None, role[, optional])."""
    return Recipe(id=id, title=title, cuisine="미분류", difficulty=None, cook_time_min=None, taste=None,
                  ingredients=tuple(RecipeIngredient(n, line[0], line[1], line[2] if len(line) > 2 else False,
                                                     line[0] or "비법 소스")
                                    for n, line in enumerate(lines, start=1)))


MILD = unknown("u_mild", "감자 소금구이", ("potato", "main"), ("salt", "seasoning"))
GOCHUJANG = unknown("u_gochujang", "감자 조림", ("potato", "main"), ("gochujang", "seasoning"))
KIMCHI_SAUCE = unknown("u_kimchi_sauce", "감자볶음", ("potato", "main"), ("kimchi_sauce", "seasoning"))  # 김치 파생
OPTIONAL_GOCHUJANG = unknown("u_opt", "감자전", ("potato", "main"), ("gochujang", "seasoning", True))
UNMAPPED = unknown("u_unmapped", "버섯구이", ("mushroom", "main"), (None, "seasoning"))
TITLE = unknown("u_title", "매콤 감자구이", ("potato", "main"), ("salt", "seasoning"))
RECIPES = [MILD, GOCHUJANG, KIMCHI_SAUCE, OPTIONAL_GOCHUJANG, UNMAPPED, TITLE]


@pytest.fixture(scope="module")
def snapshot(compiled):
    return snapshot_from_compiled(compiled)


@pytest.mark.parametrize(("recipe", "expected"), [
    (MILD, True),
    (GOCHUJANG, False),
    (KIMCHI_SAUCE, False),  # 포함(파생) 관계로 걸림
    (OPTIONAL_GOCHUJANG, False),  # 선택 재료도 본다
    (UNMAPPED, False),  # 미매칭 줄이 있으면 모른다
    (TITLE, False),  # 제목에 매운 말
], ids=lambda x: x.id if isinstance(x, Recipe) else str(x))
def test_inference_rule(snapshot, recipe, expected):
    assert inferred_not_spicy(snapshot, recipe, MARKERS, TITLE_MARKERS) is expected


def test_known_taste_is_never_inferred(snapshot):
    from engine.model import Taste

    assert not inferred_not_spicy(snapshot, replace(MILD, taste=Taste(spicy=3)), MARKERS, TITLE_MARKERS)


def make(compiled, enabled=True):
    cfg = replace(load_v2_config(CONFIG_DIR), spicy_inference_enabled=enabled, spicy_markers=MARKERS,
                  spicy_title_markers=TITLE_MARKERS)
    return RecommenderV2.from_v1(build_recommender(compiled, RECIPES, serve_draft_recipes=True), cfg)


NO_SPICY = UserContext(tastes=(TastePreference("spicy", preferred_level=0, max_level=0),),
                       pantry=frozenset({"potato", "mushroom"}))


def got(v2, user=NO_SPICY):
    r = v2.recommend(user, V2Request("random", seed=1, limit=20, rerank=False))
    return {i.item.recipe_id: i for i in r.items}


def test_spicy_limit_user_gets_inferred_mild_only(compiled):
    items = got(make(compiled))
    assert set(items) == {"u_mild"}
    assert "spicy_inferred" in items["u_mild"].notes


def test_disabled_keeps_old_rule(compiled):
    assert got(make(compiled, enabled=False)) == {}


def test_no_spicy_preference_no_note(compiled):
    items = got(make(compiled), UserContext())
    assert set(items) == {r.id for r in RECIPES}
    assert all("spicy_inferred" not in i.notes for i in items.values())


def test_taste_score_uses_inferred_zero(compiled):
    item = got(make(compiled))["u_mild"]
    assert item.item.breakdown["T"] == 1.0  # 선호 매운맛 0, 추정 0
    hot = UserContext(tastes=(TastePreference("spicy", preferred_level=5),))
    assert got(make(compiled), hot)["u_mild"].item.breakdown["T"] == 0.0


def test_dish_keyword_uses_inferred_zero(compiled):
    r = make(compiled).recommend(UserContext(), V2Request("dish", query="순한 감자", limit=20, rerank=False))
    order = [i.item.recipe_id for i in r.items]
    assert order.index("u_mild") < order.index("u_gochujang")


def test_real_markers_exist_in_knowledge():
    data = load_files()
    known = {i.id for i in data.knowledge.ingredients}
    cfg = load_v2_config(CONFIG_DIR)
    assert cfg.spicy_inference_enabled and cfg.spicy_markers
    assert cfg.spicy_markers <= known, sorted(cfg.spicy_markers - known)
