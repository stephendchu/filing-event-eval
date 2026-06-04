"""Tests for citation grounding (offline — no API)."""
from rageval.grounding import is_grounded, normalize

SRC = ("The Company expects to close the acquisition of Acme Corp by the third "
       "quarter of fiscal 2026, subject to regulatory approval.")


def test_verbatim_quote_is_grounded():
    assert is_grounded("expects to close the acquisition of Acme Corp", SRC)


def test_whitespace_and_case_differences_ok():
    assert is_grounded("EXPECTS  to close\nthe acquisition", SRC)


def test_paraphrase_is_not_grounded():
    assert not is_grounded("the company will buy Acme sometime next year", SRC)


def test_absent_quote_is_not_grounded():
    assert not is_grounded("a completely unrelated sentence about widgets", SRC)


def test_too_short_citation_rejected():
    assert not is_grounded("the", SRC)


def test_normalize_collapses_whitespace():
    assert normalize("  a\n  b\t c ") == "a b c"
