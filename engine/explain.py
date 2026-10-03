"""추천 항목의 설명 데이터: 부족 재료, 대체 안내, 템플릿 문장 (docs/plan.md 4-7).

missing은 선택 재료가 아니면서 보유도 대체도 안 되는 재료 id다(기본 양념은 보유로 간주, 4-4).
미매칭 재료는 id가 없으므로 missing 대신 notes에 원문으로 적는다.
score와 breakdown은 응답용으로 소수 셋째 자리에서 반올림한다(정렬은 반올림 전 값으로 끝난 뒤).
"""

from __future__ import annotations

from collections.abc import Mapping

from engine.candidates import Candidate
from engine.korean import josa
from engine.model import KnowledgeSnapshot, RecommendItem, SubstitutionNote


def build_item(snapshot: KnowledgeSnapshot, candidate: Candidate, score: float, breakdown: Mapping[str, float]) -> RecommendItem:
    names = snapshot.ingredient_names
    missing: list[str] = []
    substitutions: list[SubstitutionNote] = []
    notes: list[str] = []
    for m in candidate.lines:
        line = m.line
        if m.status == "substitute":
            assert m.substitute is not None
            note = SubstitutionNote(m.substitute.from_id, m.substitute.to_id)
            if note not in substitutions:
                substitutions.append(note)
                notes.append(f"{names[note.need_id]} 대신 {josa(names[note.use_id], '을')} 쓸 수 있습니다")
        elif m.status == "missing":
            if line.ingredient_id is None:
                notes.append(f"확인되지 않은 재료가 있습니다: {line.raw_text}")
            elif line.optional:
                notes.append(f"{josa(names[line.ingredient_id], '은')} 선택 재료라 빼고 조리할 수 있습니다")
            elif line.ingredient_id not in missing:
                missing.append(line.ingredient_id)
    if breakdown.get("I") == 1.0 and not substitutions:
        notes.insert(0, "필요한 주재료와 부재료를 모두 갖고 있습니다")
    if breakdown.get("M", 1.0) < 1.0:
        notes.append(f"희망 시간보다 오래 걸립니다(약 {candidate.recipe.cook_time_min}분)")
    if candidate.recipe.status != "published":
        notes.append("검수 전 레시피입니다")
    return RecommendItem(
        recipe_id=candidate.recipe.id,
        title=candidate.recipe.title,
        score=round(score, 3),
        breakdown={k: round(v, 3) for k, v in breakdown.items()},
        missing=tuple(missing),
        substitutions=tuple(substitutions),
        notes=tuple(notes),
    )
