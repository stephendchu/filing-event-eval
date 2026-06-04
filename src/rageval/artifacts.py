"""Typed artifact lookup with anti-fabrication (see docs/ARTIFACTS.md).

A 10-K's value is in *specific* artifacts, and the reliability question is: what
happens when the one you asked for isn't there? The rule: the model may answer
`not_disclosed`, and any claimed value must be grounded in a verbatim citation —
otherwise it's rejected as `ungrounded` (a likely fabrication).

Flagship: Apple stopped disclosing unit sales in 2018, so
`find_metric("iPhone unit sales", ...)` must return `not_disclosed`, never a number.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from rageval.config import CFG
from rageval.extract import _call_model
from rageval.grounding import is_grounded


@dataclass
class MetricResult:
    metric: str
    status: str                 # disclosed | not_disclosed | ungrounded
    value: str | None = None
    unit: str | None = None
    period: str | None = None
    citation: str | None = None


FIND_METRIC_PROMPT = """Find this specific metric in the SEC 10-K text below:
"{metric}"

If the filing discloses it, return JSON:
{{"status":"disclosed","value":"...","unit":"...","period":"...","citation":"<verbatim quote from the text>"}}
The citation MUST be copied exactly from the text.

If the filing does NOT disclose this metric, return exactly:
{{"status":"not_disclosed"}}
Do NOT guess, estimate, or use outside knowledge. "not_disclosed" is the correct
answer when the metric is not in the text.

<text>
{text}
</text>"""


def _parse(raw: str, metric: str) -> MetricResult:
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return MetricResult(metric, "not_disclosed")
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return MetricResult(metric, "not_disclosed")
    if d.get("status") == "disclosed":
        return MetricResult(metric, "disclosed", d.get("value"), d.get("unit"),
                            d.get("period"), d.get("citation"))
    return MetricResult(metric, "not_disclosed")


def _verify(result: MetricResult, source: str) -> MetricResult:
    """Anti-fabrication: a 'disclosed' value must be grounded, else reject it."""
    if result.status == "disclosed" and not is_grounded(result.citation or "", source):
        return MetricResult(result.metric, "ungrounded")
    return result


def find_metric(metric: str, text: str, model: str | None = None) -> MetricResult:
    """Look up one metric in a filing section; honest absence + grounded values only."""
    raw = _call_model(FIND_METRIC_PROMPT.format(metric=metric, text=text[:12000]),
                      model or CFG.model)
    return _verify(_parse(raw, metric), text)
