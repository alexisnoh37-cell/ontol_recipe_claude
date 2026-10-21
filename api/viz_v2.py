"""v2 추천 재생 표시 계층 (docs/plan.md 부록 H-3). 엔진 V2Trace → /viz 3D 그래프 노드·간선 id로 옮긴다.

판정은 하지 않는다. id 접두어(ing:, ag:, rcp:)·링크 id·라벨만 붙인다. 알레르기 경로는 v1 재생과 같은
GraphCatalog.exclusion()을 쓴다. "Jev가 받은 것"은 integrations/jev/judge.py의 순수 함수(build_state,
recipe_brief, ASPECT_QUESTIONS)로 엔진이 실제로 보낸 형태를 다시 만든 것이다(Jev를 다시 부르지 않는다).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from api.viz import REASON_PRIORITY, GraphCatalog, ag, ing, isa_link, rcp
from engine.model import UserContext
from engine.normalize import normalize_term
from engine.v2.model import V2Result
from engine.v2.trace import JudgeCall, V2Trace
from integrations.jev.judge import ASPECT_QUESTIONS, LEVELS, build_state, recipe_brief


def _r(x: float) -> float:
    return round(float(x), 3)


def judge_view(call: JudgeCall | None) -> dict[str, Any] | None:
    if call is None:
        return None
    return {
        "state": build_state(call.profile),  # Jev에 보낸 사용자 정보(키 이름 그대로)
        "aspects": list(call.aspects),
        "questions": {a: ASPECT_QUESTIONS[a] for a in call.aspects},
        "levels": list(LEVELS),
        "weights": dict(call.weights),
        "candidates": [{"key": c.key, "recipe": rcp(call.recipe_of[c.key]), "brief": recipe_brief(c)}
                       for c in call.candidates],
        "answers": {rcp(call.recipe_of[k]): {a: {"score": _r(s), "confidence": _r(conf)} for a, (s, conf) in ans.items()}
                    for k, ans in call.answers.items()},
        "failed": call.failed,
    }


def trace_v2(result: V2Result, t: V2Trace, graph: GraphCatalog, user: UserContext, *,
             exclusion_labels: Mapping[str, str], breakdown_labels: Mapping[str, str], playback: Mapping[str, Any],
             rule_weights: Mapping[str, float], s_weight: float, similarity_weights: Mapping[str, float],
             limit: int) -> dict[str, Any]:
    # 보유: 입력(pantry), 그 is_a 상위(ancestor), 기본 양념과 그 상위(staple). 엔진이 계산한 집합을 나눠 보일 뿐이다
    owned = [{"node": ing(i), "because": "pantry"} for i in sorted(t.pantry)]
    owned += [{"node": ing(i), "because": "ancestor"} for i in sorted(t.from_pantry - t.pantry)]
    owned += [{"node": ing(i), "because": "staple"} for i in sorted(t.owned - t.from_pantry - t.pantry)]
    owned_links = sorted(isa_link(c, p) for c, p in graph._isa if c in t.owned and p in t.owned)

    excluded: dict[str, str] = {}
    for e in sorted(result.exclusions, key=lambda e: REASON_PRIORITY.index(e.reason)):
        excluded.setdefault(rcp(e.recipe_id), e.reason.value)

    query = None
    if t.query is not None:
        q = t.query
        query = {
            "text": q.text, "terms": list(q.terms),
            "rules": [{"matched": [m for m in r.match if normalize_term(m) in q.norm],
                       "taste": {d: {"min": lo, "max": hi} for d, (lo, hi) in r.taste.items()},
                       "cuisine": r.cuisine, "title_any": list(r.title_any)} for r in q.rules],
            "ingredients": [ing(i) for i in sorted(q.ingredient_ids)],
            "anchors": [rcp(r.id) for r in q.anchors],
            "active": list(t.active),
            "weights": {k: similarity_weights[k] for k in t.active},
            "best_excluded": _r(t.best_excluded),
        }
    checked = dict(t.checked)  # 확인하지 않은 레시피(pool이 찬 뒤)는 None
    top_sim = sorted(t.similarity.items(), key=lambda kv: (-kv[1][0], kv[0]))[: int(playback.get("max_similarity", 60))]
    similarity = [{"recipe": rcp(rid), "S": _r(s), "parts": {k: _r(v) for k, v in parts.items()},
                   "passed": checked.get(rid)}
                  for rid, (s, parts) in top_sim]

    shown = {i.item.recipe_id for i in result.items}
    ranked = [{"recipe": rcp(rid), "rank": n, "score": _r(score),
               "breakdown": {k: _r(v) for k, v in breakdown.items()}, "shown": rid in shown}
              for n, (rid, score, breakdown) in enumerate(t.ranked, start=1)]

    hard_ing = sorted(p.target_id for p in user.preferences if p.is_hard and p.target_type == "ingredient")
    hard_cui = sorted(p.target_id for p in user.preferences if p.is_hard and p.target_type == "cuisine")
    spicy_max = min((x.max_level for x in user.tastes if x.dimension == "spicy" and x.max_level is not None),
                    default=None)
    return {
        "mode": t.mode, "ranking": t.ranking, "jev_failed": t.jev_failed, "model": result.rerank_model,
        "limit": limit, "seed": t.seed,
        "user": {"allergen_groups": [ag(g) for g in sorted(user.allergen_groups)],
                 "hard_dislikes": [ing(i) for i in hard_ing], "hard_cuisines": hard_cui,
                 "spicy_max": spicy_max, "skill_level": user.skill_level},
        "pantry": {"input": [ing(i) for i in sorted(t.pantry)], "owned": owned, "owned_links": owned_links},
        "checked": [{"recipe": rcp(rid), "passed": ok} for rid, ok in t.checked],
        "query": query,
        "similarity": similarity,
        "groups": {g: [rcp(r) for r in ids] for g, ids in t.groups.items()},
        "missing": {rcp(r): n for r, n in t.missing.items()},
        "uses_pantry": {rcp(r): n for r, n in t.uses_pantry.items()},
        "exclusions": [graph.exclusion(e, dict(exclusion_labels)) for e in result.exclusions],
        "excluded": excluded,
        "pool": [rcp(r) for r in t.pool],
        "screened": {rcp(r): _r(s) for r, s in t.screened.items()},
        "jev": judge_view(t.judge),
        "failed_jev": judge_view(t.failed_judge),
        "ranked": ranked,
        "rule_weights": dict(rule_weights), "s_weight": s_weight,
        "breakdown_labels": dict(breakdown_labels),
        "labels": dict(playback.get("labels") or {}),
    }


__all__ = ["judge_view", "trace_v2"]
