"""Recommender.trace() (docs/plan.md 부록 D-4): recommend()와 같은 코드 경로라 결과가 같아야 한다."""

from __future__ import annotations

import pytest

from storage.engine_source import load_files
from storage.personas import load_personas


@pytest.fixture(scope="module")
def recommender():
    return load_files().recommender()


@pytest.mark.parametrize("persona", load_personas(), ids=lambda p: p.id)
def test_trace_result_equals_recommend(recommender, persona):
    plain = recommender.recommend(persona.user, persona.request)
    result, trace = recommender.trace(persona.user, persona.request)
    assert result == plain
    excluded = {e.recipe_id for e in plain.exclusions}
    passed = [s.candidate.recipe.id for s in trace.ranked]
    assert {c.recipe.id for c in trace.candidates} == excluded | set(passed)
    assert not excluded & set(passed)
    assert sorted(passed) == sorted(s.candidate.recipe.id for s in trace.ordered)
    assert [s.candidate.recipe.id for s in trace.ordered[: persona.request.limit]] == [i.recipe_id for i in plain.items]
    assert trace.pantry == persona.user.pantry
    for ancestor, sources in trace.owned_from.items():
        assert all(ancestor in recommender.knowledge.snapshot().ancestors[s] for s in sources)
