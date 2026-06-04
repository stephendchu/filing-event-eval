"""Tests for eval metrics (offline — no API)."""
from rageval.evals import grounding_rate, summary
from rageval.extract import Event


def _ev(citation, grounded):
    return Event(event="x", type="risk", citation=citation, item="1A", grounded=grounded)


def test_grounding_rate_basic():
    events = [_ev("a real quote", True), _ev("another", True), _ev("fake", False)]
    assert grounding_rate(events) == round(2 / 3, 3)


def test_grounding_rate_ignores_uncited_events():
    events = [_ev("real", True), _ev("", None)]  # second has no citation
    assert grounding_rate(events) == 1.0


def test_grounding_rate_none_when_nothing_cited():
    assert grounding_rate([_ev("", None)]) is None


def test_summary_counts():
    s = summary([_ev("a", True), _ev("b", False), _ev("", None)])
    assert s["events"] == 3 and s["cited"] == 2 and s["grounded"] == 1
