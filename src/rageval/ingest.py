"""Stage 1 CLI: fetch a 10-K from EDGAR and parse it into sections.

    python -m rageval.ingest --ticker AAPL --form 10-K
"""
from __future__ import annotations

import argparse
import json

from rageval import edgar, parse
from rageval.config import FILINGS


def ingest(ticker: str, form: str = "10-K") -> dict:
    cik = edgar.ticker_to_cik(ticker)
    meta = edgar.latest_filing(cik, form)
    html = edgar.fetch_filing(meta).read_text(encoding="utf-8", errors="replace")
    sections = parse.split_sections(parse.html_to_text(html))

    # Persist full section text for the extraction stage (gitignored).
    out_path = FILINGS / f"{meta['cik']}_{meta['form']}_{meta['report_date']}.sections.json"
    out_path.write_text(
        json.dumps([{"item": s.item, "title": s.title, "text": s.text} for s in sections]),
        encoding="utf-8",
    )
    return {"meta": meta, "sections": sections, "sections_path": str(out_path)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch + section-parse a 10-K from EDGAR.")
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--form", default="10-K")
    args = ap.parse_args()

    res = ingest(args.ticker, args.form)
    m = res["meta"]
    print(f"{m['company']}  {m['form']}  (report {m['report_date']}, filed {m['filing_date']})")
    print(f"{len(res['sections'])} sections parsed:")
    for s in res["sections"]:
        print(f"  Item {s.item:<4} {len(s.text):>8,} chars  {s.title[:55]}")


if __name__ == "__main__":
    main()
