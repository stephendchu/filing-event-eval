"""Stage 5: settleability filter — turn a grounded event into a *contract candidate*.

An extracted, grounded event is only an event-contract candidate if it can be
reframed into a **binary, dated, objectively-resolvable** question with an
**authoritative future settlement source** (a later filing, a regulator, a market
print). The filing is the *source of the question*, never the settlement.

Most forward-looking statements fail this — they're soft, conditional, undated.
That's expected: the **settleability rate is itself a finding** (how few filing
statements are actually contractable). We reject honestly rather than forcing it.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from rageval.config import CFG
from rageval.extract import _call_model


@dataclass
class Contract:
    event: str
    settleable: bool
    question: str | None = None          # "Will X happen by date Y?"
    deadline: str | None = None
    settlement_source: str | None = None
    reason: str = ""


SETTLE_PROMPT = """An event extracted from an SEC 10-K is below. Decide if it can become a
SETTLEABLE event contract: a binary "Will X happen by date Y?" question that resolves
objectively from an authoritative FUTURE source (a later filing, a regulator, an exchange
print). The 10-K statement is the SOURCE of the question, NEVER the settlement.

Event: {event}
Source quote: {citation}

Return ONLY JSON.
If settleable:
{{"settleable": true, "question": "Will ...?", "deadline": "<specific date or period>", "settlement_source": "<e.g. next 10-Q, SEC filing, exchange close>"}}
If not:
{{"settleable": false, "reason": "<no deadline | not objective/binary | conditional | no settlement source>"}}

It is settleable ONLY if it is binary, has a definite deadline, AND an objective future
settlement source. Most statements are NOT settleable — that is the correct, expected answer."""


def _parse(raw: str, event: str) -> Contract:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return Contract(event, False, reason="unparseable")
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return Contract(event, False, reason="unparseable")
    if d.get("settleable") is True:
        return Contract(event, True, d.get("question"), d.get("deadline"),
                        d.get("settlement_source"), reason="")
    return Contract(event, False, reason=str(d.get("reason", "")))


def _gate(c: Contract) -> Contract:
    """Belt-and-suspenders: 'settleable' requires all three fields, or we reject.

    The model claiming settleable isn't enough — a contract with no deadline or no
    settlement source can't actually be settled, so we don't accept it.
    """
    if c.settleable and not (c.question and c.deadline and c.settlement_source):
        return Contract(c.event, False, c.question, c.deadline, c.settlement_source,
                        reason="missing question/deadline/settlement_source")
    return c


def classify(event: str, citation: str, model: str | None = None) -> Contract:
    raw = _call_model(SETTLE_PROMPT.format(event=event[:600], citation=citation[:600]),
                      model or CFG.model)
    return _gate(_parse(raw, event))


def settleability_rate(contracts: list[Contract]) -> float | None:
    """Fraction of events that are settleable contract candidates."""
    if not contracts:
        return None
    return round(sum(c.settleable for c in contracts) / len(contracts), 3)
