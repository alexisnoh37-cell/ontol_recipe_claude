"""Jev 재정렬기 (docs/plan.md 부록 G-4). engine.v2.ports.Reranker 구현.

후보마다 Score 질문 하나(5단계)를 한 요청에 담는다. 질문 문구는 영어(Jev 주 학습 언어), 레시피·질의는 원문(한국어).
보내는 것: 질의 문장(dish), 요리 실력, 맛 선호, 후보 요약(제목·음식 종류·맛·주재료 이름).
알레르기·건강 정보·사용자 id·보유 재료·레시피 id는 보내지 않는다(D7).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from engine.v2.ports import RerankAnswer, RerankCandidate, RerankError, RerankQuery
from integrations.jev.client import JevClient, JevError

SCHEMA_VERSION = "rerank-1"
LEVELS = ["not a fit at all", "a weak fit", "a reasonable fit", "a good fit", "an excellent fit"]
SKILL = {1: "beginner cook", 2: "intermediate cook", 3: "experienced cook"}
QUESTION = {
    "dish": "How well does this recipe match what the user asked for (the dish name or the mood/feel of the dish)?",
    "pantry": "How well does this recipe suit this user's cooking skill and taste preferences?",
}
TASTE_LABEL = {"spicy": "spiciness", "salty": "saltiness", "sweet": "sweetness", "sour": "sourness",
               "umami": "umami", "savory": "nuttiness/richness"}


def build_state(query: RerankQuery) -> dict[str, Any]:
    state: dict[str, Any] = {}
    if query.kind == "dish" and query.query:
        state["user_request"] = query.query
    if query.skill_level is not None:
        state["cooking_skill"] = SKILL.get(query.skill_level, str(query.skill_level))
    if query.taste_preferences:
        state["taste_preferences"] = {
            TASTE_LABEL.get(d, d): {("preferred_level_0_to_5" if k == "preferred" else "max_tolerable_0_to_5"): v
                                    for k, v in p.items()}
            for d, p in query.taste_preferences.items()
        }
    return state


def build_questions(query: RerankQuery) -> dict[str, dict[str, Any]]:
    return {c.key: {"type": "score", "instructions": {"question": QUESTION[query.kind], "recipe": _recipe(c)},
                    "criteria": LEVELS}
            for c in query.candidates}


def _recipe(c: RerankCandidate) -> dict[str, Any]:
    out: dict[str, Any] = {"title": c.title, "main_ingredients": list(c.main_ingredients)}
    if c.cuisine and c.cuisine != "미분류":
        out["cuisine"] = c.cuisine
    if c.taste is not None:
        out["taste_0_to_5"] = dict(c.taste)
    return out


def parse_answers(answers: Mapping[str, Any], keys: set[str]) -> dict[str, RerankAnswer]:
    """보낸 key만 받는다. 형식이 틀린 답은 버린다(엔진이 규칙 점수를 쓴다)."""
    top = len(LEVELS) - 1
    out: dict[str, RerankAnswer] = {}
    for key, ans in answers.items():
        if key not in keys or not isinstance(ans, Mapping) or ans.get("type") != "score":
            continue
        score, conf = ans.get("score"), ans.get("confidence")
        if not isinstance(score, (int, float)) or not isinstance(conf, (int, float)):
            continue
        out[key] = RerankAnswer(min(1.0, max(0.0, float(score) / top)), min(1.0, max(0.0, float(conf))))
    return out


class JevReranker:
    def __init__(self, client: JevClient):
        self.client = client
        self.model = client.model

    def rerank(self, query: RerankQuery, *, timeout_s: float) -> dict[str, RerankAnswer]:
        if not query.candidates:
            return {}
        try:
            answers = self.client.system_one(build_state(query), build_questions(query), timeout_s=timeout_s)
        except JevError as exc:
            raise RerankError(str(exc)) from None
        return parse_answers(answers, {c.key for c in query.candidates})
