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


def _call_model(prompt: str, model: str) -> str:
    msg = anthropic.Anthropic().messages.create(
        model=model, max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")


def parse_events(raw: str, item: str) -> list[Event]:
    """Parse the model's JSON array into Events (tolerant of fences / extra prose)."""
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return []
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    out: list[Event] = []
    for d in data:
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
