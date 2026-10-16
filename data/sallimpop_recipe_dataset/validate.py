from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parent
RECIPE_DIR = ROOT / "recipes"
REQUIRED_TOP = {
    "id", "title", "cuisine", "difficulty", "cook_time_min", "servings", "source",
    "status", "confidence", "note", "ingredients", "taste", "equipment", "steps",
}
CUISINES = {"한식", "일식", "중식", "양식", "기타"}
ROLES = {"main", "sub", "seasoning", "garnish"}
TECHNIQUES = {"볶음", "구이", "조림", "찜", "튀김", "부침", "끓이기", "무침", "데치기", "베이킹", None}
TASTE_KEYS = {"spicy", "salty", "sweet", "sour", "umami", "savory"}
SOURCE_KEYS = {"type", "channel", "channel_url", "video_title", "video_url", "published_at", "retrieved_at"}
INGREDIENT_KEYS = {"name", "raw_text", "role", "optional", "amount", "unit"}
EQUIPMENT_KEYS = {"name", "required"}
STEP_KEYS = {"text", "technique"}
ID_RE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"YAML 읽기 실패: {exc}"]
    if not isinstance(data, dict):
        return ["최상위 값이 객체가 아님"]

    missing = REQUIRED_TOP - set(data)
    if missing:
        errors.append(f"필수 필드 누락: {sorted(missing)}")
    if errors:
        return errors

    if data["id"] != path.stem:
        errors.append("id와 파일 이름이 일치하지 않음")
    if not isinstance(data["id"], str) or not ID_RE.fullmatch(data["id"]):
        errors.append("id가 영문 소문자 snake_case가 아님")
    if not isinstance(data["title"], str) or not data["title"].strip():
        errors.append("title이 비어 있음")
    if data["cuisine"] not in CUISINES:
        errors.append("cuisine 허용 값 위반")
    if data["difficulty"] not in {1, 2, 3}:
        errors.append("difficulty는 1~3이어야 함")
    if not isinstance(data["cook_time_min"], int) or data["cook_time_min"] <= 0:
        errors.append("cook_time_min은 양의 정수여야 함")
    if data["servings"] is not None and (not isinstance(data["servings"], int) or data["servings"] <= 0):
        errors.append("servings는 null 또는 양의 정수여야 함")
    if data["status"] != "draft":
        errors.append("status는 draft여야 함")
    if data["confidence"] not in {"high", "low"}:
        errors.append("confidence 허용 값 위반")
    if data["note"] is not None and not isinstance(data["note"], str):
        errors.append("note는 null 또는 문자열이어야 함")

    source = data["source"]
    if not isinstance(source, dict) or SOURCE_KEYS - set(source):
        errors.append("source 필수 필드 누락")
    else:
        if source["type"] != "youtube":
            errors.append("source.type은 youtube여야 함")
        if not isinstance(source["video_url"], str) or "youtube.com/watch?v=" not in source["video_url"]:
            errors.append("source.video_url 형식 오류")
        else:
            video_id = source["video_url"].split("watch?v=", 1)[1].split("&", 1)[0]
            suffix = re.sub(r"[^a-z0-9]+", "_", video_id[:6].lower()).strip("_")
            if not data["id"].endswith("_" + suffix):
                errors.append("id에 영상 ID 앞 6자리 정규화 값이 없음")
        for key in ("published_at", "retrieved_at"):
            if source[key] is not None and (not isinstance(source[key], str) or not DATE_RE.fullmatch(source[key])):
                errors.append(f"source.{key} 날짜 형식 오류")

    ingredients = data["ingredients"]
    if not isinstance(ingredients, list) or not ingredients:
        errors.append("ingredients가 비어 있음")
    else:
        seen = set()
        for i, item in enumerate(ingredients):
            if not isinstance(item, dict) or INGREDIENT_KEYS - set(item):
                errors.append(f"ingredients[{i}] 필수 필드 누락")
                continue
            if not isinstance(item["name"], str) or not item["name"].strip():
                errors.append(f"ingredients[{i}].name 오류")
            if item["name"] in seen:
                errors.append(f"중복 재료 name: {item['name']}")
            seen.add(item["name"])
            if item["role"] not in ROLES:
                errors.append(f"ingredients[{i}].role 허용 값 위반")
            if not isinstance(item["optional"], bool):
                errors.append(f"ingredients[{i}].optional은 bool이어야 함")
            if item["amount"] is not None and (not isinstance(item["amount"], (int, float)) or item["amount"] < 0):
                errors.append(f"ingredients[{i}].amount 오류")
            if item["unit"] is not None and not isinstance(item["unit"], str):
                errors.append(f"ingredients[{i}].unit 오류")
        if not any(x.get("role") == "main" and x.get("optional") is False for x in ingredients if isinstance(x, dict)):
            errors.append("선택이 아닌 main 재료가 없음")

    taste = data["taste"]
    if not isinstance(taste, dict) or set(taste) != TASTE_KEYS:
        errors.append("taste 필드 구성이 잘못됨")
    elif any(not isinstance(value, int) or not 0 <= value <= 5 for value in taste.values()):
        errors.append("taste 값은 0~5 정수여야 함")

    equipment = data["equipment"]
    if not isinstance(equipment, list) or not equipment:
        errors.append("equipment가 비어 있음")
    else:
        for i, item in enumerate(equipment):
            if not isinstance(item, dict) or EQUIPMENT_KEYS - set(item):
                errors.append(f"equipment[{i}] 필수 필드 누락")
            elif not isinstance(item["required"], bool):
                errors.append(f"equipment[{i}].required은 bool이어야 함")

    steps = data["steps"]
    if not isinstance(steps, list) or not steps:
        errors.append("steps가 비어 있음")
    else:
        for i, item in enumerate(steps):
            if not isinstance(item, dict) or STEP_KEYS - set(item):
                errors.append(f"steps[{i}] 필수 필드 누락")
                continue
            if not isinstance(item["text"], str) or not item["text"].strip():
                errors.append(f"steps[{i}].text 오류")
            if item["technique"] not in TECHNIQUES:
                errors.append(f"steps[{i}].technique 허용 값 위반")
    return errors


def main() -> int:
    paths = sorted(RECIPE_DIR.rglob("*.yaml"))
    if not paths:
        print("FAIL: YAML 파일이 없습니다.")
        return 1
    failures = 0
    for path in paths:
        errors = validate_file(path)
        if errors:
            failures += 1
            print(f"FAIL {path.relative_to(ROOT)}")
            for error in errors:
                print(f"  - {error}")
    if failures:
        print(f"\n검증 실패: {failures}/{len(paths)}개 파일")
        return 1
    print(f"검증 통과: {len(paths)}개 YAML 파일")
    return 0


if __name__ == "__main__":
    sys.exit(main())
