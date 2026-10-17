"""레시피 시드(data/recipes/) 검사: 형식·어휘 검증, 구성, 검수표 최신 여부, 알레르기 스모크.

1-3 검수 완료 50개(published) + 1차 확장(2026-10-04) 초안 50개(draft) + 자취요리신 YouTube 데이터 변환 100개(draft, 2026-10-16) + 살림팝 169개(draft, int-2). 개수는 시드에서 센다.
"""

from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

import pytest
import yaml

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


def test_amounts_fit_db_precision(specs):
    # recipe_ingredient.amount는 numeric(8,2)라 소수 셋째 자리부터는 DB에서 잘린다(파일 = DB 스냅샷 유지).
    bad = [(s.id, i.raw_text, i.amount) for s in specs for i in s.ingredients
           if i.amount is not None and round(i.amount, 2) != i.amount]
    assert not bad, bad[:5]


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
    assert {by_id[i].source for i in PUBLISHED_IDS} == {"agent_draft"}
    # 영상 출처(자취요리신 변환) 외에는 모두 에이전트 작성 초안이다(외부 본문 복제 금지, D3).
    assert {s.source for s in specs if not s.source.startswith("https://www.youtube.com/watch?v=")} == {"agent_draft"}


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
        assert s.steps, s.id
        if s.status == "published":  # draft(자취요리신 변환)는 미매칭·중복 매핑을 검수표·CONVERSION.md로 확인
            assert all(i.ingredient is not None for i in s.ingredients), f"{s.id}: 미매칭 재료"
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
    # 주재료가 모두 미매칭인 draft는 후보가 되지 않아 제외 기록도 없다(누구에게도 제공되지 않음, 위 served 검사로 확인).
    candidates = {s.id for s in pool if s.id in kimchi_recipes
                  and any(i.role == "main" and i.ingredient is not None for i in s.ingredients)}
    assert candidates <= {e.recipe_id for e in allergen if e.ingredient_id in KIMCHI_LIKE and e.target == "shrimp"}
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


@pytest.mark.parametrize("extra, message", [
    ("cuisine: 미분류\ncook_time_min: 10\n", "미분류"),
    ("cuisine: 한식\n", "cook_time_min"),
])
def test_loader_rejects_unclassified_or_untimed_draft(ck, tmp_path, extra, message):
    """검증은 draft에 허용해도 엔진·DB 적재는 거부한다(plan 5-4)."""
    (tmp_path / "fs_1.yaml").write_text(
        "id: fs_1\ntitle: 예\n" + extra + "source: foodsafety\nstatus: draft\n"
        "ingredients:\n  - {ingredient: salt, raw_text: 소금 약간, role: sub}\n", encoding="utf-8")
    with pytest.raises(RecipeSeedError) as exc:
        load_recipe_specs(ck, tmp_path)
    assert [i.code for i in exc.value.issues] == ["not_loadable"]
    assert message in exc.value.issues[0].message


# --- 자취요리신 데이터 변환(2026-10-16, docs/decisions.md D3 예외) ---------------------------------------------


def dataset_urls(name):
    """YouTube 데이터셋 원본의 영상 URL(변환본 source와 같아야 한다)."""
    folder = ROOT / "data" / f"{name}_recipe_dataset" / "recipes" / name
    return {yaml.safe_load(p.read_text(encoding="utf-8"))["source"]["video_url"] for p in folder.glob("*.yaml")}


@pytest.mark.parametrize("name, count", [("simplecooking", 100), ("sallimpop", 169)])
def test_youtube_recipes_are_draft_with_video_source(specs, name, count):
    # 원본이 모두 변환되고, 출처는 영상 URL, 검수 전이므로 draft 그대로다(자취요리신 2026-10-16, 살림팝 int-2).
    urls = dataset_urls(name)
    converted = [s for s in specs if s.source in urls]
    assert len(urls) == len(converted) == count
    assert {s.status for s in converted} == {"draft"}
    if name == "simplecooking":
        assert {s.confidence for s in converted} == {"low"}  # 원본 confidence 그대로(살림팝은 high·low 섞임)
    assert {s.id for s in converted}.isdisjoint(PUBLISHED_IDS)


def test_seed_is_published_expansion_and_youtube(specs):
    # 시드 구성: 1-3 검수 50 + 1차 확장 draft 50 + 자취요리신 100 + 살림팝 169. 그 밖의 출처는 없다.
    expansion = [s for s in specs if s.source == "agent_draft" and s.status == "draft"]
    assert len(expansion) == 50
    youtube = dataset_urls("simplecooking") | dataset_urls("sallimpop")
    assert len(specs) == len(PUBLISHED_IDS) + len(expansion) + sum(s.source in youtube for s in specs)


def test_unmapped_only_in_drafts(specs):
    # 미매칭(null) 재료는 draft에만 있다(docs/plan.md 5-4). 미매칭 레시피는 알레르기 사용자에게 제외된다.
    with_unmapped = {s.id: s.status for s in specs if any(i.ingredient is None for i in s.ingredients)}
    assert with_unmapped and set(with_unmapped.values()) == {"draft"}


def test_unmapped_draft_excluded_for_any_allergy(recommender_with_drafts, specs):
    unmapped = {s.id for s in specs if any(i.ingredient is None for i in s.ingredients)}
    mains = {i.ingredient for s in specs if s.id in unmapped for i in s.ingredients if i.role == "main" and i.ingredient}
    ctx = UserContext(allergen_groups=frozenset({"peach"}), pantry=ALL_PANTRY | mains)
    result = recommender_with_drafts.recommend(ctx, RecommendRequest(limit=1000))
    assert not {i.recipe_id for i in result.items} & unmapped
    excluded = {e.recipe_id for e in result.exclusions if e.reason == ExclusionReason.UNMAPPED_INGREDIENT}
    assert excluded & unmapped
