"""SEC EDGAR client: resolve tickers to CIKs and fetch filings.

Public data only. SEC requires a descriptive User-Agent (set SEC_USER_AGENT in
.env) and asks for <= 10 requests/sec, so we keep calls polite and cached.
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx

from rageval.config import CFG, FILINGS

_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"


def _client() -> httpx.Client:
    # SEC keys access off a descriptive User-Agent; without it you get 403s.
    return httpx.Client(headers={"User-Agent": CFG.sec_user_agent},
                        timeout=30, follow_redirects=True)


def _should_retry(status: int) -> bool:
    """Transient faults retry (429 + 5xx); 4xx (e.g. 403 bad User-Agent, 404) fail fast."""
    return status == 429 or status >= 500


def _get(url: str) -> httpx.Response:
    """GET with bounded exponential backoff on transient EDGAR faults."""
    last = None
    with _client() as c:
        for attempt in range(CFG.edgar_max_attempts):
            r = c.get(url)
            if not _should_retry(r.status_code):
                r.raise_for_status()   # config errors fail fast with an actionable status
                return r
            last = r
            time.sleep(min(2 ** attempt, 20))  # exponential backoff, capped
    last.raise_for_status()            # attempts exhausted -> surface the error
    return last


_TICKERS_CACHE: list[dict] | None = None


def company_tickers() -> list[dict]:
    """All SEC company-ticker rows [{cik_str, ticker, title}, ...] (cached in-process).

    This is the reference-data index the entity resolver maps against. Note it is
    the *current* mapping — see resolve.py for the as-of-date caveat.
    """
    global _TICKERS_CACHE
    if _TICKERS_CACHE is None:
        _TICKERS_CACHE = list(_get(_TICKERS_URL).json().values())
    return _TICKERS_CACHE


def ticker_to_cik(ticker: str) -> str:
    """Resolve a ticker to its zero-padded 10-digit CIK."""
    t = ticker.upper()
    for row in company_tickers():
        if row["ticker"].upper() == t:
            return str(row["cik_str"]).zfill(10)
    raise ValueError(f"ticker {ticker!r} not found in SEC company_tickers")


def latest_filing(cik: str, form: str = "10-K") -> dict:
    """Metadata for the most recent filing of `form` for a CIK."""
    url = f"{CFG.edgar_data}/submissions/CIK{cik}.json"
    data = _get(url).json()
    recent = data["filings"]["recent"]
    for i, f in enumerate(recent["form"]):
        if f == form:
            return {
                "cik": cik,
                "company": data.get("name"),
                "form": form,
                "accession": recent["accessionNumber"][i],
                "primary_doc": recent["primaryDocument"][i],
                "filing_date": recent["filingDate"][i],
                "report_date": recent["reportDate"][i],
            }
    raise ValueError(f"no {form} found for CIK {cik}")


def fetch_filing(meta: dict) -> Path:
    """Download the primary document HTML and cache it. Returns the local path."""
    acc = meta["accession"].replace("-", "")
    url = (f"{CFG.edgar_base}/Archives/edgar/data/"
           f"{int(meta['cik'])}/{acc}/{meta['primary_doc']}")
    FILINGS.mkdir(parents=True, exist_ok=True)
    out = FILINGS / f"{meta['cik']}_{meta['form']}_{meta['report_date']}.html"
    if not out.exists():
        out.write_text(_get(url).text, encoding="utf-8")
        time.sleep(0.2)  # be polite to SEC
    return out
