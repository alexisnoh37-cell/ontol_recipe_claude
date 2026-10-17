"""미매칭 보강(um-1 검수 → um-2 반영): 사람 결정이 knowledge·이름 보정표·변환 규칙에 그대로 반영됐는지.

결정 원본: docs/review/unmapped_proposal.yaml(decision), 사람 내보내기 파일 docs/review/unmapped_decisions.json.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from kb import compile_paths
from kb.foodsafety import ingredient_segments
from kb.text import normalize_term
from kb.unmapped_review import PROPOSAL, ProposalError, engine_unmapped, load_proposal
from kb.youtube_seed import NAME_OVERRIDES, YoutubeDataset, alias_index, convert, load_name_overrides

ROOT = Path(__file__).resolve().parents[2]

# 사람 결정(2026-10-17): 레시피를 보여 줄 때 재료 목록 위에 시판 제품 안내를 띄우는 재료
COMMERCIAL = {"instant_noodle_product", "naengmyeon_broth", "buldak_sauce", "sundae", "potato_chips",
              "ssanghwatang", "misutgaru"}


@pytest.fixture(scope="module")
def entries():
    return load_proposal(ROOT / PROPOSAL)


@pytest.fixture(scope="module")
def ck():
    return compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")


@pytest.fixture(scope="module")
def index(ck):
    return alias_index(ck)


@pytest.fixture(scope="module")
def overrides(ck):
    return load_name_overrides(ROOT, ck)


def test_every_entry_has_a_human_decision(entries):
    decisions = json.loads((ROOT / "docs" / "review" / "unmapped_decisions.json").read_text(encoding="utf-8"))
    assert decisions["format"] == "unmapped-decisions/1"
    assert all(e.decision in ("O", "X") for e in entries)


def test_approved_aliases_and_new_ingredients_map(entries, ck, index):
    status = {i.id: i.status for i in ck.ingredients}
    for e in entries:
        if e.decision != "O" or e.kind not in ("A", "B", "E"):
            continue
        expected = e.new["id"] if e.new else e.target
        if e.new:
            assert status.get(expected) == "draft", expected  # 재료 검수 전
        for t in e.texts:
            assert index.get(normalize_term(t)) == expected, (t, expected)


def test_rejected_and_held_terms_stay_unmapped(entries, index, overrides):
    # X(반영 안 함)와 C(보류)는 미매칭으로 남아 알레르기 사용자에게 계속 제외된다.
    for e in entries:
        if e.decision == "X" or e.kind == "C":
            for t in e.texts:
                k = normalize_term(t)
                assert k not in index and k not in overrides, t


def test_name_overrides_match_approved_d_entries(entries, overrides):
    fs_rules = {"재료 닭가슴살", "양념 다진 마늘", "육수 무", "장식"}  # 식품안전나라는 변환 규칙으로 처리
    expected = {}
    for e in entries:
        if e.kind == "D" and e.decision == "O" and e.key not in fs_rules:
            fix = {"split": e.split} if e.split else {"drop": e.drop} if e.drop else {"id": e.target}
            expected.update({normalize_term(t): fix for t in e.texts})
    assert overrides == expected


def test_drop_is_only_for_water_or_a_line_already_present(overrides):
    assert {f["drop"].split(":")[0] for f in overrides.values() if "drop" in f} <= {"water", "duplicate"}


def test_engine_recipes_left_unmapped_only_by_human_choice(entries, ck):
    # 엔진 레시피(자취요리신·살림팝)에 남은 미매칭 표기는 모두 X·C로 결정된 것뿐이다.
    left = set(engine_unmapped(ROOT, ck).terms)
    kept = {normalize_term(t) for e in entries if e.decision == "X" or e.kind == "C" for t in e.texts}
    assert left <= kept, sorted(left - kept)


def test_commercial_notice_products_are_approved_and_configured(entries):
    display = yaml.safe_load((ROOT / "config" / "display.yaml").read_text(encoding="utf-8"))
    notice = display["commercial_product_notice"]
    assert set(notice["ingredients"]) == COMMERCIAL
    assert notice["text"] == "시판 제품으로 제품 성분을 확인해 알레르기 유무를 확인하시기 바랍니다."
    approved = {e.new["id"] for e in entries if e.decision == "O" and e.new}
    assert COMMERCIAL <= approved


def test_commercial_products_keep_broad_possible_allergens(ck):
    # 시판 제품은 성분이 제품마다 달라 넓게 '포함 가능'으로 둔다(사람이 승인한 목록, Gemini 지적 성분 포함).
    closure: dict[str, set[str]] = {}
    for r in ck.allergen_closure:
        closure.setdefault(r.ingredient_id, set()).add(r.allergen_group_id)
    assert {"peanut", "shrimp", "egg", "wheat"} <= closure["instant_noodle_product"]
    assert {"pork", "shellfish"} <= closure["naengmyeon_broth"]
    assert {"egg", "sesame"} <= closure["buldak_sauce"]
    assert {"egg", "milk", "beef", "sesame"} <= closure["sundae"]
    assert {"beef", "pork", "chicken", "egg", "tomato"} <= closure["potato_chips"]
    assert "sulfites" in closure["ssanghwatang"]
    assert {"peanut", "walnut", "buckwheat", "milk"} <= closure["misutgaru"]


def test_duplicate_term_across_entries_is_rejected(tmp_path):
    p = tmp_path / "p.yaml"
    p.write_text("entries:\n- {kind: A, terms: [가], target: onion}\n- {kind: C, terms: [ 가 ]}\n", encoding="utf-8")
    with pytest.raises(ProposalError):
        load_proposal(p)


# --- 변환 규칙 ---

DS = YoutubeDataset(name="t", label="테스트", script="-")


def _src(*lines):
    return {"id": "t1", "title": "테스트", "cuisine": "한식", "difficulty": 1, "cook_time_min": 10, "servings": 1,
            "source": {"video_url": "https://www.youtube.com/watch?v=x"}, "status": "draft", "confidence": "low",
            "note": None, "taste": None, "equipment": [], "steps": [],
            "ingredients": [{"name": n, "raw_text": r, "role": role, "optional": False, "amount": 1.0, "unit": "개"}
                            for n, r, role in lines]}


def test_override_maps_splits_and_drops(ck, index):
    ov = {normalize_term("맛을 위해 참기름"): {"id": "sesame_oil"},
          normalize_term("파란부분 올리브유"): {"split": [{"id": "green_onion", "amount": False}, {"id": "olive_oil"}]},
          normalize_term("이제 물"): {"drop": "water"}}
    out, unmapped, changes = convert(DS, ck, _src(("맛을 위해 참기름", "맛을 위해 참기름 1스푼", "seasoning"),
                                                  ("파란부분 올리브유", "파란부분 올리브유 5스푼", "seasoning"),
                                                  ("이제 물", "이제 물 700ml", "sub"),
                                                  ("양파", "양파 1개", "main")), index, ov)
    got = [(i["ingredient"], i["amount"]) for i in out["ingredients"]]
    assert got == [("sesame_oil", 1.0), ("green_onion", None), ("olive_oil", 1.0), ("onion", 1.0)]
    assert not unmapped and len(changes) == 3


def test_override_refuses_to_drop_a_line_that_is_not_a_duplicate(ck, index):
    # 한 줄 안에 두 표기가 적힌 경우("양념은 불닭소스 3스푼 / 불닭소스 3스푼")를 중복 줄로 오판해 빼면 알레르기 성분이 사라진다.
    ov = {normalize_term("양념은 불닭소스"): {"drop": "duplicate:buldak_sauce"}}
    with pytest.raises(SystemExit):
        convert(DS, ck, _src(("양념은 불닭소스", "양념은 불닭소스 3스푼", "sub"), ("양파", "양파 1개", "main")), index, ov)


def test_override_file_rejects_unknown_ingredient(ck, tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / NAME_OVERRIDES).write_text("overrides:\n- {names: [가], id: no_such_thing}\n", encoding="utf-8")
    with pytest.raises(SystemExit):
        load_name_overrides(tmp_path, ck)


def test_foodsafety_strips_header_word_prefix_and_decor():
    skipped: list[str] = []
    out = ingredient_segments("재료 닭가슴살 100g, 양념 다진 마늘 1큰술, 소스 1큰술, 장식", "닭요리", skipped)
    assert out == ["닭가슴살 100g", "다진 마늘 1큰술", "소스 1큰술"]
    assert skipped == ["재료", "양념", "장식"]
