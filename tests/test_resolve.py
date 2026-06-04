"""Entity-resolution scenarios (offline). These curated edge cases are how we prove
the resolver handles ambiguity / not-found / as-of-date drift — the cases recent
real filings rarely surface."""
from rageval.resolve import build_index, normalize_company_name, resolve

# Synthetic SEC reference index. Two "Acme" issuers create a deliberate ambiguity.
_ROWS = [
    {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
    {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corporation"},
    {"cik_str": 111111, "ticker": "ACMX", "title": "Acme Corporation"},
    {"cik_str": 222222, "ticker": "ACMY", "title": "Acme Company"},
]
IDX = build_index(_ROWS)


def test_normalize_strips_suffixes():
    assert normalize_company_name("Apple Inc.") == "apple"
    assert normalize_company_name("Microsoft Corporation") == "microsoft"


def test_resolve_by_ticker():
    r = resolve("AAPL", IDX)
    assert r.status == "resolved" and r.cik == "0000320193"


def test_resolve_by_exact_name():
    r = resolve("Microsoft Corporation", IDX)
    assert r.status == "resolved" and r.ticker == "MSFT"


def test_resolve_by_unique_containment():
    r = resolve("Apple", IDX)
    assert r.status == "resolved" and r.ticker == "AAPL"


def test_ambiguous_does_not_guess():
    r = resolve("Acme", IDX)
    assert r.status == "ambiguous"
    assert r.cik is None                      # never guesses
    assert {c["ticker"] for c in r.candidates} == {"ACMX", "ACMY"}


def test_unresolved_is_flagged_not_fabricated():
    r = resolve("Nonexistent Holdings", IDX)
    assert r.status == "unresolved" and r.cik is None


def test_asof_risk_flagged_for_old_filing():
    # A ticker resolved against TODAY's map, but the filing is old -> flag drift risk.
    old = resolve("AAPL", IDX, as_of_date="2009-09-27")
    recent = resolve("AAPL", IDX, as_of_date="2025-09-27")
    assert old.asof_risk is True
    assert recent.asof_risk is False
