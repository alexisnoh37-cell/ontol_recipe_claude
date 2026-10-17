"""미매칭 2차 보강(um-3): 일괄 승인분과 꼭 확인 검수 결정이 반영되고, 보류는 미매칭으로 남는지.

결정 원본: docs/review/unmapped_round2.yaml. 사람 결정(2026-10-17) "일괄 승인은 그대로 진행하고 꼭 확인해야 할 것만 검수".
decision O = 반영. 꼭 확인 17개(E)는 검수 화면에서 사람이 결정했다(docs/review/unmapped_round2_decisions.json, 모두 O).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from kb import compile_paths
from kb.foodsafety import NAME_OVERRIDES, convert_row, ingredient_segments
from kb.text import normalize_term
from kb.unmapped_review import foodsafety_unmapped, load_proposal
from kb.youtube_seed import alias_index, load_name_overrides

ROOT = Path(__file__).resolve().parents[2]
ROUND2 = ROOT / "docs" / "review" / "unmapped_round2.yaml"


@pytest.fixture(scope="module")
def entries():
    return load_proposal(ROUND2)


@pytest.fixture(scope="module")
def ck():
    return compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")


@pytest.fixture(scope="module")
def index(ck):
    return alias_index(ck)


@pytest.fixture(scope="module")
def overrides(ck):
    return load_name_overrides(ROOT, ck, NAME_OVERRIDES)


DECISIONS = ROOT / "docs" / "review" / "unmapped_round2_decisions.json"


def _human():
    data = json.loads(DECISIONS.read_text(encoding="utf-8"))
    assert data["format"] == "unmapped-round2-decisions/1"
    return {r["id"]: r for r in data["rows"]}


def test_must_check_items_follow_human_decisions(entries):
    human = _human()
    checked = {e.new["id"]: e for e in entries if e.kind == "E"}
    assert set(checked) == set(human)  # 꼭 확인 항목 = 검수 화면에서 결정한 항목
    for i, e in checked.items():
        assert e.decision == {"O": "O", "X": "X"}.get(human[i]["decision"]), i
    assert all(e.decision == "O" for e in entries if e.kind != "E")


def test_must_check_memos_applied(ck):
    """메모 '알레르기 제외' → 알레르기 없음, '성분표 확인 후 사용 권장' → 시판 제품 안내 대상(ir-2와 같은 해석)."""
    import yaml

    has_allergen = {r.ingredient_id for r in ck.allergen_closure}
    assert "coconut" not in has_allergen and "acorn_jelly" not in has_allergen
    notice = set(yaml.safe_load((ROOT / "config" / "display.yaml").read_text(encoding="utf-8"))
                 ["commercial_product_notice"]["ingredients"])
    memo = {i for i, r in _human().items() if "확인" in r["memo"] and r["decision"] != "X"}
    assert len(memo) == 14 and memo <= notice
    status = {i.id: i.status for i in ck.ingredients}
    assert all(status[i] == "reviewed" for i in _human())


def test_approved_aliases_and_new_ingredients_map(entries, ck, index):
    status = {i.id: i.status for i in ck.ingredients}
    for e in entries:
        if e.decision != "O" or e.kind not in ("A", "B", "E"):
            continue
        expected = e.new["id"] if e.new else e.target
        if e.new:
            assert status[expected] == "reviewed", expected  # 사람 일괄 승인
        for t in e.texts:
            assert index.get(normalize_term(t)) == expected, t


ROUND3 = ROOT / "docs" / "review" / "unmapped_round3.yaml"


def test_held_terms_stay_unmapped(entries, index, overrides):
    later = {normalize_term(t) for e in load_proposal(ROUND3) for t in e.texts}  # um-4에서 다시 정한 표기
    for e in entries:
        if e.decision != "O" or e.kind == "C":
            for t in [t for t in e.texts if normalize_term(t) not in later]:
                assert normalize_term(t) not in index, t
                assert normalize_term(t) not in overrides, t


def test_foodsafety_name_overrides_match_approved_d_entries(entries, overrides):
    expected = {}
    later = load_proposal(ROUND3) + load_proposal(ROOT / "docs" / "review" / "unmapped_round4.yaml")
    for e in entries + later:  # 보정표는 2~4차(um-3~5) 승인 D를 함께 담는다
        if e.kind == "D" and e.decision == "O":
            fix = ({"split": e.split} if e.split else {"drop": e.drop} if e.drop else {"id": e.target})
            for t in e.texts:
                expected[normalize_term(t)] = fix
    assert overrides == expected


def test_converted_recipes_leave_only_held_or_pending_terms(entries):
    """변환 결과(data/recipes_foodsafety)가 지금 지식·보정표와 맞는지: 남은 미매칭은 1·2차에서 보류·제외한 표기뿐."""
    first = load_proposal(ROOT / "docs" / "review" / "unmapped_proposal.yaml")
    left_open = {normalize_term(t) for e in entries if e.kind == "C" or e.decision != "O" for t in e.texts}
    left_open |= {normalize_term(t) for e in first if e.kind == "C" or e.decision == "X" for t in e.texts}
    fs = foodsafety_unmapped(ROOT)
    assert set(fs.terms) <= left_open


def test_new_ingredient_allergens(ck):
    def groups(i):
        return {r.allergen_group_id: r.certainty for r in ck.allergen_closure if r.ingredient_id == i}

    assert groups("pecan")["other_tree_nuts"] == "definite"
    assert groups("hazelnut")["other_tree_nuts"] == "definite"
    assert {"soybean", "wheat"} <= set(groups("hoisin"))
    assert "wheat" in groups("couscous") and "wheat" in groups("crackers")
    assert groups("worcestershire").get("other_fish")  # 멸치
    assert groups("eel")["other_fish"] == "definite"
    assert groups("turban_shell")["shellfish"] == "definite"
    assert groups("pond_snail")  # 우렁이(복족류) → 조개류
    assert set(groups("seafood_stock")) >= {"shrimp", "crab", "squid", "shellfish", "mackerel"}


def test_foodsafety_splits_label_after_amount():
    """양 뒤에 '소제목:'이 이어진 줄의 뒤 재료가 앞 줄에 묻히지 않는다(알레르기 누락 방지, um-3)."""
    assert ingredient_segments("마늘다진것 2g 리코타치즈:우유 125g", "예") == ["마늘다진것 2g", "리코타치즈", "우유 125g"]
    assert ingredient_segments("황설탕(7g) 호떡소: 검정깨", "예") == ["황설탕(7g)", "호떡소", "검정깨"]
    assert ingredient_segments("다진 실파 2 양념장: 간장 3", "예") == ["다진 실파 2", "간장 3"]
    assert ingredient_segments("두부 10g, 초코크림 : 아몬드가루 85g", "예") == ["두부 10g", "초코크림", "아몬드가루 85g"]
    assert ingredient_segments("땅콩: 10g", "예") == ["땅콩: 10g"]


def test_foodsafety_numbered_header_word_is_a_label():
    assert ingredient_segments("소스1 발사믹식초(5g), 소스2 마요네즈(10g)", "예") == ["발사믹식초(5g)", "마요네즈(10g)"]
    assert ingredient_segments("마늘 1g[소스1]간장 1g", "예") == ["마늘 1g", "간장 1g"]


def test_foodsafety_overrides_map_split_and_drop(ck, index):
    fixes = {normalize_term("올ㄹ브오일"): {"id": "olive_oil"}, normalize_term("유산지"): {"drop": "not_ingredient"},
             normalize_term("청홍고추"): {"split": [{"id": "green_chili"}, {"id": "red_chili"}]}}
    row = {"RCP_SEQ": "1", "RCP_NM": "예", "RCP_PARTS_DTLS": "올ㄹ브오일 5g, 유산지 1장, 청홍고추 10g"}
    r = convert_row(row, index, ck.concept_ids, fixes)
    assert [(i["ingredient"], i["raw_text"]) for i in r["ingredients"]] == [
        ("olive_oil", "올ㄹ브오일 5g"), ("green_chili", "청홍고추 10g"), ("red_chili", "청홍고추 10g")]
    assert "이름 보정표로 고친 줄 3개" in r["note"]
