"""Jev 판단기 (decisions D10, docs/plan.md 부록 G-12). engine.v2.ports.Judge 구현.

  judge   후보 × 항목마다 Score 질문(5단계) 하나. 한 요청에 모두 담는다(후보 40 × 항목 5 ≈ 200질문, 약 2.5만 토큰).
  screen  넓은 후보(수백 개)를 후보마다 Score 질문 하나로 가볍게 걸러낸다. chunk개씩 나눠 병렬 요청.
질문 문구는 영어(Jev 주 학습 언어), 레시피·사용자 정보는 한국어 원문.
보내는 사용자 정보: 요리 실력, 매운맛 선호, 좋아하는·싫어하는 재료 이름, 음식 종류 선호, 요청 문장, 보유 재료 이름(내 재료로).
알레르기·절대 안 먹는 재료·사용자 id·레시피 id는 보내지 않는다(D10).
"""

from __future__ import annotations

import concurrent.futures as cf
import time
from collections.abc import Mapping
from typing import Any

from engine.v2.ports import JudgeCandidate, JudgeProfile, RerankAnswer, RerankError
from integrations.jev.client import JevClient, JevError

LEVELS = ["not at all", "weakly", "somewhat", "well", "perfectly"]
SKILL = {1: "beginner cook", 2: "intermediate cook", 3: "experienced cook"}
ASPECT_QUESTIONS = {
    "request": "How well does this recipe match what the user asked for (the dish name, or the mood/feel they described)?",
    "taste": "How well does this recipe's spiciness suit the user's spiciness preference?",
    "ingredients": "How well does this recipe suit the user's liked and disliked ingredients?",
    "cuisine": "How well does this recipe's cuisine suit the user's cuisine preferences?",
    "skill": "How suitable is this recipe's difficulty for the user's cooking skill?",
    "pantry": "How well does this recipe make use of the ingredients the user has on hand, needing little else?",
}
SCREEN_QUESTION = ("How likely is this recipe to be a good recommendation for this user? "
                   "If the user made a request, judge mainly by how well the recipe matches the request.")


def build_state(p: JudgeProfile) -> dict[str, Any]:
    s: dict[str, Any] = {}
    if p.request:
        s["user_request"] = p.request
    if p.skill_level is not None:
        s["cooking_skill"] = SKILL.get(p.skill_level, str(p.skill_level))
    if p.spicy_preference is not None:
        s["spiciness_preference_0_to_5"] = p.spicy_preference
    for key, value in (("liked_ingredients", p.liked_ingredients), ("disliked_ingredients", p.disliked_ingredients),
                       ("liked_cuisines", p.liked_cuisines), ("disliked_cuisines", p.disliked_cuisines),
                       ("ingredients_on_hand", p.ingredients_on_hand)):
        if value:
            s[key] = list(value)
    return s


def recipe_brief(c: JudgeCandidate, *, short: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"title": c.title, "main_ingredients": list(c.main_ingredients[:4] if short
                                                                      else c.main_ingredients)}
    if short:
        return out
    if c.cuisine:
        out["cuisine"] = c.cuisine
    if c.spiciness is not None:
        out["spiciness_0_to_5"] = c.spiciness
    if c.difficulty is not None:
        out["difficulty_1_to_3"] = c.difficulty
    if c.missing_ingredients:
        out["missing_ingredients"] = list(c.missing_ingredients)
    return out


def build_judge_questions(cands: tuple[JudgeCandidate, ...], aspects: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    return {f"{c.key}__{a}": {"type": "score",
                              "instructions": {"question": ASPECT_QUESTIONS[a], "recipe": recipe_brief(c)},
                              "criteria": LEVELS}
            for c in cands for a in aspects}


def build_screen_questions(cands: tuple[JudgeCandidate, ...]) -> dict[str, dict[str, Any]]:
    return {c.key: {"type": "score", "instructions": {"question": SCREEN_QUESTION,
                                                      "recipe": recipe_brief(c, short=True)},
                    "criteria": LEVELS}
            for c in cands}


def _score(ans: Any) -> RerankAnswer | None:
    if not isinstance(ans, Mapping) or ans.get("type") != "score":
        return None
    score, conf = ans.get("score"), ans.get("confidence")
    if not isinstance(score, (int, float)) or not isinstance(conf, (int, float)):
        return None
    top = len(LEVELS) - 1
    return RerankAnswer(min(1.0, max(0.0, float(score) / top)), min(1.0, max(0.0, float(conf))))


def parse_judge(answers: Mapping[str, Any], cands: tuple[JudgeCandidate, ...],
                aspects: tuple[str, ...]) -> dict[str, dict[str, RerankAnswer]]:
    """보낸 key·항목만 받는다. 형식이 틀린 답은 버린다."""
    out: dict[str, dict[str, RerankAnswer]] = {}
    for c in cands:
        for a in aspects:
            ans = _score(answers.get(f"{c.key}__{a}"))
            if ans is not None:
                out.setdefault(c.key, {})[a] = ans
    return out


class JevJudge:
    def __init__(self, client: JevClient, *, screen_chunk: int = 250, parallel: int = 8):
        self.client = client
        self.model = client.model
        self.screen_chunk = screen_chunk
        self.parallel = parallel

    def judge(self, profile: JudgeProfile, candidates: tuple[JudgeCandidate, ...], aspects: tuple[str, ...], *,
              timeout_s: float) -> dict[str, dict[str, RerankAnswer]]:
        if not candidates:
            return {}
        try:
            answers = self.client.system_one(build_state(profile), build_judge_questions(candidates, aspects),
                                             timeout_s=timeout_s)
        except JevError as exc:
            raise RerankError(str(exc)) from None
        return parse_judge(answers, candidates, aspects)

    def screen(self, profile: JudgeProfile, candidates: tuple[JudgeCandidate, ...], *,
               timeout_s: float) -> dict[str, float]:
        if not candidates:
            return {}
        state = build_state(profile)
        chunks = [candidates[i:i + self.screen_chunk] for i in range(0, len(candidates), self.screen_chunk)]
        deadline = time.monotonic() + timeout_s

        def run(chunk: tuple[JudgeCandidate, ...]) -> dict[str, float]:
            answers = self.client.system_one(state, build_screen_questions(chunk),
                                             timeout_s=max(0.1, deadline - time.monotonic()))
            out = {}
            for c in chunk:
                ans = _score(answers.get(c.key))
                if ans is not None:
                    out[c.key] = ans.score
            return out

        merged: dict[str, float] = {}
        try:
            with cf.ThreadPoolExecutor(max_workers=min(self.parallel, len(chunks))) as ex:
                for part in ex.map(run, chunks):
                    merged.update(part)
        except JevError as exc:
            raise RerankError(str(exc)) from None
        return merged
