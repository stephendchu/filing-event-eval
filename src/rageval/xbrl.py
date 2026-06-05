"""Slice 6: XBRL numeric path — exact financial facts from SEC's structured data.

The grounding eval exposed a parsing-driven hallucination rate on *numbers* (a
filing presented a tax rate as a table; the model invented a prose sentence). The
fix is to **not parse HTML for figures** — pull them from SEC **XBRL**, where every
fact is machine-readable and tagged with an exact value, unit, and period. **Zero
hallucination for quantitative facts.** The LLM is reserved for narrative, behind
the grounding gate.

    PYTHONPATH=src python -m rageval.xbrl --ticker AAPL --metric rd_expense
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass

from rageval import edgar

# Friendly metric name -> us-gaap concept(s), first match wins.
CONCEPTS = {
    "revenue": ["RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues"],
    "rd_expense": ["ResearchAndDevelopmentExpense"],
    "sga_expense": ["SellingGeneralAndAdministrativeExpense"],
    "net_income": ["NetIncomeLoss"],
    "operating_income": ["OperatingIncomeLoss"],
    "gross_profit": ["GrossProfit"],
}


@dataclass
class Fact:
    concept: str
    value: float
    unit: str
    fy: int | None
    period_end: str
    form: str


def company_facts(cik: str) -> dict:
    """All XBRL facts for a company (network; uses the retrying EDGAR client)."""
    return edgar._get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json").json()


def pick_annual(facts: dict, metric: str) -> Fact | None:
    """Most recent **annual** (10-K, full-year) value for a metric — pure, testable.

    Returns None if the concept isn't reported. No guessing, no LLM: the value is
    exactly what the company tagged.
    """
    usgaap = facts.get("facts", {}).get("us-gaap", {})
    for concept in CONCEPTS.get(metric, [metric]):
        usd = usgaap.get(concept, {}).get("units", {}).get("USD", [])
        annual = [u for u in usd
                  if u.get("form") == "10-K" and u.get("fp") == "FY" and u.get("val") is not None]
        if annual:
            u = max(annual, key=lambda x: x.get("end", ""))
            return Fact(concept, float(u["val"]), "USD", u.get("fy"), u.get("end"), u.get("form"))
    return None


def get_annual_fact(ticker: str, metric: str) -> Fact | None:
    return pick_annual(company_facts(edgar.ticker_to_cik(ticker)), metric)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--metric", default="rd_expense", choices=list(CONCEPTS))
    args = ap.parse_args()
    f = get_annual_fact(args.ticker, args.metric)
    if f is None:
        print(f"{args.ticker} {args.metric}: not reported")
        return
    print(f"{args.ticker} {args.metric}: {f.value:,.0f} {f.unit}  (FY{f.fy}, {f.period_end}, {f.form})")
    print("  ^ exact, from XBRL — zero hallucination (no HTML parsing, no LLM).")


if __name__ == "__main__":
    main()
