"""식품안전나라 원본 변환 (docs/plan.md 5-3-1). 실제 API 데이터가 아니라 직접 만든 예시 행을 쓴다."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from kb.datacheck import check_recipes
from kb.foodsafety import (
    FoodsafetyApiError,
    clean_step,
    convert_row,
    convert_rows,
    ingredient_name,
    ingredient_segments,
    match_ingredient,
    parse_page,
    split_outside_parens,
)
from kb.recipes import RecipeSeedError, load_recipe_specs
from tests.support.kb_builders import compile_basics

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def ck():
    return compile_basics()


@pytest.fixture(scope="module")
def index(ck):
    return {a.alias_norm: a.ingredient_id for a in ck.aliases}


def row(**overrides):
    base = {
        "RCP_SEQ": "7",
        "RCP_NM": "김치 새우 볶음",
        "RCP_PAT2": "반찬",
        "RCP_WAY2": "볶기",
        "RCP_PARTS_DTLS": "김치 새우 볶음\n●주재료 : 김치 100g(1/2컵), 새우 50g(5마리)\n양념\n소금 약간, 비법가루 1작은술",
        "MANUAL01": "1. 김치를 썬다.a",
        "MANUAL02": "2. 새우와 함께 볶는다.b",
        "MANUAL03": "",
    }
    base.update(overrides)
    return base


def test_parse_page_ok_and_errors():
    ok = {"COOKRCP01": {"total_count": "2", "row": [{"RCP_SEQ": "1"}], "RESULT": {"CODE": "INFO-000", "MSG": "정상"}}}
    assert parse_page(ok) == (2, [{"RCP_SEQ": "1"}])
    empty = {"COOKRCP01": {"total_count": "0", "RESULT": {"CODE": "INFO-200", "MSG": "없음"}}}
    assert parse_page(empty) == (0, [])
    with pytest.raises(FoodsafetyApiError, match="INFO-100"):
        parse_page({"RESULT": {"CODE": "INFO-100", "MSG": "인증키가 유효하지 않습니다"}})
    with pytest.raises(FoodsafetyApiError, match="INFO-300"):
        parse_page({"COOKRCP01": {"RESULT": {"CODE": "INFO-300", "MSG": "제한"}}})


def test_split_keeps_commas_inside_parens():
    assert split_outside_parens("달걀 30g(1/2개, 노른자), 소금 약간") == ["달걀 30g(1/2개, 노른자)", "소금 약간"]


def test_segments_drop_only_title_and_header_lines():
    segs = ingredient_segments(row()["RCP_PARTS_DTLS"], "김치 새우 볶음")
    assert segs == ["김치 100g(1/2컵)", "새우 50g(5마리)", "소금 약간", "비법가루 1작은술"]


def test_non_header_colon_line_is_kept_whole():
    """머리말이 아닌 "땅콩: 10g"을 버리면 알레르기 판정에서 빠진다. 줄을 그대로 둔다."""
    assert ingredient_segments("땅콩: 10g", "예") == ["땅콩: 10g"]
    assert ingredient_name("땅콩: 10g") == "땅콩"


def test_short_unknown_line_is_not_dropped():
    """머리말 목록에 없는 짧은 줄(예: 재료 이름만 있는 줄)은 재료로 남는다."""
    assert ingredient_segments("고명\n땅콩", "예") == ["땅콩"]


def test_html_serving_and_bracket_headers_are_removed():
    parts = "2인분 기준<br>\n• [추가 재료] 두부(100g), 부추(10g)<br />\n[ 1인분 ] 소금 약간"
    assert ingredient_segments(parts, "예") == ["두부(100g)", "부추(10g)", "소금 약간"]


def test_sub_dish_label_is_kept_as_its_own_line():
    """"●두부구이 : 두부 70g"의 "두부구이"는 머리말 목록에 없으므로 버리지 않고 따로 남긴다(정보 손실 없음)."""
    assert ingredient_segments("●두부구이 : 두부 70g, 전분 10g", "예") == ["두부구이", "두부 70g", "전분 10g"]
    assert ingredient_segments("[땅콩소스] 간장 1큰술", "예") == ["땅콩소스", "간장 1큰술"]


def test_water_is_not_an_ingredient():
    """data/recipes/README.md: 물은 재료로 적지 않는다. 이름이 정확히 "물"일 때만 뺀다."""
    assert ingredient_segments("물 30ml(2큰술), 물전분 1큰술", "예") == ["물전분 1큰술"]


def test_skipped_items_are_reported_in_order():
    """외부 레시피 분석(부록 E)은 버린 항목을 화면에 보여 준다. 버리는 규칙은 그대로다."""
    skipped: list[str] = []
    segs = ingredient_segments("[양념장] 간장 1큰술\n2인분 기준\n물 200ml, 두부 1모", "예", skipped)
    assert segs == ["간장 1큰술", "두부 1모"]
    assert skipped == ["양념장", "2인분 기준", "물 200ml"]


def test_ingredient_name_and_exact_match(index, ck):
    assert ingredient_name("연두부 75g(3/4모)") == "연두부"
    assert ingredient_name("소금 약간") == "소금"
    assert match_ingredient("김치 100g", index, ck.concept_ids) == "kimchi"  # 별칭
    assert match_ingredient("다진 새우 50g", index, ck.concept_ids) is None  # 정확 일치만
    assert match_ingredient("해산물 200g", index, ck.concept_ids) is None  # concept 노드는 미매칭


def test_clean_step():
    assert clean_step("1. 김치를 썬다.a") == "김치를 썬다."
    assert clean_step("소스에 MSG 대신 간장") == "소스에 MSG 대신 간장"


def test_convert_row_shape(index, ck):
    r = convert_row(row(), index, ck.concept_ids)
    assert r["id"] == "fs_7" and r["title"] == "김치 새우 볶음"
    assert (r["cuisine"], r["source"], r["status"], r["confidence"]) == ("미분류", "foodsafety", "draft", "low")
    assert "cook_time_min" not in r and "taste" not in r
    assert [i["ingredient"] for i in r["ingredients"]] == ["kimchi", "shrimp_raw", "salt", None]
    assert {i["role"] for i in r["ingredients"]} == {"sub"}
    assert [s["text"] for s in r["steps"]] == ["김치를 썬다.", "새우와 함께 볶는다."]
    assert "식품안전나라" in r["note"] and "일련번호 7" in r["note"] and "미매칭 재료 1개" in r["note"]


def test_converted_recipe_passes_validation_except_unmapped(index, ck):
    # draft의 미매칭(null)은 검증 오류가 아니다(plan 5-4, 자취요리신 연결 때 승인). 엔진은 알레르기 사용자에게 제외한다.
    r = convert_row(row(), index, ck.concept_ids)
    assert any(i["ingredient"] is None for i in r["ingredients"])
    assert check_recipes(ck, [("fs_7", r)]) == []
    assert "unmapped" in {i.code for i in check_recipes(ck, [("fs_7", {**r, "status": "published"})])}  # published는 계속 오류


def test_row_without_parts_is_skipped(index, ck):
    conv = convert_rows([row(RCP_SEQ="9", RCP_PARTS_DTLS=""), row()], index, ck.concept_ids)
    assert [r["id"] for r in conv.recipes] == ["fs_7"]
    assert conv.skipped == [("fs_9", "김치 새우 볶음", "재료 정보 없음")]


def test_converted_recipes_load_with_unknown_fields(index, ck, tmp_path):
    """ar-1: cuisine 미분류·조리시간·난이도·맛이 없어도 draft로 엔진·DB에 적재되고, 엔진은 그 값을 '모름'(None)으로 둔다."""
    from storage.engine_source import recipe_from_spec

    r = convert_row(row(RCP_PARTS_DTLS="김치 100g, 소금 약간"), index, ck.concept_ids)
    (tmp_path / "fs_7.yaml").write_text(yaml.safe_dump(r, allow_unicode=True), encoding="utf-8")
    [spec] = load_recipe_specs(ck, tmp_path)
    recipe = recipe_from_spec(spec)
    assert (spec.cuisine, spec.status) == ("미분류", "draft")
    assert recipe.cook_time_min is None and recipe.difficulty is None and recipe.taste is None


def test_convert_script_end_to_end(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("convert_foodsafety", ROOT / "scripts" / "convert_foodsafety.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "compile_paths", lambda *_: compile_basics())
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"fetched_on": "2026-10-16", "rows": [row(), row(RCP_SEQ="8", RCP_PARTS_DTLS="")]},
                              ensure_ascii=False), encoding="utf-8")
    out_dir, review = tmp_path / "out", tmp_path / "review.md"
    assert module.main(["--raw", str(raw), "--out-dir", str(out_dir), "--review", str(review)]) == 0
    assert [p.name for p in out_dir.glob("*.yaml")] == ["fs_7.yaml"]
    text = review.read_text(encoding="utf-8")
    assert "변환한 레시피: 1개, 재료정보가 없어 건너뜀: 1개" in text
    assert "| 1 | 비법가루 | 1 | 1 |" in text


def _fetch_module():
    spec = importlib.util.spec_from_file_location("fetch_foodsafety", ROOT / "scripts" / "fetch_foodsafety.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_fetch_requires_key(monkeypatch):
    module = _fetch_module()
    monkeypatch.setattr(module, "load_dotenv", lambda: None)
    monkeypatch.delenv("FOODSAFETY_API_KEY", raising=False)
    assert module.main([]) == 2


def test_fetch_pages_until_total_and_never_saves_key(monkeypatch, tmp_path):
    module = _fetch_module()
    monkeypatch.setattr(module, "load_dotenv", lambda: None)
    monkeypatch.setenv("FOODSAFETY_API_KEY", "secret-key")
    monkeypatch.setattr(module, "PAGE_SIZE", 2)
    calls = []

    def fake_fetch(key, start, end, timeout):
        calls.append((start, end))
        rows = [{"RCP_SEQ": str(n)} for n in range(start, min(end, 3) + 1)]
        return {"COOKRCP01": {"total_count": "3", "row": rows, "RESULT": {"CODE": "INFO-000"}}}

    monkeypatch.setattr(module, "fetch_page", fake_fetch)
    out = tmp_path / "raw.json"
    assert module.main(["--out", str(out)]) == 0
    assert calls == [(1, 2), (3, 4)]
    text = out.read_text(encoding="utf-8")
    assert "secret-key" not in text
    assert [r["RCP_SEQ"] for r in json.loads(text)["rows"]] == ["1", "2", "3"]


def test_inline_separators_start_new_lines():
    assert ingredient_segments("소금 0.5g - 양념장 : 간장 3g", "예") == ["소금 0.5g", "간장 3g"]
    assert ingredient_segments("크림치즈 > 우유 875ml", "예") == ["크림치즈", "우유 875ml"]
    assert ingredient_segments("닭가슴살 60g [소스소개] 매운소스", "예") == ["닭가슴살 60g", "매운소스"]
    assert ingredient_segments("치킨-스톡 1큰술", "예") == ["치킨-스톡 1큰술"]


def _viewer_module():
    spec = importlib.util.spec_from_file_location("make_foodsafety_viewer", ROOT / "scripts" / "make_foodsafety_viewer.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_viewer_records_and_safe_embedding(index, ck):
    module = _viewer_module()
    rows = [row(MANUAL_IMG01="http://example.test/1.png", INFO_ENG="220", RCP_NM="</script><b>x</b>"),
            row(RCP_SEQ="9", RCP_PARTS_DTLS="")]
    recs = module.viewer_records(rows, index, ck.concept_ids, {"kimchi": "배추김치"})
    assert [r["id"] for r in recs] == ["fs_7"]  # 재료정보 없는 행은 변환기와 같이 뺀다
    r = recs[0]
    # 이름이 바뀌어 첫 줄("김치 새우 볶음")이 레시피 이름 줄로 걸러지지 않고 미매칭 재료로 남는다
    assert r["miss"] == 2 and {"t": "김치 100g(1/2컵)", "id": "kimchi", "name": "배추김치"} in r["ings"]
    assert r["steps"][0] == {"t": "김치를 썬다.", "img": "http://example.test/1.png"}
    assert r["nut"][0] == ["열량", 220.0, "kcal"]
    html = module.render(recs, "2026-10-16")
    payload = html.split('<script type="application/json" id="data">', 1)[1].split("</script>", 1)[0]
    assert "</script" not in payload  # 데이터가 스크립트 태그를 닫지 못한다
    assert json.loads(payload.replace("<\/", "</"))["recipes"][0]["title"] == "</script><b>x</b>"
