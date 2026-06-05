"""Settleability gate + parsing tests (offline — no API).

The gate is the important guard: even if the model says 'settleable', a candidate
with no deadline or no settlement source can't be settled, so it's rejected.
"""
from rageval.settle import Contract, _gate, _parse, settleability_rate


def test_parse_settleable():
    raw = ('{"settleable": true, "question": "Will the acquisition close by Q3 2026?", '
           '"deadline": "Q3 2026", "settlement_source": "next 10-Q"}')
    c = _parse(raw, "expects to close acquisition")
    assert c.settleable and c.deadline == "Q3 2026"


def test_parse_not_settleable_keeps_reason():
    c = _parse('{"settleable": false, "reason": "no deadline"}', "vague plan")
    assert c.settleable is False and c.reason == "no deadline"


def test_gate_accepts_complete_contract():
    c = Contract("e", True, "Will X by Y?", "Q3 2026", "next 10-Q")
    assert _gate(c).settleable is True


def test_gate_rejects_missing_deadline():
    c = Contract("e", True, "Will X happen?", deadline=None, settlement_source="SEC")
    assert _gate(c).settleable is False


def test_gate_rejects_missing_settlement_source():
    c = Contract("e", True, "Will X by Y?", "Q3 2026", settlement_source=None)
    assert _gate(c).settleable is False


def test_settleability_rate():
    cs = [Contract("a", True, "q", "d", "s"), Contract("b", False), Contract("c", False)]
    assert settleability_rate(cs) == round(1 / 3, 3)
