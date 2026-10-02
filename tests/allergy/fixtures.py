"""알레르기 회귀 테스트용 작은 지식과 레시피.

지식은 dict로 적고 실제 컴파일러(kb.compile)를 통과시켜 closure를 만든다. closure를 손으로 만들지 않는다.
각 레시피는 검사하려는 알레르기 재료를 하나만 갖도록 짰다(제외 원인이 분명하도록).
모든 레시피는 같은 조건(한식, 난이도 1, 20분, 매운맛 0, 필수 조리기구 없음, published)이라
알레르기가 없는 사용자에게는 전부 추천 가능해야 한다(대조군).
"""

from __future__ import annotations

from engine.model import Preference, Recipe, RecipeIngredient, UserContext

# --- 지식 ----------------------------------------------------------------------


def _ing(id: str, name: str, **fields) -> dict:
    return {"id": id, "name": name, "status": "draft", **fields}


def _allergen(group: str, certainty: str = "definite") -> list[dict]:
    return [{"group": group, "certainty": certainty}]


INGREDIENTS = [
    # 분류
    _ing("seafood", "해산물", kind="concept"),
    _ing("jeotgal", "젓갈류", is_a=["seafood"]),
    # 원천 재료
    _ing("shrimp_raw", "새우", is_a=["seafood"], allergens=_allergen("shrimp")),
    _ing("crab", "게", is_a=["seafood"], allergens=_allergen("crab")),
    _ing("squid_raw", "오징어", is_a=["seafood"], allergens=_allergen("squid")),
    _ing("oyster", "굴", is_a=["seafood"], allergens=_allergen("shellfish")),
    _ing("egg", "계란", aliases=["달걀"], allergens=_allergen("egg")),
    _ing("milk", "우유", allergens=_allergen("milk")),
    _ing("peanut", "땅콩", allergens=_allergen("peanut")),
    _ing("walnut", "호두", allergens=_allergen("walnut")),
    _ing("wheat_flour", "밀가루", allergens=_allergen("wheat")),
    _ing("soybean", "대두", allergens=_allergen("soybean")),
    # 가공품 (알레르기는 derived_from으로만 상속)
    _ing("saeujeot", "새우젓", is_a=["jeotgal"], derived_from=["shrimp_raw"], is_processed=True),
    _ing("kimchi", "배추김치", aliases=["김치"],
         derived_from=[{"id": "saeujeot", "certainty": "possible"}], is_processed=True),
    _ing("oyster_sauce", "굴소스", derived_from=["oyster"], is_processed=True),
    _ing("mayonnaise", "마요네즈", derived_from=["egg"], is_processed=True),
    _ing("peanut_butter", "땅콩버터", derived_from=["peanut"], is_processed=True),
    _ing("butter", "버터", derived_from=["milk"], is_processed=True),
    _ing("soy_sauce", "간장", derived_from=["soybean", "wheat_flour"], is_processed=True),
    _ing("gochujang", "고추장",
         derived_from=["soybean", {"id": "wheat_flour", "certainty": "possible"}], is_processed=True),
    _ing("buchimgaru", "부침가루", derived_from=["wheat_flour"], is_processed=True),
    # 3단계 파생: 김치양념소스 → 김치 → 새우젓 → 새우
    _ing("kimchi_sauce", "김치양념소스", derived_from=["kimchi"], is_processed=True),
    # 원천 재료 자체의 알레르기가 포함 가능(possible)
    _ing("seasoning_blend", "혼합 조미료", allergens=_allergen("milk", "possible")),
    # 알레르기는 상위 재료(조개)에만 지정, 하위(바지락)는 is_a로 상속
    _ing("clam", "조개", is_a=["seafood"], allergens=_allergen("shellfish")),
    _ing("manila_clam", "바지락", is_a=["clam"]),
    _ing("octopus", "낙지", is_a=["seafood"]),
    # 알레르기 없는 재료
    _ing("rice", "쌀"),
    _ing("potato", "감자"),
    _ing("cabbage", "배추"),
    _ing("mushroom", "버섯"),
    _ing("cucumber", "오이"),
    _ing("green_onion", "대파"),
    _ing("cooking_oil", "식용유"),
    _ing("salt", "소금"),
    _ing("sesame_oil", "참기름"),
]

GROUPS = [
    {"id": g, "display_name": g, "status": "draft"}
    for g in ("shrimp", "crab", "squid", "shellfish", "egg", "milk", "peanut", "walnut", "wheat", "soybean")
]

BUNDLES = [
    {"id": "crustacean_bundle", "display_name": "갑각류", "includes": ["shrimp", "crab"], "status": "draft"},
    {"id": "nuts_bundle", "display_name": "견과류", "includes": ["peanut", "walnut"], "status": "draft"},
    {"id": "seafood_bundle", "display_name": "해산물 전체", "includes": ["shrimp", "crab", "squid", "shellfish"],
     "status": "draft"},
]

# 식용유는 일부러 기본 양념에서 뺐다(대체 안내 시나리오에서 "없는 재료"가 되도록).
STAPLES = ["salt", "sesame_oil", "soy_sauce", "gochujang"]

SUBSTITUTES = [
    {"from": "cooking_oil", "to": "butter", "context": ["볶음"], "status": "draft"},
    {"from": "octopus", "to": "shrimp_raw", "context": ["볶음"], "status": "draft"},
]

