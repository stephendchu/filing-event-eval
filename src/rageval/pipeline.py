"""Traced end-to-end run: ingest -> cited extraction -> faithfulness eval.

Run it (see real spans in your terminal):
    PYTHONPATH=src python -m rageval.pipeline --ticker AAPL --sections 3

Add the Phoenix UI (http://localhost:6006):
    PHOENIX=1 PYTHONPATH=src python -m rageval.pipeline --ticker AAPL --sections 3

Each stage is wrapped in a span; each Claude call is auto-spanned by the Anthropic
instrumentation, so you can see prompts, tokens, and latency per call.
"""
from __future__ import annotations

import argparse

from rageval import edgar, evals, parse
from rageval.config import CFG
from rageval.extract import extract_section
from rageval.obs import init_tracing

# Sections most likely to contain contract-worthy events, in priority order.
_PREFERRED = ["1A", "7", "3", "1", "5"]


def _pick_sections(sections, n):
    by_item = {s.item: s for s in sections}
    picked = [by_item[i] for i in _PREFERRED if i in by_item]
    # top up with the longest remaining sections if we need more
    rest = sorted((s for s in sections if s not in picked),
                  key=lambda s: len(s.text), reverse=True)
    return (picked + rest)[:n]


def run(ticker: str, n_sections: int = 3, model: str | None = None):
    tracer = init_tracing()
    with tracer.start_as_current_span("pipeline") as root:
        root.set_attribute("ticker", ticker)

        with tracer.start_as_current_span("ingest") as s:
            cik = edgar.ticker_to_cik(ticker)
            meta = edgar.latest_filing(cik)
            html = edgar.fetch_filing(meta).read_text(encoding="utf-8", errors="replace")
            sections = parse.split_sections(parse.html_to_text(html))
            s.set_attribute("filing.company", meta["company"])
            s.set_attribute("filing.report_date", meta["report_date"])
            s.set_attribute("sections.parsed", len(sections))

        events = []
        picked = _pick_sections(sections, n_sections)
        with tracer.start_as_current_span("extract") as s:
            s.set_attribute("sections.used", ",".join(p.item for p in picked))
            for sec in picked:
                with tracer.start_as_current_span("extract.section") as ss:
                    ss.set_attribute("item", sec.item)
                    evs = extract_section(sec.item, sec.text, model or CFG.model)
                    ss.set_attribute("events", len(evs))
                    events.extend(evs)
            s.set_attribute("events.total", len(events))

        with tracer.start_as_current_span("eval.faithfulness") as s:
            summary = evals.summary(events)
            for k, v in summary.items():
                s.set_attribute(f"faithfulness.{k}", v if v is not None else -1)

    return meta, events, summary


def main() -> None:
    ap = argparse.ArgumentParser(description="Traced ingest -> extract -> eval run.")
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--sections", type=int, default=3, help="how many sections to extract from")
    args = ap.parse_args()

    meta, events, summary = run(args.ticker, args.sections)
    print(f"\n=== {meta['company']} {meta['form']} ({meta['report_date']}) ===")
    print(f"events extracted: {summary['events']}  |  cited: {summary['cited']}  |  "
          f"grounded: {summary['grounded']}  |  grounding rate: {summary['grounding_rate']}")
    for e in events[:8]:
        flag = "OK " if e.grounded else "!! "
        print(f"  [{flag}] Item {e.item:<3} {e.type:<16} {e.event[:70]}")


if __name__ == "__main__":
    main()
