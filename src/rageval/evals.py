"""Evaluation metrics. Starts with faithfulness (the metric W&B/Arize sell).

Faithfulness here = **grounding rate**: of the events that carry a citation, what
fraction have a citation that's actually a verbatim span of the source section
(via `grounding.is_grounded`). High grounding rate = the model isn't fabricating
quotes. This is the deterministic *floor* eval, computed with no extra LLM calls.
"""
from __future__ import annotations

from rageval.extract import Event


def grounding_rate(events: list[Event]) -> float | None:
    """Fraction of cited events whose citation is grounded in the source.

    Returns None if no events carry a citation (nothing to check).
    """
    cited = [e for e in events if e.citation]
    if not cited:
        return None
    return round(sum(bool(e.grounded) for e in cited) / len(cited), 3)


def summary(events: list[Event]) -> dict:
    """A compact eval summary for logging / trace attributes."""
    return {
        "events": len(events),
        "cited": sum(1 for e in events if e.citation),
        "grounded": sum(1 for e in events if e.grounded),
        "grounding_rate": grounding_rate(events),
    }
