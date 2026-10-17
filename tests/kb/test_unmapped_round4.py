"""미매칭 4차 정리(um-5): 바로 반영한 것은 반영되고, 꼭 확인 항목은 사람 결정 전까지 미매칭으로 남는지.

결정 원본: docs/review/unmapped_round4.yaml. decision O = 바로 반영, null = 꼭 확인(검수 화면 unmapped_round4_review.html).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kb import compile_paths
from kb.foodsafety import NAME_OVERRIDES, convert_row, ingredient_segments
from kb.text import normalize_term
from kb.unmapped_review import load_proposal
from kb.youtube_seed import alias_index, load_name_overrides

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def entries():
    return load_proposal(ROOT / "docs" / "review" / "unmapped_round4.yaml")


@pytest.fixture(scope="module")
def ck():
    return compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")


@pytest.fixture(scope="module")
def index(ck):
    return alias_index(ck)


def test_pending_items_are_not_applied_yet(entries, ck, index):
    fs_fix = load_name_overrides(ROOT, ck, NAME_OVERRIDES)
    eng_fix = load_name_overrides(ROOT, ck)
    pending = [e for e in entries if e.decision is None]
    assert pending
    for e in pending:
        for t in e.texts:
            k = normalize_term(t)
            assert k not in index and k not in fs_fix and k not in eng_fix, t
        if e.new:
            assert e.new["id"] not in ck.ingredient_ids


def test_applied_items(entries, ck, index):
    fs_fix = load_name_overrides(ROOT, ck, NAME_OVERRIDES)
    for e in entries:
        if e.decision == "O" and e.kind == "D":
            for t in e.texts:
                assert fs_fix[normalize_term(t)] == {"id": e.target}
        elif e.decision == "O" and e.kind == "C":
            for t in e.texts:
                assert normalize_term(t) not in index and normalize_term(t) not in fs_fix


def test_number_with_gaji_is_a_name_not_an_amount(ck, index):
    """'곁들이채소2 : 2가지색 미니파프리카 30g'의 '2가지'를 양으로 읽지 않는다(um-5)."""
    assert ingredient_segments("곁들이채소2 : 2가지색 미니파프리카 30g, 양파 60g", "예") == \
        ["곁들이채소2", "2가지색 미니파프리카 30g", "양파 60g"]
    assert ingredient_segments("땅콩: 10g", "예") == ["땅콩: 10g"]
    # 번호 붙은 소제목('곁들이채소1')도 구성 재료가 따로 적혀 있으면 뺀다
    row = {"RCP_SEQ": "1", "RCP_NM": "예", "RCP_PARTS_DTLS": "곁들이채소1 : 당근 20g, 양파 60g"}
    r = convert_row(row, index, ck.concept_ids)
    assert [i["ingredient"] for i in r["ingredients"]] == ["carrot", "onion"]
