"""레시피 시드(data/recipes/) 검사: 형식·어휘 검증, 구성, 검수표 최신 여부, 알레르기 스모크.

1-3 검수 완료 50개(published) + 1차 확장(2026-10-04) 초안(draft). 개수는 시드에서 센다.
"""

from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

import pytest

from engine.model import ExclusionReason, RecommendRequest, UserContext
from kb import compile_paths
from kb.recipes import RecipeSeedError, load_recipe_specs, read_recipe_dir
from tests.support.engine_fixtures import build_recommender, recipe_from_spec

ROOT = Path(__file__).resolve().parents[2]
RECIPES_DIR = ROOT / "data" / "recipes"


@pytest.fixture(scope="module")
def ck():
    return compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")


@pytest.fixture(scope="module")
def specs(ck):
    return load_recipe_specs(ck, RECIPES_DIR, ROOT)


@pytest.fixture(scope="module")
def recommender(ck, specs):
    return build_recommender(ck, [recipe_from_spec(s) for s in specs])


# 1-3에서 사람이 검수해 published로 바꾼 레시피(2026-10-03). 검수로 published가 늘면 이 목록에 추가한다.
PUBLISHED_IDS = frozenset({
    "aglio_olio", "beef_steak", "bibimbap", "bok_choy_stirfry", "budae_jjigae", "bulgogi", "cheese_omelet", "cream_pasta",
    "dakbokkeumtang", "doenjang_jjigae", "dubu_jorim", "egg_fried_rice", "eomuk_bokkeum", "galbijjim", "gamja_jorim",
    "gamjajeon", "gimbap", "gochu_japchae", "godeungeo_jorim", "gyeran_mari", "gyeranjjim", "gyudon", "haemul_pajeon",
    "hobakjeon", "janchi_guksu", "jangjorim", "japanese_curry", "japchae", "jeyuk_bokkeum", "jjajang_deopbap", "kake_udon",
    "kimchi_jjigae", "kimchijeon", "kongnamul_muchim", "mapo_tofu", "miso_soup", "miyeokguk", "musaengchae",
    "myeolchi_bokkeum", "ojingeo_bokkeum", "oyakodon", "potato_gratin", "salmon_don", "sigeumchi_namul", "sogogi_muguk",
    "tangsuyuk", "tomato_egg_stirfry", "tomato_pasta", "tonkatsu", "tteokbokki",
})


def test_seed_validates_without_issues(specs):
    # 개수는 시드 폴더에서 센다(파일 하나 = 레시피 하나). 검증 오류가 있으면 fixture에서 이미 실패한다.
    files = sorted(RECIPES_DIR.glob("*.yaml"))
    assert len(specs) == len(files) > len(PUBLISHED_IDS)
    assert {s.id for s in specs} == {f.stem for f in files}


def test_one_recipe_per_file_named_by_id():
    for where, item in read_recipe_dir(RECIPES_DIR, ROOT):
        assert Path(where).stem == item["id"], where


def test_cuisine_mix(specs):
    # 1-3 검수 완료분의 구성(한식 30·기타 20)은 그대로 유지한다. 전체 구성은 시드에서 센다.
    published = Counter(s.cuisine for s in specs if s.id in PUBLISHED_IDS)
    assert published["한식"] == 30
    assert sum(published.values()) - published["한식"] == 20
    counts = Counter(s.cuisine for s in specs)
    assert sum(counts.values()) == len(specs)
    assert {"한식", "일식", "양식", "중식"} <= set(published) <= set(counts)


def test_reviewed_recipes_stay_published(specs):
    # 1-3 사람 검수 완료(2026-10-03). 검수한 50개는 그대로 published여야 한다.
    by_id = {s.id: s for s in specs}
    assert PUBLISHED_IDS <= set(by_id), sorted(PUBLISHED_IDS - set(by_id))
    assert {by_id[i].status for i in PUBLISHED_IDS} == {"published"}
    assert {s.source for s in specs} == {"agent_draft"}


def test_published_recipes_have_required_fields(specs):
    published = [s for s in specs if s.status == "published"]
    assert {s.id for s in published} == PUBLISHED_IDS  # 검수 목록 밖의 published 금지(사람 승인 없이 바꾸지 않음)
    for s in published:
        assert s.taste is not None and s.difficulty is not None, s.id
        assert s.steps and s.cook_time_min > 0, s.id
        assert any(i.role == "main" and not i.optional for i in s.ingredients), s.id
        assert all(i.ingredient is not None for i in s.ingredients), s.id


def test_new_recipes_are_draft(specs):
    # 1차 확장(2026-10-04) 등 검수 전 레시피는 draft로 둔다. 사람이 검수표로 승인한 뒤에만 published.
    new = [s for s in specs if s.id not in PUBLISHED_IDS]
    assert new
    assert {s.status for s in new} == {"draft"}, sorted(s.id for s in new if s.status != "draft")


