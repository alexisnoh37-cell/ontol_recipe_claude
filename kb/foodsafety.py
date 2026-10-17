"""식품안전나라 조리식품 레시피 DB(COOKRCP01) 원본 → 레시피 YAML dict 변환 (docs/plan.md 5-3-1).

결정적 규칙만 쓴다(LLM·확률적 매핑 없음). 재료 이름이 별칭 색인과 정확히 일치할 때만 정규 id를 채우고,
나머지는 None(미매칭)으로 둔다. 미매칭 재료가 있는 레시피는 알레르기 사용자에게 제외된다(안전 규칙).
재료 줄을 잘못 버리면 알레르기 판정에서 빠지므로, 버리는 줄은 레시피 이름과 고정된 머리말 단어뿐이다.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from kb.datacheck import UNCLASSIFIED_CUISINE
from kb.text import normalize_term

SERVICE_ID = "COOKRCP01"
NAME_OVERRIDES = Path("data") / "foodsafety_name_overrides.yaml"  # 재료 이름 보정표(um-3)
SOURCE = "foodsafety"
SOURCE_LABEL = "식품의약품안전처 식품안전나라 조리식품의 레시피 DB(COOKRCP01)"
MANUAL_COUNT = 20

# 재료정보에서 재료가 아니라 묶음 머리말로 쓰이는 단어(정확히 일치할 때만 버린다)
HEADER_WORDS = frozenset(normalize_term(w) for w in (
    "재료", "주재료", "부재료", "필수재료", "선택재료", "기본재료", "고명", "고명재료", "양념", "양념장", "양념재료",
    "소스", "소스재료", "드레싱", "육수", "반죽", "속재료", "토핑", "곁들임", "밑간", "절임물", "조림장", "소스소개",
    "장식",  # um-2 사람 결정(2026-10-17)
))
_BULLET = re.compile(r"^[\s●•·○◎■□◆◇▶▷★☆※*\-]+")
_BRACKET_HEAD = re.compile(r"^[\[［【<〈(（]([^\]］】>〉)）]{1,15})[\]］】>〉)）]\s*")
# 양 표기가 시작되는 지점: 숫자, 여는 괄호, 분수 문자, 양 단어
_AMOUNT_START = re.compile(r"[0-9０-９½⅓⅔¼¾(（]|약간|적당량|적당히|조금|소량|한줌|한꼬집")
_NOT_AMOUNT = re.compile(r"\d+\s*가지")  # "2가지색 미니파프리카"의 '2가지'는 양이 아니라 이름(um-5)
_PAREN = re.compile(r"[(（][^)）]*[)）]")
_HTML_TAG = re.compile(r"<\s*/?\s*[a-zA-Z]+[^>]{0,10}>")
_MID_BRACKET = re.compile(r"\[([^\[\]\n]{1,15})\]")
_DASH_SEP = re.compile(r"(?:^|\s)-\s+", re.MULTILINE)  # 공백 사이 하이픈만(재료 이름 속 "-"는 그대로)
# 양 표기 뒤에 소제목과 쌍점이 이어지는 줄("다진 마늘 2 국물: 멸치국물", "황설탕(7g) 호떡소: 검정깨")은
# 소제목부터 새 줄로 나눈다(um-3). 나누지 않으면 쌍점 뒤 재료가 앞 재료 줄에 묻혀 알레르기 판정에서 빠진다.
_MID_LABEL = re.compile(r"([0-9０-９][0-9./]*\s*[a-zA-Z가-힣]{0,3}\)?)[ \t]+(?=[^\s:：,，][^:：,，\n]{0,20}[:：])")
_LABEL_NO = re.compile(r"\d+$")  # "소스1 발사믹식초"의 머리말 번호
_SERVING = re.compile(r"^\d+(?:~\d+)?인분(?:기준|분량)?$")  # "2인분", "2인분 기준"(정규화 후)
# 재료로 적지 않는 것(data/recipes/README.md "물은 재료로 적지 않는다"). 이름이 정확히 일치할 때만
NOT_INGREDIENTS = frozenset(normalize_term(w) for w in ("물",))
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


def _starts_with_amount(text: str) -> bool:
    """쌍점 오른쪽이 양 표기로 시작하는지("땅콩: 10g"). '2가지색 …'처럼 숫자로 시작하는 이름은 양이 아니다."""
    return _AMOUNT_START.match(text) is not None and _NOT_AMOUNT.match(text) is None


def _is_label(norm: str, title_norm: str) -> bool:
    """버려도 되는 묶음 머리말: 고정 단어, 레시피 이름, 분량("2인분 기준"), "…재료"(예: 추가 재료)."""
    return (not norm or _LABEL_NO.sub("", norm) in HEADER_WORDS or norm == title_norm  # "[소스1]"도 머리말(um-3)
            or bool(_SERVING.match(norm)) or norm.endswith("재료"))


def _strip_label_prefix(item: str, skipped: list[str] | None) -> str:
    """"재료 닭가슴살 100g", "양념 다진 마늘"처럼 머리말 단어가 공백으로만 붙은 항목에서 머리말을 뗀다(um-2).

    뒤가 양 표기로 시작하면("소스 1큰술") 머리말이 아니라 재료 이름이므로 그대로 둔다.
    """
    head, _, rest = item.strip().partition(" ")
    rest = rest.strip()
    head_norm = _LABEL_NO.sub("", normalize_term(head))  # "소스1", "양념2"도 머리말(um-3)
    if rest and head_norm in HEADER_WORDS and _AMOUNT_START.match(rest) is None:
        if skipped is not None:
            skipped.append(head)
        return rest
    return item


def ingredient_segments(parts: str, title: str, skipped: list[str] | None = None,
                        subtitles: set[str] | None = None) -> list[str]:
    """재료정보 원문 → 재료 표기 목록(원문 순서).

    버리는 것은 머리말(_is_label)과 물뿐이다. 머리말이 아닌 소제목("●두부구이 : 두부 70g"의 "두부구이",
    "[소스] …"의 "소스" 외 값)은 버리지 않고 따로 한 항목으로 남긴다(미매칭으로 검수표에 오른다).
    skipped를 주면 버린 항목(빈 문자열 제외)을 원문 순서로 덧붙인다(외부 레시피 분석이 화면에 보여 준다).
    subtitles를 주면 쌍점·대괄호로 구분된 소제목(뒤에 구성 재료가 적힌 것)의 정규화 이름을 넣는다(um-4,
    convert_row가 재료로 연결되지 않은 소제목 줄을 뺄 때 쓴다).
    """
    title_norm = normalize_term(title)
    out: list[str] = []
    text = _HTML_TAG.sub("\n", parts).replace("\r", "\n")
    text = _MID_BRACKET.sub(r"\n[\1]", text)  # "… 9g [소스소개] 소스" → 대괄호부터 새 줄
    text = _DASH_SEP.sub("\n", text).replace(">", ":").replace("＞", ":")  # " - 양념장 : …", "크림치즈 > 우유"
    text = _MID_LABEL.sub(r"\1\n", text)
    for raw_line in text.split("\n"):
        line = _BULLET.sub("", raw_line).strip()
        labels: list[str] = []
        if m := _BRACKET_HEAD.match(line):
            labels.append(m.group(1).strip())
            line = _BULLET.sub("", line[m.end():]).strip()
        if ":" in line or "：" in line:
            head, _, rest = line.replace("：", ":").partition(":")
            rest = rest.strip()
            if not rest:
                line = head
                if subtitles is not None:
                    subtitles.add(normalize_term(_PAREN.sub("", head)))  # "●오이무침 :" 다음 줄에 구성 재료
            elif not _starts_with_amount(rest) and len(split_outside_parens(head)) == 1:
                # "양념장 : 간장 1큰술", "두부구이 : 두부 70g" → 소제목과 재료를 나눈다.
                # "땅콩: 10g"처럼 오른쪽이 양으로 시작하면 한 재료이므로 그대로 둔다.
                # 왼쪽에 쉼표 목록이 있으면("두부 10g, 초코크림 : 아몬드가루") 아래에서 항목별로 나눈다
                labels.append(_PAREN.sub("", head).strip())
                line = rest
        items: list[str] = []
        for item in split_outside_parens(line.strip()):
            head, sep, rest = item.replace("：", ":").partition(":")
            if sep and rest.strip() and not _starts_with_amount(rest.strip()):
                # 쉼표 목록 속 "초코크림 : 아몬드가루 85g"(um-3): 소제목과 재료를 나눈다
                items += [_PAREN.sub("", head).strip(), rest.strip()]
                if subtitles is not None:
                    subtitles.add(normalize_term(_PAREN.sub("", head)))
            else:
                items.append(item)
        if subtitles is not None:
            for lab in labels:
                subtitles.add(normalize_term(lab))
                subtitles.add(normalize_term(_strip_label_prefix(lab, None)))  # "곁들임 채소" → "채소"
        for item in labels + items:
            item = _strip_label_prefix(item, skipped)
            norm = normalize_term(item)
            if _is_label(norm, title_norm) or normalize_term(ingredient_name(item)) in NOT_INGREDIENTS:
                if skipped is not None and norm:
                    skipped.append(item)
                continue
            out.append(item)
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


def convert_row(row: Mapping[str, Any], alias_index: Mapping[str, str], concept_ids: frozenset[str],
                overrides: Mapping[str, dict] | None = None) -> dict[str, Any] | None:
    """API 행 하나 → 레시피 dict(RecipeSpec 형식). 재료정보가 없으면 None.

    overrides는 이름 보정표(data/foodsafety_name_overrides.yaml, um-3)를 kb.youtube_seed.load_name_overrides로 읽은 것.
    재료 이름(양 표기 앞, 정규화)이 표에 있으면 별칭 색인보다 먼저 적용한다: id(그 재료) · drop(뺌) · split(여러 재료).
    """
    rid = recipe_id(row)
    title = str(row.get("RCP_NM") or "").strip()
    subtitles: set[str] = set()
    segments = ingredient_segments(str(row.get("RCP_PARTS_DTLS") or ""), title, subtitles=subtitles)
    if not segments:
        return None
    ingredients = []
    fixed = dropped = 0
    for seg in segments:
        fix = (overrides or {}).get(normalize_term(ingredient_name(seg)))
        if fix is None:
            ids = [match_ingredient(seg, alias_index, concept_ids)]
            if ids == [None] and {normalize_term(ingredient_name(seg)), normalize_term(seg)} & subtitles:
                # um-4: 재료로 연결되지 않는 소제목("구이소스", "곁들임채소")과 그 소제목을 가리키는 줄("겉절이 양념 15g")은
                # 구성 재료가 소제목 뒤에 따로 적혀 있으므로 재료 줄로 남기지 않는다. 재료로 연결되는 소제목("팥소")은 그대로 둔다
                dropped += 1
                continue
        else:
            fixed += 1
            ids = [fix["id"]] if "id" in fix else [p["id"] for p in fix.get("split", [])]
        ingredients += [{"ingredient": i, "raw_text": seg, "role": "sub"} for i in ids]
    if not ingredients:
        return None
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
    if fixed:
        note += f". 이름 보정표로 고친 줄 {fixed}개"
    if dropped:
        note += f". 구성 재료가 따로 적힌 소제목 줄 {dropped}개 뺌"
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


def convert_rows(rows: list[Mapping[str, Any]], alias_index: Mapping[str, str], concept_ids: frozenset[str],
                 overrides: Mapping[str, dict] | None = None) -> Conversion:
    out = Conversion()
    for row in rows:
        recipe = convert_row(row, alias_index, concept_ids, overrides)
        if recipe is None:
            out.skipped.append((recipe_id(row), str(row.get("RCP_NM") or "").strip(), "재료 정보 없음"))
        else:
            out.recipes.append(recipe)
    out.recipes.sort(key=lambda r: int(r["id"][3:]))
    return out
