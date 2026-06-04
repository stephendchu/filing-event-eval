"""Control for H1: naive single-prompt extraction over the whole filing.

No retrieval, no per-section structure, no citation requirement — one shot at the
full document. This is the baseline the staged, cited pipeline (extract.py) must
beat on *valid-candidate yield* (grounded AND attributed AND settleable).
"""
from __future__ import annotations

from rageval.config import CFG
from rageval.extract import _call_model, parse_events

BASELINE_PROMPT = """Here is a company's 10-K filing. List the events that could
underlie a binary event contract ("will X happen by date Y?"). Return ONLY a JSON
array of objects, each with an "event" field.

<filing>
{text}
</filing>"""


def extract_baseline(full_text: str, model: str | None = None):
    """Naive whole-filing extraction. No citations -> events can't be grounded."""
    raw = _call_model(BASELINE_PROMPT.format(text=full_text[:60000]), model or CFG.model)
    return parse_events(raw, item="?")
