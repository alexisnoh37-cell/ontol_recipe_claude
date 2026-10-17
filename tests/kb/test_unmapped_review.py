"""미매칭 보강 검수표(um-1): 제안 데이터가 지식과 충돌하지 않고, 엔진 레시피 미매칭을 모두 분류했으며, 검수표가 최신인지."""

from __future__ import annotations

from pathlib import Path

import pytest

from kb import compile_paths
from kb.text import normalize_term
from kb.unmapped_review import (
    OUT,
    PROPOSAL,
    Entry,
    ProposalError,
    Unmapped,
    Usage,
    _resolved_keys,
    candidate_knowledge,
    engine_unmapped,
    foodsafety_unmapped,
    load_proposal,
    make,
    read_approvals,
    simulate,
    unclassified,
)

ROOT = Path(__file__).resolve().parents[2]


def _lf(text: str) -> str:
    """git 줄바꿈 변환(CRLF)과 무관하게 비교한다."""
    return text.replace("\r\n", "\n")


@pytest.fixture(scope="module")
def entries():
    return load_proposal(ROOT / PROPOSAL)


@pytest.fixture(scope="module")
def ck_now():
    return compile_paths(ROOT / "knowledge", ROOT / "config" / "pantry_staples.yaml")


@pytest.fixture(scope="module")
def eng(ck_now):
    return engine_unmapped(ROOT, ck_now)


def test_proposal_compiles_into_knowledge(entries, ck_now):
    # 별칭 충돌·없는 id가 있으면 KnowledgeError/ProposalError. 새 재료는 모두 draft로 들어간다.
    ck = candidate_knowledge(ROOT, entries)
    new_ids = {e.new["id"] for e in entries if e.new}
    assert new_ids and not new_ids & {i.id for i in ck_now.ingredients}
    assert {i.id: i.status for i in ck.ingredients if i.id in new_ids} == dict.fromkeys(new_ids, "draft")


def test_proposal_terms_are_still_unmapped(entries, ck_now):
    # 지식이 바뀌어 이미 매핑되는 표기가 생기면 제안을 정리해야 한다.
    index = {a.alias_norm for a in ck_now.aliases if a.ingredient_id not in ck_now.concept_ids}
    stale = [t for e in entries for t in e.texts if normalize_term(t) in index]
    assert not stale, stale


def test_every_engine_unmapped_term_is_classified(entries, eng):
    fs = Unmapped({}, {}, 0, 0)
    e_left, _ = unclassified(entries, eng, fs)
    assert not e_left, e_left


def test_new_ingredients_with_possible_allergens_are_low_confidence(entries):
    # 제품마다 성분이 다른 새 재료(possible 관계)는 confidence low로 검수표에 올린다(CLAUDE.md).
    for e in entries:
        if not e.new:
            continue
        rels = list(e.new.get("derived_from", [])) + list(e.new.get("allergens", []))
        if e.kind == "E" or any(isinstance(r, dict) and r.get("certainty") == "possible" for r in rels):
            assert e.new["confidence"] == "low" or e.new["id"] == "mixed_nuts", e.new["id"]


def test_duplicate_term_across_entries_is_rejected(tmp_path):
    p = tmp_path / "p.yaml"
    p.write_text("entries:\n- {kind: A, terms: [가], target: onion}\n- {kind: C, terms: [ 가 ]}\n", encoding="utf-8")
    with pytest.raises(ProposalError):
        load_proposal(p)


def test_d_entry_needs_its_new_ingredient_approved():
    entries = [
        Entry(0, "E", ["코인"], new={"id": "x_stock", "name": "코인", "category": "육수·조미료"}),
        Entry(1, "D", ["멸치 대신 코인"], target="x_stock"),
        Entry(2, "D", ["마지막 꿀"], target="honey"),
    ]
    assert _resolved_keys(entries, {"D"}) == {"마지막꿀"}
    assert _resolved_keys(entries, {"D", "E"}) == {"코인", "멸치대신코인", "마지막꿀"}


def test_simulate_counts_recipes_without_unmapped():
    u = Unmapped({"a": Usage(2), "b": Usage(1)}, {"r1": {"a"}, "r2": {"a", "b"}}, 3, 10)
    assert simulate(u, set()) == (3, 1)
    assert simulate(u, {"a"}) == (1, 2)
    assert simulate(u, {"a", "b"}) == (0, 3)


def test_review_is_up_to_date_and_keeps_approvals():
    # 검수표는 생성기 결과와 같아야 한다(승인 열은 기존 파일에서 가져와 유지).
    assert _lf((ROOT / OUT).read_text(encoding="utf-8")) == _lf(make(ROOT))
    assert isinstance(read_approvals(ROOT / OUT), dict)


def test_foodsafety_counts_match_conversion_report():
    fs = foodsafety_unmapped(ROOT)
    assert fs.recipe_count == 1153
    report = (ROOT / "docs" / "review" / "foodsafety_unmatched.md").read_text(encoding="utf-8")
    assert f"미매칭: {sum(u.lines for u in fs.terms.values())}개" in report


def _html_script():
    import importlib.util
    spec = importlib.util.spec_from_file_location("make_unmapped_review_html", ROOT / "scripts" / "make_unmapped_review_html.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_review_html_is_up_to_date_and_prefill_covers_disagreements():
    # 두 검토가 갈린 줄은 모두 미리 채울 판단(unmapped_prefill.yaml)이 있어야 생성된다. 화면 파일은 생성 결과와 같아야 한다.
    mod = _html_script()
    html, data = mod.build()
    assert _lf((ROOT / "docs" / "review" / "unmapped_review.html").read_text(encoding="utf-8")) == _lf(html)
    assert len(data) == len(load_proposal(ROOT / PROPOSAL))
    assert {d["prefill"]["decision"] for d in data} <= {"O", "X", "보류"}
    # 시판 제품(E)은 포장 확인 전 승인으로 미리 채우지 않는다.
    assert all(d["prefill"]["decision"] != "O" for d in data if d["kind"] == "E")