VOCAB = {
    "cuisines": ["한식"],
    "equipment": ["냄비", "프라이팬"],
    "techniques": ["볶음", "끓이기", "구이", "조림", "무침", "부침"],
    "categories": [],
}


# --- 레시피 --------------------------------------------------------------------


def _recipe(id: str, title: str, *lines: tuple, techniques: tuple[str, ...] = ()) -> Recipe:
    """lines: (재료 id 또는 None, role[, optional[, raw_text]])"""
    ingredients = []
    for n, line in enumerate(lines, start=1):
        ingredient_id, role = line[0], line[1]
        optional = line[2] if len(line) > 2 else False
        raw_text = line[3] if len(line) > 3 else (ingredient_id or "")
        ingredients.append(RecipeIngredient(n, ingredient_id, role, optional, raw_text))
    return Recipe(
        id=id, title=title, cuisine="한식", difficulty=1, cook_time_min=20,
        ingredients=tuple(ingredients), techniques=frozenset(techniques),
    )


RECIPES = [
    # 모든 알레르기 사용자에게 안전한 레시피(엔진이 전부 제외하지 않는지 확인용)
    _recipe("potato_salt", "감자구이", ("potato", "main"), ("salt", "seasoning")),
    # 새우·갑각류
    _recipe("cabbage_saeujeot_soup", "배추 새우젓국", ("cabbage", "main"), ("saeujeot", "seasoning")),
    _recipe("kimchi_fried_rice", "김치볶음밥", ("rice", "main"), ("kimchi", "sub"), ("sesame_oil", "seasoning")),
    _recipe("shrimp_stirfry", "새우볶음", ("shrimp_raw", "main"), ("salt", "seasoning")),
    _recipe("crab_soup", "게탕", ("crab", "main"), ("salt", "seasoning")),
    _recipe("squid_stirfry", "오징어볶음", ("squid_raw", "main"), ("salt", "seasoning")),
    # 조개류
    _recipe("oyster_sauce_mushroom", "굴소스 버섯볶음", ("mushroom", "main"), ("oyster_sauce", "seasoning")),
    # 난류·우유
    _recipe("mayo_cucumber_salad", "오이 마요 샐러드", ("cucumber", "main"), ("mayonnaise", "seasoning")),
    _recipe("butter_potato", "버터감자", ("potato", "main"), ("butter", "sub")),
    _recipe("cucumber_soup_egg_garnish", "오이냉국(지단 고명)", ("cucumber", "main"), ("egg", "garnish")),
    _recipe("mushroom_rice_optional_egg", "버섯밥(계란 선택)", ("rice", "main"), ("mushroom", "sub"),
            ("egg", "sub", True)),
    # 견과류
    _recipe("peanut_butter_cucumber", "오이 땅콩버터 무침", ("cucumber", "main"), ("peanut_butter", "sub")),
    _recipe("walnut_roast", "호두볶음", ("walnut", "main"), ("salt", "seasoning")),
    # 밀·대두
    _recipe("soy_braised_potato", "감자조림", ("potato", "main"), ("soy_sauce", "seasoning")),
    _recipe("gochujang_potato", "고추장 감자조림", ("potato", "main"), ("gochujang", "seasoning")),
    _recipe("pajeon", "파전", ("green_onion", "main"), ("buchimgaru", "sub")),
    # 미매칭 재료
    _recipe("mushroom_secret_sauce", "비법소스 버섯구이", ("mushroom", "main"), (None, "seasoning", False, "비법 소스 2큰술")),
    # 대체 안내: 식용유가 없고 버터가 있음
    _recipe("mushroom_stirfry_oil", "버섯볶음", ("mushroom", "main"), ("cooking_oil", "sub"), techniques=("볶음",)),
    # 대체재로만 후보가 되는 레시피: 낙지가 없고 새우가 있음(낙지 → 새우, 볶음)
    _recipe("octopus_stirfry", "낙지볶음", ("octopus", "main"), ("salt", "seasoning"), techniques=("볶음",)),
    # 넓은 재료·그래프 변형
    _recipe("jeotgal_cabbage_salad", "배추겉절이(젓갈)", ("cabbage", "main"), ("jeotgal", "seasoning")),
    _recipe("kimchi_sauce_potato", "김치양념 감자볶음", ("potato", "main"), ("kimchi_sauce", "seasoning")),
    _recipe("seasoning_blend_mushroom", "조미료 버섯구이", ("mushroom", "main"), ("seasoning_blend", "seasoning")),
    _recipe("manila_clam_soup", "바지락국", ("manila_clam", "main"), ("salt", "seasoning")),
]

RECIPE_IDS = frozenset(r.id for r in RECIPES)

# 모든 레시피가 후보가 되도록 레시피의 main·sub·garnish 재료를 모두 보유한다.
# 단, 식용유와 낙지는 빼서 대체 안내(식용유 대신 버터, 낙지 대신 새우)가 필요한 상황을 만든다.
PANTRY = frozenset(
    line.ingredient_id
    for r in RECIPES
    for line in r.ingredients
    if line.ingredient_id is not None and line.role in ("main", "sub", "garnish")
) - {"cooking_oil", "octopus"}


def user(*allergens: str, preferences: tuple[Preference, ...] = (), pantry: frozenset[str] = PANTRY) -> UserContext:
    return UserContext(allergen_groups=frozenset(allergens), preferences=preferences, pantry=pantry)


def hard_dislike(ingredient_id: str) -> Preference:
    return Preference("ingredient", ingredient_id, -1, 1.0, is_hard=True)


NO_ALLERGY = user()
