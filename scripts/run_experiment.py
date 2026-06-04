"""H1 experiment: naive whole-filing **baseline** vs section-aware **treatment**.

Both arms cite. We compare:
- grounding rate (fraction of cited events whose citation is verbatim-verifiable),
- grounded-candidate count,
- and (treatment) settleability of the grounded candidates -> valid-candidate yield.

Hypothesis: section-aware extraction grounds better (focused context -> fewer
fabricated quotes) and finds more (covers more sections, not truncated to fit).

Rate-limit aware: spacing + retry on 429. Resumable-ish; writes results.json.
    PYTHONPATH=src python scripts/run_experiment.py --tickers AAPL MSFT --sections 3
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import anthropic

from rageval import edgar, parse
from rageval.baseline import extract_baseline
from rageval.extract import extract_section
from rageval.settle import classify

SPACING, RETRY_WAIT, MAX_RETRY = 8, 45, 4
PREFERRED = ["1A", "7", "3", "1", "5"]
OUT = Path("/mnt/c/Users/Steph/agentic-rag-eval/results/experiment")
OUT.mkdir(parents=True, exist_ok=True)


def log(m): print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


def retry(fn, what: str):
    for a in range(MAX_RETRY):
        try:
            return fn()
        except anthropic.RateLimitError:
            log(f"  429 on {what} — wait {RETRY_WAIT}s ({a+1}/{MAX_RETRY})")
            time.sleep(RETRY_WAIT)
        except anthropic.APIError as e:
            log(f"  API error on {what}: {str(e)[:80]}")
            return None
    return None


def _ingest(ticker):
    cik = edgar.ticker_to_cik(ticker)
    meta = edgar.latest_filing(cik)
    html = edgar.fetch_filing(meta).read_text(encoding="utf-8", errors="replace")
    sections = parse.split_sections(parse.html_to_text(html))
    return meta, sections, " ".join(s.text for s in sections)


def _pick(sections, n):
    by = {s.item: s for s in sections}
    picked = [by[i] for i in PREFERRED if i in by]
    rest = sorted((s for s in sections if s not in picked), key=lambda s: len(s.text), reverse=True)
    return (picked + rest)[:n]


def _grate(events):
    cited = [e for e in events if e.citation]
    return round(sum(bool(e.grounded) for e in cited) / len(cited), 3) if cited else None


def run(tickers, n_sections=3, do_settle=True):
    rows = []
    for tk in tickers:
        meta, secs, full = _ingest(tk)
        log(f"{tk}: {meta['company']} ({meta['report_date']})")

        base = retry(lambda: extract_baseline(full), f"{tk}/baseline") or []
        time.sleep(SPACING)

        treat = []
        for s in _pick(secs, n_sections):
            evs = retry(lambda s=s: extract_section(s.item, s.text), f"{tk}/extract/{s.item}") or []
            treat.extend(evs)
            time.sleep(SPACING)

        grounded = [e for e in treat if e.grounded]
        n_settle = 0
        if do_settle:
            for e in grounded[:10]:  # cap for cost/throttle
                c = retry(lambda e=e: classify(e.event, e.citation), f"{tk}/settle")
                if c and c.settleable:
                    n_settle += 1
                time.sleep(SPACING)

        row = {
            "ticker": tk, "company": meta["company"],
            "baseline": {"events": len(base),
                         "grounded": sum(bool(e.grounded) for e in base),
                         "grounding_rate": _grate(base)},
            "treatment": {"events": len(treat), "grounded": len(grounded),
                          "grounding_rate": _grate(treat),
                          "settleable_of_grounded": n_settle,
                          "valid_candidate_yield": round(n_settle / len(treat), 3) if treat else None},
        }
        rows.append(row)
        (OUT / "results.json").write_text(json.dumps(rows, indent=2))
        log(f"  baseline: gr={row['baseline']['grounding_rate']} ({row['baseline']['grounded']}/{row['baseline']['events']})"
            f"  |  treatment: gr={row['treatment']['grounding_rate']} ({len(grounded)}/{len(treat)})  settleable={n_settle}")
    log("DONE -> results/experiment/results.json")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", nargs="+", default=["AAPL", "MSFT"])
    ap.add_argument("--sections", type=int, default=3)
    ap.add_argument("--no-settle", action="store_true")
    args = ap.parse_args()
    run(args.tickers, args.sections, do_settle=not args.no_settle)


if __name__ == "__main__":
    main()
