"""미매칭 3차 정리(um-4): 사람이 승인한 추천안 1~6이 지식·이름 보정표·변환 규칙에 반영됐는지.

결정 원본: docs/review/unmapped_round3.yaml(2026-10-18 사람 승인 "진행해").
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from kb import compile_paths
from kb.foodsafety import NAME_OVERRIDES, convert_row, ingredient_segments
from kb.text import normalize_term
from kb.unmapped_review import engine_unmapped, foodsafety_unmapped, load_proposal
from kb.youtube_seed import alias_index, load_name_overrides

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "docs" / "review"


@pytest.fixture(scope="module")
def entries():
    return load_proposal(REVIEW / "unmapped_round3.yaml")


@pytest.fixture(scope="module")
def ck():
    return compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")


@pytest.fixture(scope="module")
def index(ck):
    return alias_index(ck)


@pytest.fixture(scope="module")
def overrides(ck):
    return load_name_overrides(ROOT, ck, NAME_OVERRIDES)


def test_all_decisions_are_approved(entries):
    assert entries and all(e.decision == "O" for e in entries)


def test_approved_terms_map(entries, ck, index, overrides):
    status = {i.id: i.status for i in ck.ingredients}
    for e in entries:
        if e.kind in ("A", "B", "E"):
            expected = e.new["id"] if e.new else e.target
            assert status[expected] == "reviewed", expected
            for t in e.texts:
                assert index.get(normalize_term(t)) == expected or overrides.get(normalize_term(t)) == {"id": expected}, t
        elif e.kind == "D":
            fix = {"split": e.split} if e.split else {"drop": e.drop} if e.drop else {"id": e.target}
            for t in e.texts:
                assert overrides[normalize_term(t)] == fix, t
        else:  # C: 미매칭 유지
            for t in e.texts:
                assert normalize_term(t) not in index and normalize_term(t) not in overrides, t


def test_ambiguous_terms_take_every_candidate_allergen(ck):
    def groups(i):
        return {r.allergen_group_id: r.certainty for r in ck.allergen_closure if r.ingredient_id == i}

    assert groups("green_onion_unspecified") == {} and groups("chili_unspecified") == {}  # 후보 모두 알레르기 없음
    assert groups("sesame_unspecified") == {"sesame": "possible"}
    assert groups("meat_unspecified") == {"beef": "possible", "pork": "possible"}
    assert {"peach", "tomato"} <= set(groups("fruit_unspecified"))
    assert {"shrimp", "crab", "squid", "shellfish", "mackerel", "beef", "pork", "chicken", "soybean", "wheat"} \
        <= set(groups("stock_unspecified"))
    assert {"shrimp", "other_fish"} <= set(groups("green_curry_paste"))
    assert {"egg", "wheat", "soybean"} <= set(groups("mustard_sauce"))


def test_commercial_sauces_get_notice(entries):
    notice = set(yaml.safe_load((ROOT / "config" / "display.yaml").read_text(encoding="utf-8"))
                 ["commercial_product_notice"]["ingredients"])
    assert {e.new["id"] for e in entries if e.kind == "E"} <= notice


def test_converted_recipes_leave_only_human_held_terms(ck):
    """남은 미매칭은 1~3차에서 사람이 보류(C)·제외(X)한 표기뿐(식품안전나라·엔진 모두)."""
    held = set()
    for name in ("unmapped_proposal.yaml", "unmapped_round2.yaml", "unmapped_round3.yaml"):
        held |= {normalize_term(t) for e in load_proposal(REVIEW / name) if e.kind == "C" or e.decision == "X" for t in e.texts}
    fs = foodsafety_unmapped(ROOT)
    eng = engine_unmapped(ROOT, ck)
    assert set(fs.terms) <= held
    assert set(eng.terms) <= held
    assert sum(u.lines for u in fs.terms.values()) <= 30


def _row(parts):
    return {"RCP_SEQ": "1", "RCP_NM": "예", "RCP_PARTS_DTLS": parts}


def test_unmapped_subtitles_are_dropped_but_ingredients_kept(ck, index):
    """구성 재료가 따로 적힌 소제목 줄은 빼고, 재료로 연결되는 소제목은 남긴다(연결된 재료 손실 없음)."""
    r = convert_row(_row("●구이소스 : 된장 15g, 꿀 30g\n[겉절이양념] 고춧가루 25g\n겉절이양념(15g), 두부 50g"), index, ck.concept_ids)
    assert [(i["ingredient"], i["raw_text"]) for i in r["ingredients"]] == [
        ("doenjang", "된장 15g"), ("honey", "꿀 30g"), ("gochugaru", "고춧가루 25g"), ("tofu", "두부 50g")]
    assert "소제목 줄 3개 뺌" in r["note"]
    # 소제목 이름이 재료면 그대로 둔다: "[팥소]팥 15g" → 팥소(팥앙금)와 팥 모두 남음
    r = convert_row(_row("밀가루 20g [팥소]팥 15g, 설탕 10g"), index, ck.concept_ids)
    assert "bean_paste_sweet" in [i["ingredient"] for i in r["ingredients"]]
    # 소제목이 아닌 미매칭 줄은 그대로 미매칭
    r = convert_row(_row("키위소스 20g, 두부 50g"), index, ck.concept_ids)
    assert [i["ingredient"] for i in r["ingredients"]] == [None, "tofu"]


def test_segments_report_subtitles():
    subs: set[str] = set()
    segs = ingredient_segments("●오이무침 :\n오이 70g\n두부 10g, 초코크림 : 아몬드가루 85g", "예", subtitles=subs)
    assert segs == ["오이무침", "오이 70g", "두부 10g", "초코크림", "아몬드가루 85g"]  # 목록은 그대로(외부 분석 화면 호환)
    assert {"오이무침", "초코크림"} <= subs
