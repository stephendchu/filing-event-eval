"""Citation grounding — the seed of the faithfulness eval.

An extracted event is only trustworthy if its citation is actually IN the source
section (i.e. the model didn't fabricate the quote). This verbatim check is cheap,
deterministic, and becomes the *floor* of the eval harness — before any LLM-judge.
"""
from __future__ import annotations

import re


def normalize(s: str) -> str:
    """Lowercase + collapse whitespace, so quotes match despite formatting noise."""
    return re.sub(r"\s+", " ", s or "").strip().lower()


def is_grounded(citation: str, source: str, min_chars: int = 12) -> bool:
    """True if `citation` appears (whitespace-normalized) verbatim in `source`.

    Short citations are rejected: a handful of characters can match by accident
    and aren't a meaningful, checkable quote.
    """
    c = normalize(citation)
    if len(c) < min_chars:
        return False
    return c in normalize(source)
