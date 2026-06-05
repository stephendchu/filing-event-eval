"""Control for H1: naive single-prompt extraction over the whole filing.

No retrieval, no per-section structure, no citation requirement — one shot at the
full document. This is the baseline the staged, cited pipeline (extract.py) must
beat on *valid-candidate yield* (grounded AND attributed AND settleable).
"""
from __future__ import annotations

from rageval.config import CFG
from rageval.extract import _call_model, parse_events
from rageval.grounding import is_grounded

# Fair baseline: it ALSO must cite, so the experiment isolates the value of
# *section-aware* extraction (the treatment), not just "we asked one to cite."
BASELINE_PROMPT = """Here is a company's 10-K filing (possibly truncated). List events that
could underlie a binary event contract ("will X happen by date Y?"). For EACH event include
a VERBATIM citation copied exactly from the filing. Return ONLY a JSON array of objects, each
with "event", "type", and "citation".

<filing>
{text}
</filing>"""


def extract_baseline(full_text: str, model: str | None = None):
    """Naive whole-filing single-prompt extraction (control). Cited, then grounded
    against the full text — the same grounding bar the treatment is held to."""
    # Whole-filing extraction lists many events -> needs a large output budget, or the
    # JSON array truncates. (The earlier 0-event baseline was exactly this artifact.)
    raw = _call_model(BASELINE_PROMPT.format(text=full_text[:60000]), model or CFG.model,
                      max_tokens=8000)
    events = parse_events(raw, item="?")
    for e in events:
        e.grounded = is_grounded(e.citation, full_text)
    return events
