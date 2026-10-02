"""지식 기반 점수와 다양성 보정 (docs/plan.md 4-4~4-6).

S = Σ 가중치 × 항목. 항목(I·K·T·P·D·M)은 모두 0~1이고 가중치·계수는 config/weights.yaml에서 온다.
필터를 통과한 후보만 점수를 매긴다. 알레르기·절대 불선호는 이미 제외되었고 점수로 되살아나지 않는다.

  I 재료 커버리지: main 3·sub 2·기본 양념이 아닌 seasoning 1(비선택)의 가중합 중 보유 비율. 기본 양념·선택 재료·
     garnish는 뺀다. 대체재는 ratio(없으면 기본 인정 비율).
  K 음식 종류: soft cuisine 선호. 선호 like, 불선호 dislike, 없으면 neutral. 상충하면 낮은 값.
  T 맛 적합도: 1 − (|preferred_level − 레시피 강도|의 가중 평균 ÷ 5). 입력한 맛만, 전부 없으면 0.5.
  P 재료 선호: 재료마다 가장 구체적인 soft 선호(is_a 조상 depth가 가장 작은 것, 같은 깊이면 최솟값).
     값 = 0.5 + 0.5·polarity·strength. 역할 가중 평균(선택 재료는 optional 가중치). 가중치 없는 역할은 뺀다.
  D 난이도: (레시피 난이도 − 사용자 실력)별 점수.
  M 시간: 희망 시간 w 이내 1.0, 넘으면 max(0, 1 − (t − w)/w). 희망 시간 없으면 1.0.

요청 처리 중 재귀 탐색은 하지 않는다. P의 상위 개념은 컴파일된 ancestors(id → {조상: depth})만 조회한다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from engine.candidates import Candidate
from engine.config import COMPONENTS, ScoringConfig
from engine.model import KnowledgeSnapshot, RecommendRequest, UserContext


@dataclass(frozen=True)
class Scored:
    candidate: Candidate
    score: float
    breakdown: Mapping[str, float]


class UserScorer:
    """요청 한 번 동안의 점수 계산기. 사용자 선호를 미리 색인해 둔다."""

    def __init__(self, snapshot: KnowledgeSnapshot, cfg: ScoringConfig, user: UserContext, req: RecommendRequest):
        self._snapshot = snapshot
        self._cfg = cfg
        self._skill = user.skill_level
        self._wish = req.max_time_min

        soft = [p for p in user.preferences if not p.is_hard]
        self._ingredient_pref: dict[str, float] = {}
        for p in soft:
            if p.target_type != "ingredient":
                continue
            if p.target_id not in snapshot.ingredient_names:
                raise ValueError(f"알 수 없는 선호 재료: {p.target_id}")
            value = 0.5 + 0.5 * p.polarity * p.strength
            # 같은 재료에 선호가 여러 개면 가장 낮은 값(4-5 "같은 깊이면 최솟값"과 같은 원칙)
            self._ingredient_pref[p.target_id] = min(value, self._ingredient_pref.get(p.target_id, value))

        self._cuisine_score: dict[str, float] = {}
        for p in soft:
            if p.target_type == "cuisine":
                value = cfg.cuisine_like if p.polarity > 0 else cfg.cuisine_dislike
                self._cuisine_score[p.target_id] = min(value, self._cuisine_score.get(p.target_id, value))

        self._taste_pref: dict[str, int] = {}
        for t in user.tastes:
            # 같은 차원이 여러 번 오면 처음 값을 쓴다
            if t.preferred_level is not None and t.dimension in cfg.taste_dimensions:
                self._taste_pref.setdefault(t.dimension, t.preferred_level)

    # --- 항목별 점수 ------------------------------------------------------------------

    def coverage(self, candidate: Candidate) -> float:
        cfg = self._cfg
        need = have = 0.0
        for m in candidate.lines:
            weight = cfg.coverage_role_weight.get(m.line.role)
            if weight is None or (m.line.optional and cfg.coverage_exclude_optional):
                continue
            if cfg.coverage_exclude_pantry_staples and m.line.ingredient_id in self._snapshot.pantry_staples:
                continue
            need += weight
            if m.status == "owned":
                have += weight
            elif m.status == "substitute":
                assert m.substitute is not None
                ratio = m.substitute.ratio if m.substitute.ratio is not None else cfg.substitute_credit
                have += weight * ratio
        return have / need if need else 1.0

    def cuisine(self, candidate: Candidate) -> float:
        return self._cuisine_score.get(candidate.recipe.cuisine, self._cfg.cuisine_neutral)

    def taste(self, candidate: Candidate) -> float:
        if not self._taste_pref:
            return 0.5
        weights = self._cfg.taste_dimension_weight
        total = sum(weights[d] for d in self._taste_pref)
        if not total:
            return 0.5
        gap = sum(weights[d] * abs(level - getattr(candidate.recipe.taste, d)) for d, level in self._taste_pref.items())
        return max(0.0, 1.0 - (gap / total) / 5.0)

    def ingredient_preference(self, candidate: Candidate) -> float:
        cfg = self._cfg
        total = acc = 0.0
        for m in candidate.lines:
            line = m.line
            weight = cfg.preference_role_weight["optional"] if line.optional else cfg.preference_role_weight.get(line.role)
            if weight is None or line.ingredient_id is None:
                continue
            total += weight
            acc += weight * self.ingredient_value(line.ingredient_id)
        return acc / total if total else cfg.preference_neutral

    def ingredient_value(self, ingredient_id: str) -> float:
        """구체성 우선(4-5): 재료 자신(depth 0)부터 is_a 조상 depth 순으로 처음 만나는 선호."""
        if not self._ingredient_pref:
            return self._cfg.preference_neutral
        if ingredient_id in self._ingredient_pref:
            return self._ingredient_pref[ingredient_id]
        best_depth: int | None = None
        best = self._cfg.preference_neutral
        for ancestor, depth in self._snapshot.ancestors.get(ingredient_id, {}).items():
            value = self._ingredient_pref.get(ancestor)
            if value is None:
                continue
            if best_depth is None or depth < best_depth:
                best_depth, best = depth, value
            elif depth == best_depth:
                best = min(best, value)
        return best

    def difficulty(self, candidate: Candidate) -> float:
        diff = max(-2, min(2, candidate.recipe.difficulty - self._skill))
        return self._cfg.difficulty[diff]

    def time(self, candidate: Candidate) -> float:
        w = self._wish
        t = candidate.recipe.cook_time_min
        if w is None or t <= w:
            return 1.0
        if w <= 0:
            return 0.0
        return max(0.0, 1.0 - (t - w) / w)

    # --- 합산 ----------------------------------------------------------------------

    def score(self, candidate: Candidate) -> Scored:
        breakdown = {
            "I": self.coverage(candidate),
            "K": self.cuisine(candidate),
            "T": self.taste(candidate),
            "P": self.ingredient_preference(candidate),
            "D": self.difficulty(candidate),
            "M": self.time(candidate),
        }
        total = sum(self._cfg.weights[c] * breakdown[c] for c in COMPONENTS)
        return Scored(candidate, total, breakdown)


def rank(scored: Sequence[Scored]) -> list[Scored]:
    """점수 내림차순. 동점(응답 표기와 같은 소수 셋째 자리 기준)이면 I 높은 순 → 부족 재료 적은 순 →
    조리시간 짧은 순 → id 순."""
    return sorted(scored, key=_rank_key)


def _rank_key(s: Scored) -> tuple:
    return (-round(s.score, 3), -round(s.breakdown["I"], 3), missing_count(s.candidate),
            s.candidate.recipe.cook_time_min, s.candidate.recipe.id)


def missing_count(candidate: Candidate) -> int:
    """응답의 missing과 같은 기준: 선택 재료가 아니면서 보유·대체가 안 되는 재료 id 수."""
    return len({m.line.ingredient_id for m in candidate.lines
                if m.status == "missing" and not m.line.optional and m.line.ingredient_id is not None})


def diversify(ranked: Sequence[Scored], cfg: ScoringConfig) -> list[Scored]:
    """다양성 보정(4-6): 상위 top_n 안에 같은 음식 종류·같은 주재료가 한도를 넘지 않게 뒤로 미룬다.

    main 재료가 여러 개면 각각 센다. 한도를 지키며 top_n을 다 채우지 못하면 미룬 항목을 점수 순으로 채운다.
    top_n 밖의 순서는 점수 순 그대로다.
    """
    top_n = cfg.diversity_top_n
    picked: list[Scored] = []
    deferred: list[Scored] = []
    cuisine_count: dict[str, int] = {}
    main_count: dict[str, int] = {}
    rest_start = len(ranked)
    for i, s in enumerate(ranked):
        if len(picked) >= top_n:
            rest_start = i
            break
        recipe = s.candidate.recipe
        mains = _main_ids(s.candidate)
        if cuisine_count.get(recipe.cuisine, 0) >= cfg.diversity_max_same_cuisine or any(
            main_count.get(m, 0) >= cfg.diversity_max_same_main for m in mains
        ):
            deferred.append(s)
            continue
        picked.append(s)
        cuisine_count[recipe.cuisine] = cuisine_count.get(recipe.cuisine, 0) + 1
        for m in mains:
            main_count[m] = main_count.get(m, 0) + 1
    rest = list(ranked[rest_start:]) if len(picked) >= top_n else []
    fill = top_n - len(picked)
    head = picked + deferred[:fill]
    tail = rank(deferred[fill:] + rest)
    return head + tail


def _main_ids(candidate: Candidate) -> frozenset[str]:
    return frozenset(
        m.line.ingredient_id for m in candidate.lines if m.line.role == "main" and m.line.ingredient_id is not None
    )
