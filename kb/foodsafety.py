"""식품안전나라 조리식품 레시피 DB(COOKRCP01) 원본 → 레시피 YAML dict 변환 (docs/plan.md 5-3-1).

결정적 규칙만 쓴다(LLM·확률적 매핑 없음). 재료 이름이 별칭 색인과 정확히 일치할 때만 정규 id를 채우고,
나머지는 None(미매칭)으로 둔다. 미매칭 재료가 있는 레시피는 알레르기 사용자에게 제외된다(안전 규칙).
재료 줄을 잘못 버리면 알레르기 판정에서 빠지므로, 버리는 줄은 레시피 이름과 고정된 머리말 단어뿐이다.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from kb.datacheck import UNCLASSIFIED_CUISINE
from kb.text import normalize_term

SERVICE_ID = "COOKRCP01"
SOURCE = "foodsafety"
SOURCE_LABEL = "식품의약품안전처 식품안전나라 조리식품의 레시피 DB(COOKRCP01)"
MANUAL_COUNT = 20

# 재료정보에서 재료가 아니라 묶음 머리말로 쓰이는 단어(정확히 일치할 때만 버린다)
HEADER_WORDS = frozenset(normalize_term(w) for w in (
    "재료", "주재료", "부재료", "필수재료", "선택재료", "기본재료", "고명", "고명재료", "양념", "양념장", "양념재료",
    "소스", "소스재료", "드레싱", "육수", "반죽", "속재료", "토핑", "곁들임", "밑간", "절임물", "조림장",
))
_BULLET = re.compile(r"^[\s●•·○◎■□◆◇▶▷★☆※*\-]+")
_BRACKET_HEAD = re.compile(r"^[\[［【<〈(（]([^\]］】>〉)）]{1,15})[\]］】>〉)）]\s*")
# 양 표기가 시작되는 지점: 숫자, 여는 괄호, 분수 문자, 양 단어
_AMOUNT_START = re.compile(r"[0-9０-９½⅓⅔¼¾(（]|약간|적당량|적당히|조금|소량|한줌|한꼬집")
_PAREN = re.compile(r"[(（][^)）]*[)）]")
_STEP_NO = re.compile(r"^\s*\d+\s*[.)]\s*")
_STEP_TAIL = re.compile(r"[a-zA-Z]\s*$")


class FoodsafetyApiError(Exception):
    pass


def parse_page(payload: Any) -> tuple[int, list[dict[str, Any]]]:
    """API 응답 한 쪽 → (전체 건수, 행 목록). 결과 코드가 정상(INFO-000)이 아니면 FoodsafetyApiError."""
    body = payload.get(SERVICE_ID) if isinstance(payload, dict) else None
    if not isinstance(body, dict):
        # 인증키 오류 등은 {"RESULT": {...}}만 오기도 한다
        result = payload.get("RESULT", {}) if isinstance(payload, dict) else {}
        raise FoodsafetyApiError(f"응답 형식이 다릅니다: {result.get('CODE')} {result.get('MSG')}".strip())
    result = body.get("RESULT") or {}
    code = result.get("CODE")
    if code == "INFO-200":  # 해당하는 데이터가 없음
        return int(body.get("total_count") or 0), []
    if code != "INFO-000":
        raise FoodsafetyApiError(f"{code} {result.get('MSG')}")
    return int(body["total_count"]), list(body.get("row") or [])


def split_outside_parens(text: str) -> list[str]:
    """쉼표(괄호 밖)로 나눈다. "달걀 30g(1/2개, 노른자)"의 괄호 안 쉼표는 나누지 않는다."""
    out, buf, depth = [], [], 0
    for ch in text:
        if ch in "([（［":
            depth += 1
        elif ch in ")]）］" and depth:
            depth -= 1
        if ch in ",，、" and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    out.append("".join(buf))
    return [s.strip() for s in out if s.strip()]


def ingredient_segments(parts: str, title: str) -> list[str]:
    """재료정보 원문 → 재료 표기 목록(원문 순서). 레시피 이름 줄과 머리말만 버린다."""
    title_norm = normalize_term(title)
    out: list[str] = []
    for raw_line in parts.replace("\r", "\n").split("\n"):
        line = _BULLET.sub("", raw_line).strip()
        if m := _BRACKET_HEAD.match(line):
            if normalize_term(m.group(1)) in HEADER_WORDS or not line[m.end():].strip():
                line = line[m.end():]
        if ":" in line or "：" in line:
            head, _, rest = line.replace("：", ":").partition(":")
            # "양념장 : 간장 1큰술", "재료(2인분) :" → 머리말을 뗀다. 머리말이 아니면("땅콩: 10g") 줄을 그대로 둔다
            head_norm = normalize_term(_PAREN.sub("", head))
            if not head_norm or head_norm in HEADER_WORDS or head_norm == title_norm:
                line = rest
        line = line.strip()
        norm = normalize_term(line)
        if not norm or norm == title_norm or norm in HEADER_WORDS:
            continue
        out.extend(split_outside_parens(line))
    return out


def ingredient_name(segment: str) -> str:
    """"연두부 75g(3/4모)" → "연두부". 양 표기가 없으면 원문 그대로."""
    m = _AMOUNT_START.search(segment)
    name = segment[: m.start()] if m else segment
    return name.strip().rstrip(":：").strip() or segment.strip()


def match_ingredient(segment: str, alias_index: Mapping[str, str], concept_ids: frozenset[str]) -> str | None:
    """정확 일치만. 이름 → 원문 전체 순으로 본다. concept 노드는 레시피 재료로 쓸 수 없으므로 미매칭."""
    for key in (normalize_term(ingredient_name(segment)), normalize_term(segment)):
        ing = alias_index.get(key)
        if ing is not None:
            return None if ing in concept_ids else ing
    return None


def clean_step(text: str) -> str:
    """"1. 새우를 데친다.a" → "새우를 데친다." (API 원문의 앞 번호와 끝 영문 한 글자 표식 제거)."""
    text = " ".join(text.split())
    text = _STEP_NO.sub("", text)
    if len(text) > 1 and _STEP_TAIL.search(text) and not re.search(r"[a-zA-Z]{2}\s*$", text):
        text = _STEP_TAIL.sub("", text).rstrip()
    return text


def recipe_id(row: Mapping[str, Any]) -> str:
    return f"fs_{int(str(row['RCP_SEQ']).strip())}"


@dataclass
class Conversion:
    recipes: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[tuple[str, str, str]] = field(default_factory=list)  # (id, 이름, 사유)


def convert_row(row: Mapping[str, Any], alias_index: Mapping[str, str], concept_ids: frozenset[str]) -> dict[str, Any] | None:
    """API 행 하나 → 레시피 dict(RecipeSpec 형식). 재료정보가 없으면 None."""
    rid = recipe_id(row)
    title = str(row.get("RCP_NM") or "").strip()
    segments = ingredient_segments(str(row.get("RCP_PARTS_DTLS") or ""), title)
    if not segments:
        return None
    ingredients = [
        {"ingredient": match_ingredient(seg, alias_index, concept_ids), "raw_text": seg, "role": "sub"}
        for seg in segments
    ]
    unmatched = sum(1 for i in ingredients if i["ingredient"] is None)
    steps = []
    for n in range(1, MANUAL_COUNT + 1):
        text = clean_step(str(row.get(f"MANUAL{n:02d}") or ""))
        if text:
            steps.append({"text": text})
    pat, way = (str(row.get(k) or "").strip() or "-" for k in ("RCP_PAT2", "RCP_WAY2"))
    note = (f"출처: {SOURCE_LABEL} 일련번호 {int(str(row['RCP_SEQ']).strip())}. 요리종류 {pat}, 조리방법 {way}. "
            f"자동 변환: role(모두 sub)·cuisine·조리시간·난이도·맛은 검수 때 정함")
    if unmatched:
        note += f". 미매칭 재료 {unmatched}개"
    return {
        "id": rid,
        "title": title or rid,
        "cuisine": UNCLASSIFIED_CUISINE,
        "source": SOURCE,
        "status": "draft",
        "confidence": "low",
        "note": note,
        "ingredients": ingredients,
        "steps": steps,
    }


def convert_rows(rows: list[Mapping[str, Any]], alias_index: Mapping[str, str], concept_ids: frozenset[str]) -> Conversion:
    out = Conversion()
    for row in rows:
        recipe = convert_row(row, alias_index, concept_ids)
        if recipe is None:
            out.skipped.append((recipe_id(row), str(row.get("RCP_NM") or "").strip(), "재료 정보 없음"))
        else:
            out.recipes.append(recipe)
    out.recipes.sort(key=lambda r: int(r["id"][3:]))
    return out
