"""Anti-fabrication tests for typed metric lookup (offline — no API).

These exercise the *guard*, not the LLM: a claimed value with an ungroundable
citation must be rejected; an honest 'not_disclosed' must survive.
"""
from rageval.artifacts import MetricResult, _parse, _verify

SRC = ("Research and development expense was $34.8 billion in fiscal 2025, "
       "an increase of 10% year over year.")


def test_parse_disclosed():
    raw = ('{"status":"disclosed","value":"$34.8 billion","unit":"USD","period":"FY2025",'
           '"citation":"Research and development expense was $34.8 billion"}')
    r = _parse(raw, "R&D expense")
    assert r.status == "disclosed" and r.value == "$34.8 billion"


def test_parse_not_disclosed():
    assert _parse('{"status":"not_disclosed"}', "iPhone unit sales").status == "not_disclosed"


def test_parse_garbage_defaults_to_not_disclosed():
    assert _parse("no json here", "x").status == "not_disclosed"


def test_verify_keeps_grounded_value():
    r = MetricResult("R&D expense", "disclosed", "$34.8 billion",
                     citation="Research and development expense was $34.8 billion")
    assert _verify(r, SRC).status == "disclosed"


def test_verify_rejects_ungrounded_value():
    # The model claimed a number but the citation is NOT in the source -> fabrication.
    r = MetricResult("iPhone unit sales", "disclosed", "230 million",
                     citation="Apple sold 230 million iPhones in 2025")
    assert _verify(r, SRC).status == "ungrounded"


def test_not_disclosed_survives_verify():
    assert _verify(MetricResult("iPhone unit sales", "not_disclosed"), SRC).status == "not_disclosed"
