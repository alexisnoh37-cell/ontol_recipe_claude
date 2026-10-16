"""재료 선택으로 레시피 찾기 (docs/plan.md 6장 "부가 트랙 ui", ui-2).

추천이 아니라 조회다. 점수·선호로 순위를 매기지 않고 "고른 재료로 만들 수 있는가"만 본다.

  - 보유로 보는 재료: 고른 재료, 기본 양념, 그리고 그들의 is_a 조상(삼겹살 → "돼지고기" 충족, 반대 방향은 아님).
    추천 후보 단계와 같은 owned_ingredients를 쓴다(컴파일된 ancestor 조회만, 요청 중 그래프 탐색 없음).
  - 대상 레시피: 고른 재료(기본 양념 제외)로 main 재료 하나 이상이 채워지는 레시피(추천 후보 기준과 같음).
  - 꼭 필요한 재료: 선택이 아닌 main·sub·seasoning 줄. 고명과 선택 재료는 없어도 조리 가능으로 본다.
    정규 id가 없는(미매칭) 꼭 필요한 줄은 채울 수 없으므로 부족으로 센다.
  - 조리 가능: 부족 0개. 거의 가능: 부족 1~max_missing개.
  - 대체재는 쓰지 않는다(사람 결정 2026-10-16).

알레르기는 제외하지 않고 주의 표시로 붙인다(사람 결정 2026-10-16, 조회 기능 한정). 판정 자체는 추천 필터와
같은 UserConstraints.check(possible·선택·고명·기본 양념 포함, 미매칭 재료 = 안전 보장 불가)를 그대로 쓰고,
그 결과(Exclusion) 중 알레르기·미매칭 사유만 경고로 돌려준다. 추천(Recommender.recommend)의 제외 규칙은 바뀌지 않는다.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from engine.candidates import CANDIDATE_ROLES, owned_ingredients
from engine.filters import UserConstraints
from engine.model import Exclusion, ExclusionReason, KnowledgeSnapshot, Recipe, RecommendRequest, UserContext
from engine.normalize import clean_pantry
from engine.ports import RecipeRepository

REQUIRED_ROLES = ("main", "sub", "seasoning")
ALLERGY_REASONS = (ExclusionReason.ALLERGEN, ExclusionReason.UNMAPPED_INGREDIENT)


@dataclass(frozen=True)
class BrowseItem:
    recipe: Recipe
    used: tuple[str, ...]  # 이 레시피의 줄을 채운 고른 재료(고른 순서)
    missing: tuple[int, ...]  # 부족한 꼭 필요한 줄 번호(line_no)
    optional_missing: tuple[int, ...]  # 없는 고명·선택 줄 번호(조리 가능 판단과 무관, 표시용)
    allergy: tuple[Exclusion, ...]  # 알레르기·미매칭 경고(사용자 알레르기가 있을 때만)

    @property
    def has_allergy_warning(self) -> bool:
        return bool(self.allergy)


@dataclass(frozen=True)
class BrowseResult:
    selected: tuple[str, ...]  # 정리된 고른 재료(모르는 id·concept 제외)
    cookable: tuple[BrowseItem, ...]
    near: tuple[BrowseItem, ...]  # 부족 1~max_missing개


def find_by_ingredients(
    snapshot: KnowledgeSnapshot,
    recipes: RecipeRepository,
    selected: Iterable[str],
    *,
    allergen_groups: Iterable[str] = (),
    max_missing: int = 2,
    serve_draft_recipes: bool = False,
) -> BrowseResult:
    """모르는 알레르기 그룹이면 ValueError(UserConstraints와 같음)."""
    selected = list(selected)
    valid = clean_pantry(snapshot, selected)
    order = [i for i in dict.fromkeys(selected) if i in valid]
    chosen = frozenset(order)
    constraints = UserConstraints(snapshot, UserContext(allergen_groups=frozenset(allergen_groups)), RecommendRequest())
    owned = owned_ingredients(snapshot, chosen)
    from_selected = owned_ingredients(snapshot, chosen, include_staples=False)
    covers = {s: {s, *snapshot.ancestors.get(s, {})} for s in order}  # 고른 재료 → 채울 수 있는 재료 id

    cookable: list[BrowseItem] = []
    near: list[BrowseItem] = []
    for recipe in recipes.by_ingredients(from_selected):
        if recipe.status != "published" and not serve_draft_recipes:
            continue
        if not any(line.role in CANDIDATE_ROLES and line.ingredient_id in from_selected for line in recipe.ingredients):
            continue
        missing, optional_missing = [], []
        for line in recipe.ingredients:
            if line.ingredient_id is not None and line.ingredient_id in owned:
                continue
            required = line.role in REQUIRED_ROLES and not line.optional
            (missing if required else optional_missing).append(line.line_no)
        if len(missing) > max_missing:
            continue
        ids = {line.ingredient_id for line in recipe.ingredients}
        used = tuple(s for s in order if covers[s] & ids)
        allergy = tuple(e for e in constraints.check(recipe) if e.reason in ALLERGY_REASONS)
        item = BrowseItem(recipe, used, tuple(missing), tuple(optional_missing), allergy)
        (near if missing else cookable).append(item)

    # 안전한 레시피를 먼저, 그다음 부족 수가 적고 고른 재료를 많이 쓰는 순. 동점은 제목·id 순.
    def key(it: BrowseItem) -> tuple:
        return (it.has_allergy_warning, len(it.missing), -len(it.used), it.recipe.title, it.recipe.id)

    return BrowseResult(tuple(order), tuple(sorted(cookable, key=key)), tuple(sorted(near, key=key)))
