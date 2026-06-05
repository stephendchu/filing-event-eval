"""Tests for XBRL fact selection (offline — mock SEC company-facts JSON)."""
from rageval.xbrl import pick_annual

# Minimal companyfacts shape: an annual (10-K) value per year + a quarterly to ignore.
FACTS = {"facts": {"us-gaap": {"ResearchAndDevelopmentExpense": {"units": {"USD": [
    {"end": "2023-09-30", "val": 29915000000, "fy": 2023, "fp": "FY", "form": "10-K"},
    {"end": "2024-09-28", "val": 31370000000, "fy": 2024, "fp": "FY", "form": "10-K"},
    {"end": "2025-09-27", "val": 34550000000, "fy": 2025, "fp": "FY", "form": "10-K"},
    {"end": "2025-06-28", "val":  8500000000, "fy": 2025, "fp": "Q3", "form": "10-Q"},
]}}}}}


def test_picks_most_recent_annual():
    f = pick_annual(FACTS, "rd_expense")
    assert f.value == 34550000000 and f.fy == 2025


def test_ignores_quarterly_filings():
    assert pick_annual(FACTS, "rd_expense").form == "10-K"   # not the 10-Q


def test_exact_value_no_rounding():
    assert pick_annual(FACTS, "rd_expense").value == 34550000000.0


def test_unreported_metric_returns_none():
    assert pick_annual(FACTS, "net_income") is None          # concept absent -> honest None