def test_review_fixes_1_3(specs):
    # 1-3 검수에서 선택 재료로 바꾼 것
    optional = {(s.id, i.ingredient) for s in specs for i in s.ingredients if i.optional}
    assert {("gyeranjjim", "saeujeot"), ("gyeran_mari", "carrot"), ("gyeran_mari", "green_onion"),
            ("doenjang_jjigae", "zucchini"), ("doenjang_jjigae", "potato"), ("kimchi_jjigae", "tofu")} <= optional


def test_every_recipe_is_complete(specs):
    for s in specs:
        assert s.taste is not None and s.difficulty is not None, s.id
        assert any(i.role == "main" and not i.optional for i in s.ingredients), f"{s.id}: 필수 주재료 없음"
        assert all(i.ingredient is not None for i in s.ingredients), f"{s.id}: 미매칭 재료"
        assert s.steps, s.id
        assert len({i.ingredient for i in s.ingredients}) == len(s.ingredients), f"{s.id}: 재료 중복"


def test_bad_seed_is_rejected(ck, tmp_path):
    (tmp_path / "bad.yaml").write_text(
        "id: bad\ntitle: 나쁜 예\ncuisine: 태국식\ncook_time_min: 10\nsource: test\n"
        "ingredients:\n  - {ingredient: seafood, raw_text: 해산물, role: main}\n", encoding="utf-8")
    with pytest.raises(RecipeSeedError) as exc:
        load_recipe_specs(ck, tmp_path)
    assert {i.code for i in exc.value.issues} == {"bad_vocab", "concept_usage"}


def test_review_table_is_up_to_date(ck, specs):
    spec = importlib.util.spec_from_file_location("make_recipe_review", ROOT / "scripts" / "make_recipe_review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    committed = (ROOT / "docs" / "review" / "recipes_review.md").read_text(encoding="utf-8")
    assert committed == module.render(ck, specs), "검수표가 최신이 아닙니다: uv run python scripts/make_recipe_review.py"


# --- 실제 시드 + 엔진 알레르기 스모크(기본 설정: published만 제공) ------------------------------------------------


ALL_PANTRY = frozenset({"kimchi", "egg", "pork_belly", "pasta", "tofu", "rice", "potato", "squid", "tomato_sauce", "scallion"})


@pytest.fixture(scope="module")
def recommender_with_drafts(ck, specs):
    return build_recommender(ck, [recipe_from_spec(s) for s in specs], serve_draft_recipes=True)


KIMCHI_LIKE = frozenset({"kimchi", "kkakdugi", "young_radish_kimchi"})


@pytest.mark.parametrize("serve_drafts", [False, True])
def test_kimchi_recipes_excluded_for_shrimp_allergy(recommender, recommender_with_drafts, specs, serve_drafts):
    """김치류가 들어간 모든 레시피(검수 전 draft 포함)가 새우 알레르기 사용자에게 제외된다."""
    engine = recommender_with_drafts if serve_drafts else recommender
    pool = [s for s in specs if serve_drafts or s.status == "published"]
    kimchi_recipes = {s.id for s in pool if any(i.ingredient in KIMCHI_LIKE for i in s.ingredients)}
    assert {"kimchi_jjigae", "kimchijeon", "budae_jjigae"} <= kimchi_recipes
    # 모든 김치 레시피가 후보가 되도록 그 main 재료를 보유로 넣는다(후보가 아니면 제외 기록이 남지 않음).
    mains = {i.ingredient for s in pool if s.id in kimchi_recipes for i in s.ingredients if i.role == "main"}
    result = engine.recommend(UserContext(allergen_groups=frozenset({"shrimp"}), pantry=ALL_PANTRY | mains),
                              RecommendRequest(limit=1000))
    served = {i.recipe_id for i in result.items}
    assert served and not served & (kimchi_recipes | {"gyeranjjim", "haemul_pajeon"})
    allergen = [e for e in result.exclusions if e.reason == ExclusionReason.ALLERGEN]
    assert kimchi_recipes <= {e.recipe_id for e in allergen if e.ingredient_id in KIMCHI_LIKE and e.target == "shrimp"}
    reasons = {(e.recipe_id, e.ingredient_id, e.certainty) for e in allergen}
    assert ("kimchi_jjigae", "kimchi", "possible") in reasons
    assert ("gyeranjjim", "saeujeot", "definite") in reasons
    assert ("haemul_pajeon", "shrimp_raw", "definite") in reasons  # 선택 재료여도 제외


def test_milk_allergy_excludes_optional_cheese(recommender):
    result = recommender.recommend(UserContext(allergen_groups=frozenset({"milk"}), pantry=ALL_PANTRY),
                                   RecommendRequest(limit=100))
    served = {i.recipe_id for i in result.items}
    assert not served & {"tomato_pasta", "cream_pasta", "potato_gratin", "cheese_omelet"}
    assert not any("검수 전 레시피입니다" in i.notes for i in result.items)


def test_published_seed_served_by_default(recommender, specs):
    result = recommender.recommend(UserContext(pantry=ALL_PANTRY), RecommendRequest(limit=100))
    assert len(result.items) >= 20
    drafts = {s.id for s in specs if s.status == "draft"}
    assert not {i.recipe_id for i in result.items} & drafts  # 기본 설정은 검수 전 레시피를 제공하지 않는다
