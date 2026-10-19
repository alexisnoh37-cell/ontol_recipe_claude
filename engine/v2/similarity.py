"""요리명·느낌 유사도 S (docs/plan.md 부록 G-3). 규칙만 쓴다(재현 가능, Jev 없음).

S는 질의에서 걸린 항목만 가중 평균한다(가중치 config/v2.yaml dish.similarity).
  title      제목 완전 일치 1, 질의가 제목에 들어 있거나 제목이 질의에 들어 있으면 0.8,
             아니면 질의 낱말(min_term_len 이상) 중 제목에 들어 있는 비율 × 0.6
  ingredient 질의에 나온 재료 이름(별칭 색인)을 레시피가 쓰는 비율(레시피 재료의 is_a 조상까지)
  keyword    키워드 규칙 조건(맛 범위·음식 종류·제목 낱말)을 만족하는 정도. 맛을 모르면 0.5
  anchor     제목이 질의와 완전히 같은 레시피(앵커)와의 맛·main 재료·음식 종류 유사도
항목이 하나도 걸리지 않으면 None(호출자가 "비슷한 레시피 없음"으로 처리).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from engine.model import KnowledgeSnapshot, Recipe
from engine.normalize import normalize_term
from engine.v2.config import TASTE_DIMENSIONS, KeywordRule, V2Config


@dataclass(frozen=True)
class DishQuery:
    text: str
    norm: str
    terms: tuple[str, ...]  # 공백으로 나눈 낱말(정규화, 최소 길이 이상)
    ingredient_ids: frozenset[str]  # 질의에 나온 재료
    rules: tuple[KeywordRule, ...]  # 걸린 키워드 규칙
    anchors: tuple[Recipe, ...]  # 제목이 질의와 완전히 같은 레시피


def parse_query(snapshot: KnowledgeSnapshot, cfg: V2Config, text: str, recipes: Sequence[Recipe],
                titles: Mapping[str, str] | None = None) -> DishQuery:
    """titles: 레시피 id → 정규화한 제목(호출자가 미리 만들어 두면 다시 계산하지 않는다)."""
    norm = normalize_term(text)
    min_len = cfg.dish_min_term_len
    terms = tuple(dict.fromkeys(t for t in (normalize_term(w) for w in text.split()) if len(t) >= min_len))
    ingredient_ids = frozenset(
        i for alias, i in snapshot.alias_index.items()
        if len(alias) >= min_len and alias in norm and i not in snapshot.concept_ids
    )
    rules = tuple(r for r in cfg.dish_keywords if any(normalize_term(m) in norm for m in r.match))
    title_of = (lambda r: titles[r.id]) if titles is not None else (lambda r: normalize_term(r.title))
    anchors = tuple(r for r in recipes if title_of(r) == norm)
    return DishQuery(text, norm, terms, ingredient_ids, rules, anchors)


class DishScorer:
    def __init__(self, snapshot: KnowledgeSnapshot, cfg: V2Config, query: DishQuery,
                 titles: Mapping[str, str] | None = None, not_spicy: frozenset[str] = frozenset()):
        self._snapshot = snapshot
        self._cfg = cfg
        self._q = query
        self._titles = titles or {}
        self._not_spicy = not_spicy  # 맛 정보는 없지만 매운맛 0으로 추정한 레시피(D9)

    def components(self, recipe: Recipe) -> dict[str, float]:
        """걸린 항목만 담는다. title은 값이 0이어도 담고, 호출자가 전체 후보 중 0뿐이면 뺀다."""
        out = {"title": self.title(recipe)}
        if self._q.ingredient_ids:
            out["ingredient"] = self.ingredient(recipe)
        if self._q.rules:
            out["keyword"] = self.keyword(recipe)
        if self._q.anchors:
            out["anchor"] = self.anchor(recipe)
        return out

    def title(self, recipe: Recipe) -> float:
        q = self._q
        t = self._titles.get(recipe.id) or normalize_term(recipe.title)
        if not q.norm or not t:
            return 0.0
        if t == q.norm:
            return 1.0
        min_len = self._cfg.dish_min_term_len
        if (len(q.norm) >= min_len and q.norm in t) or (len(t) >= min_len and t in q.norm):
            return 0.8
        if not q.terms:
            return 0.0
        return 0.6 * sum(1 for term in q.terms if term in t) / len(q.terms)

    def ingredient(self, recipe: Recipe) -> float:
        wanted = self._q.ingredient_ids
        have: set[str] = set()
        for line in recipe.ingredients:
            if line.ingredient_id is None:
                continue
            have.add(line.ingredient_id)
            have.update(self._snapshot.ancestors.get(line.ingredient_id, {}))
        return len(wanted & have) / len(wanted)

    def keyword(self, recipe: Recipe) -> float:
        scores: list[float] = []
        for rule in self._q.rules:
            for dim, (lo, hi) in rule.taste.items():
                if recipe.taste is None:
                    if dim == "spicy" and recipe.id in self._not_spicy:
                        scores.append(1.0 if (lo is None or lo <= 0) else 0.0)
                    else:
                        scores.append(0.5)
                    continue
                level = getattr(recipe.taste, dim)
                scores.append(1.0 if (lo is None or level >= lo) and (hi is None or level <= hi) else 0.0)
            if rule.cuisine is not None:
                scores.append(1.0 if recipe.cuisine == rule.cuisine else 0.0)
            if rule.title_any:
                scores.append(1.0 if any(w in recipe.title for w in rule.title_any) else 0.0)
        return sum(scores) / len(scores) if scores else 0.0

    def anchor(self, recipe: Recipe) -> float:
        return max(_recipe_similarity(a, recipe) for a in self._q.anchors)


def combine(components: Mapping[str, float], weights: Mapping[str, float], active: Iterable[str]) -> float:
    keys = [k for k in active if k in components]
    total = sum(weights[k] for k in keys)
    return sum(weights[k] * components[k] for k in keys) / total if total else 0.0


def _recipe_similarity(a: Recipe, b: Recipe) -> float:
    if a.id == b.id:
        return 1.0
    if a.taste is None or b.taste is None:
        taste = 0.5
    else:
        gap = sum(abs(getattr(a.taste, d) - getattr(b.taste, d)) for d in TASTE_DIMENSIONS) / len(TASTE_DIMENSIONS)
        taste = 1.0 - gap / 5.0
    ma, mb = _mains(a), _mains(b)
    mains = len(ma & mb) / len(ma | mb) if ma | mb else 0.0
    cuisine = 1.0 if a.cuisine == b.cuisine else 0.0
    return (taste + mains + cuisine) / 3.0


def _mains(r: Recipe) -> frozenset[str]:
    return frozenset(line.ingredient_id for line in r.ingredients if line.role == "main" and line.ingredient_id)
