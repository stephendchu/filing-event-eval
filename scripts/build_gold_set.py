"""Draft a GOLD SET (reference list) for measuring extraction recall.

The AI does the word-by-word reading and drafts an exhaustive, cited event list per
section. YOU then verify it (tick keep / drop, fix citations, ADD anything missed) —
that human pass is what breaks the circularity (an unverified AI reference = AI
grading AI, which can't detect a miss both models share).

    PYTHONPATH=src python scripts/build_gold_set.py --ticker AAPL --sections 3
Writes reports/gold/gold_set_<TICKER>.md for you to verify.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from rageval import edgar, parse
from rageval.config import CFG
from rageval.extract import _call_model, parse_events
from rageval.grounding import is_grounded

PREFERRED = ["1A", "7", "3", "1", "5"]
OUT = Path("/mnt/c/Users/Steph/agentic-rag-eval/reports/gold")

# Exhaustive (thorough) prompt — deliberately different from the contract-focused
# extractor, so the reference isn't just a copy of the system under test.
GOLD_PROMPT = """You are building a REFERENCE LIST to evaluate an extraction system.
From the SEC 10-K section below, **exhaustively** list EVERY distinct factual or
forward-looking statement that could matter for an event contract — be thorough, do
not skip minor ones. For each: a one-line summary and a VERBATIM citation copied
exactly from the text. Return ONLY a JSON array of {{"event":"...","citation":"..."}}.

<section item="{item}">
{text}
</section>"""


def _pick(sections, n):
    by = {s.item: s for s in sections}
    picked = [by[i] for i in PREFERRED if i in by]
    rest = sorted((s for s in sections if s not in picked), key=lambda s: len(s.text), reverse=True)
    return (picked + rest)[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ticker", required=True)
    ap.add_argument("--sections", type=int, default=3)
    args = ap.parse_args()

    cik = edgar.ticker_to_cik(args.ticker)
    meta = edgar.latest_filing(cik)
    html = edgar.fetch_filing(meta).read_text(encoding="utf-8", errors="replace")
    sections = parse.split_sections(parse.html_to_text(html))

    OUT.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Gold set (DRAFT — VERIFY ME) — {meta['company']} {meta['form']} ({meta['report_date']})",
        "",
        "> **AI-drafted. You must verify before using it as ground truth.**",
        "> For each item: keep `[x]` / drop `[ ]`, fix the citation if wrong, and **ADD**",
        "> anything the draft missed. An unverified AI list = AI grading AI.",
        "",
    ]
    for s in _pick(sections, args.sections):
        raw = _call_model(GOLD_PROMPT.format(item=s.item, text=s.text[:12000]), CFG.model, max_tokens=6000)
        events = parse_events(raw, s.item)
        lines.append(f"## Item {s.item}  ({len(events)} drafted)")
        for e in events:
            g = "grounded" if is_grounded(e.citation, s.text) else "UNGROUNDED — fix or drop"
            lines.append(f"- [x] {e.event}")
            lines.append(f"      cite: \"{e.citation[:140]}\"  _({g})_")
        lines.append("")
        time.sleep(2)

    path = OUT / f"gold_set_{args.ticker}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
