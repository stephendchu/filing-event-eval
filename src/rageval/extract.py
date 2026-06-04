"""Stage 2 (treatment): extract events from a filing section, each grounded in a
verbatim citation.

The citation is the load-bearing part — every event must quote the exact source
span it came from, so the eval can check grounding. This structured, cited,
per-section extraction is the *treatment*; `baseline.py` is the naive control.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

import anthropic

from rageval.config import CFG
from rageval.grounding import is_grounded

EVENT_TYPES = ("material", "risk", "forward_looking")

EXTRACT_PROMPT = """You are analyzing ONE section of an SEC 10-K to find EVENTS that
could underlie an event contract (a binary "will X happen by date Y?" market).

Extract only concrete events — material events, risk factors, or forward-looking
statements. For EACH event return an object with:
- "event": one sentence describing it
- "type": one of material | risk | forward_looking
- "citation": a VERBATIM quote copied exactly from the section text below. Do NOT
  paraphrase the citation — copy the words as they appear.

Return ONLY a JSON array (no prose). If there are no events, return [].

<section item="{item}">
{text}
</section>"""


@dataclass
class Event:
    event: str
    type: str
    citation: str
    item: str
    grounded: bool | None = None  # set by the grounding check


def _call_model(prompt: str, model: str, max_tokens: int = 4000) -> str:
    msg = anthropic.Anthropic().messages.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def _json_objects(text: str) -> list[dict]:
    """Recover every complete top-level {...} object from text.

    Brace-scans instead of requiring a complete [...] array, so a JSON array that
    got *truncated* by the output-token cap still yields all the complete objects
    before the cut (the last partial one is simply dropped). Also tolerant of code
    fences / surrounding prose.
    """
    objs: list[dict] = []
    depth = 0
    start = None
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    objs.append(json.loads(text[start:i + 1]))
                except json.JSONDecodeError:
                    pass
                start = None
    return objs


def parse_events(raw: str, item: str) -> list[Event]:
    """Parse the model's JSON into Events (tolerant of fences, prose, truncation)."""
    out: list[Event] = []
    for d in _json_objects(raw):
        if isinstance(d, dict) and d.get("event"):
            out.append(Event(
                event=str(d.get("event", "")).strip(),
                type=str(d.get("type", "")).strip(),
                citation=str(d.get("citation", "")).strip(),
                item=item,
            ))
    return out


def extract_section(item: str, text: str, model: str | None = None) -> list[Event]:
    """Extract grounded events from one section (the treatment path)."""
    raw = _call_model(EXTRACT_PROMPT.format(item=item, text=text[:12000]), model or CFG.model)
    events = parse_events(raw, item)
    for e in events:
        e.grounded = is_grounded(e.citation, text)  # verify the quote is real
    return events
