"""Stage 4: entity resolution with **as-of-date integrity** — the reference-data edge.

Resolve a company name/ticker mentioned in a filing to canonical IDs (CIK + ticker)
against SEC reference data. This handles the cases real reference-data systems care
about — and that recent real filings rarely surface, so the scenario fixtures
(`tests/`) are how we prove it:

- **ambiguous** (>1 match) -> flag + return candidates; *never guess*.
- **unresolved** (no match) -> flag; *never fabricate*.
- **as-of-date drift** -> a ticker today may have belonged to a *different* issuer
  at the filing date (tickers get reused; companies rename/merge). SEC's *current*
  ticker map can't prove the historical mapping, so for older filings we **flag the
  risk** rather than silently trusting today's mapping. Flagging the risk you can't
  fully resolve from public data *is* the reference-data discipline.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

# Common corporate suffixes/stopwords stripped before name matching.
_NOISE = re.compile(
    r"\b(inc|incorporated|corp|corporation|co|company|companies|ltd|limited|llc|"
    r"lp|plc|holdings|holding|group|the|and)\b", re.IGNORECASE)


def normalize_company_name(name: str) -> str:
    n = re.sub(r"[.,&/]", " ", name.lower())
    n = _NOISE.sub(" ", n)
    return re.sub(r"\s+", " ", n).strip()


@dataclass
class Resolution:
    query: str
    status: str                       # resolved | ambiguous | unresolved
    cik: str | None = None
    ticker: str | None = None
    name: str | None = None
    candidates: list[dict] = field(default_factory=list)
    asof_risk: bool = False           # current mapping may not hold as-of the filing


def build_index(rows: list[dict]) -> list[dict]:
    """Build the resolver index from SEC company-ticker rows."""
    return [{
        "cik": str(r["cik_str"]).zfill(10),
        "ticker": str(r["ticker"]).upper(),
        "name": r["title"],
        "norm": normalize_company_name(r["title"]),
    } for r in rows]


def _asof_risk(as_of_date: str | None, recent_years: int) -> bool:
    """True if the filing is old enough that today's mapping may not hold."""
    if not as_of_date:
        return False
    try:
        return (date.today().year - int(str(as_of_date)[:4])) > recent_years
    except ValueError:
        return False


def _candidates(rows: list[dict]) -> list[dict]:
    return [{"cik": r["cik"], "ticker": r["ticker"], "name": r["name"]} for r in rows[:5]]


def resolve(query: str, index: list[dict], as_of_date: str | None = None,
            recent_years: int = 3) -> Resolution:
    """Resolve `query` (a ticker or company name) against the reference index."""
    asof = _asof_risk(as_of_date, recent_years)
    q = query.strip()

    # 1) exact ticker
    tmatch = [r for r in index if r["ticker"] == q.upper()]
    if len(tmatch) == 1:
        return Resolution(query, "resolved", tmatch[0]["cik"], tmatch[0]["ticker"],
                          tmatch[0]["name"], asof_risk=asof)
    if len(tmatch) > 1:
        return Resolution(query, "ambiguous", candidates=_candidates(tmatch), asof_risk=asof)

    # 2) exact normalized name
    qn = normalize_company_name(q)
    if qn:
        nmatch = [r for r in index if r["norm"] == qn]
        if len(nmatch) == 1:
            return Resolution(query, "resolved", nmatch[0]["cik"], nmatch[0]["ticker"],
                              nmatch[0]["name"], asof_risk=asof)
        if len(nmatch) > 1:
            return Resolution(query, "ambiguous", candidates=_candidates(nmatch), asof_risk=asof)

        # 3) unique containment (e.g. "Acme" -> "Acme Industries")
        part = [r for r in index if qn in r["norm"]]
        if len(part) == 1:
            return Resolution(query, "resolved", part[0]["cik"], part[0]["ticker"],
                              part[0]["name"], asof_risk=asof)
        if len(part) > 1:
            return Resolution(query, "ambiguous", candidates=_candidates(part), asof_risk=asof)

    return Resolution(query, "unresolved")


def load_index() -> list[dict]:
    """Live index from SEC reference data (network)."""
    from rageval import edgar
    return build_index(edgar.company_tickers())
