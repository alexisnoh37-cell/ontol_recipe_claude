"""미매칭 4차 정리(um-5): 사람 검수 결정(꼭 확인 25개 모두 O)과 메모가 지식·이름 보정표·시판 안내에 반영됐는지.

결정 원본: docs/review/unmapped_round4.yaml, 사람 내보내기 docs/review/unmapped_round4_decisions.json.
"""

from __future__ import annotations

import json
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
    return load_proposal(REVIEW / "unmapped_round4.yaml")


@pytest.fixture(scope="module")
def ck():
    return compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")


@pytest.fixture(scope="module")
def index(ck):
    return alias_index(ck)


def test_every_item_follows_the_human_decision(entries):
    rows = json.loads((REVIEW / "unmapped_round4_decisions.json").read_text(encoding="utf-8"))
    assert rows["format"] == "unmapped-round4-decisions/1"
    decided = {r["id"]: r["decision"] for r in rows["rows"]}
    assert len(decided) == 25 and set(decided.values()) == {"O"}
    assert all(e.decision == "O" for e in entries)


def test_terms_are_applied(entries, ck, index):
    fs_fix = load_name_overrides(ROOT, ck, NAME_OVERRIDES)
    eng_fix = load_name_overrides(ROOT, ck)
    status = {i.id: i.status for i in ck.ingredients}
    for e in entries:
        keys = [normalize_term(t) for t in e.texts]
        if e.kind == "E":
            assert status[e.new["id"]] == "reviewed"
            for k in keys:
                assert index.get(k) == e.new["id"] or fs_fix.get(k) == {"id": e.new["id"]}, k
        elif e.kind == "D":
            fix = {"split": e.split} if e.split else {"drop": e.drop} if e.drop else {"id": e.target}
            for k in keys:
                assert fs_fix.get(k) == fix or eng_fix.get(k) == fix, k
        else:
            for k in keys:
                assert k not in index and k not in fs_fix and k not in eng_fix


def test_only_one_unmapped_line_is_left(ck):
    assert not engine_unmapped(ROOT, ck).terms
    fs = foodsafety_unmapped(ROOT)
    assert set(fs.terms) == {"10g"} and len(fs.by_recipe) == 1  # 원문에 재료 이름이 없는 줄(fs_3069)


def test_memos_add_commercial_notice_but_not_for_zucchini():
    notice = set(yaml.safe_load((ROOT / "config" / "display.yaml").read_text(encoding="utf-8"))
                 ["commercial_product_notice"]["ingredients"])
    assert {"gat_jangajji", "cocoa_mix", "kiwi_sauce", "basil_rub", "meal_kit_sauce", "hotteok_mix",
            "instant_noodle_product", "instant_stock"} <= notice
    assert "zucchini" not in notice and "edible_flower" not in notice


def test_split_text_gives_each_line_its_own_name(ck, index):
    fixes = {normalize_term("."): {"split": [{"id": "broccoli", "text": "브로콜리"}, {"id": "milk", "text": "우유"}]}}
    r = convert_row({"RCP_SEQ": "1", "RCP_NM": "예", "RCP_PARTS_DTLS": "."}, index, ck.concept_ids, fixes)
    assert [(i["ingredient"], i["raw_text"]) for i in r["ingredients"]] == [("broccoli", "브로콜리"), ("milk", "우유")]


def test_subtitle_rule_runs_before_name_overrides(ck, index):
    """보정표의 '볶음 소스'(간편식 소스)는 재료 줄에만, 구성 재료가 적힌 소제목 '볶음소스:'는 지금처럼 뺀다."""
    fixes = {normalize_term("볶음 소스"): {"id": "meal_kit_sauce"}}
    r = convert_row({"RCP_SEQ": "1", "RCP_NM": "예", "RCP_PARTS_DTLS": "볶음소스: 굴소스 1g, 대파 13g"},
                    index, ck.concept_ids, fixes)
    assert [i["ingredient"] for i in r["ingredients"]] == ["oyster_sauce", "green_onion"]
    r = convert_row({"RCP_SEQ": "1", "RCP_NM": "예", "RCP_PARTS_DTLS": "양파 110g, 볶음 소스(20g)"}, index, ck.concept_ids, fixes)
    assert [i["ingredient"] for i in r["ingredients"]] == ["onion", "meal_kit_sauce"]


def test_number_with_gaji_is_a_name_not_an_amount():
    assert ingredient_segments("곁들이채소2 : 2가지색 미니파프리카 30g, 양파 60g", "예") == \
        ["곁들이채소2", "2가지색 미니파프리카 30g", "양파 60g"]
