# Reliability & Orchestration Plan

A pipeline over messy public filings *will* hit missing sections, malformed HTML,
rate limits, and unresolvable entities. This documents how the pipeline **degrades
gracefully and observably** instead of crashing — and how every failure becomes a
**traced, measured signal** (it flows into the same OpenTelemetry/Phoenix spans
and eval metrics as everything else).

## Principles
1. **Never crash the batch on one item.** Per-item `try/except`; the run continues
   and records the failure.
2. **Partial results beat no results.** If Item 1A is missing, extract from the
   sections we *do* have and record the coverage gap.
3. **Failures are first-class data.** Every failure sets span attributes + a
   counter, so "things not being there" is *measurable*, not hidden.
4. **Bounded retries with backoff** for transient faults (network, 429);
   **fail fast** for config faults (bad SEC User-Agent) with an actionable message.
5. **Idempotent + cached.** Filings are cached; re-runs are resumable and don't
   re-hit EDGAR.

## Failure modes → handling
| Stage | Failure | Detection | Graceful handling | Observed as |
|---|---|---|---|---|
| Ingest | Ticker not found | lookup miss | clear error; suggest verifying the ticker | `error` span |
| Ingest | EDGAR 403 | HTTP 403 | **fail fast**: "set SEC_USER_AGENT (name + email)" | `error` span |
| Ingest | EDGAR 429 / 5xx / timeout | HTTP / exception | exponential backoff + bounded retry, then skip + record | `ingest.retries` |
| Ingest | No 10-K for the form | empty filter | record "no filing"; skip company | `coverage.filings` |
| Parse | Malformed HTML | parse exception | fall back to whole-document text | `parse.status=degraded` |
| Parse | **Expected Item missing** (e.g. 1A) | item absent | continue with available Items; record gap | `coverage.sections` |
| Parse | Zero sections | empty | fall back to whole-doc extraction | `parse.status=fallback` |
| Extract | Model 429 / throttle | rate-limited result | backoff + bounded retry, then skip section | `extract.retries` |
| Extract | Invalid JSON | parse fail | return `[]` for that section; record | `extract.parse_fail` |
| Extract | Zero events | empty (valid!) | record `events=0`; not an error | `events.total` |
| Ground | Citation not verbatim | `is_grounded=False` | keep event, flag ungrounded | `faithfulness.grounding_rate` |
| Resolve | Entity not found | lookup miss | keep event, mark `unresolved` | `resolve.resolution_rate` |
| Resolve | **Ambiguous** (>1 match) | multiple matches | mark `ambiguous` + candidates; **do not guess** | `resolve.ambiguous` |
| Resolve | **As-of-date drift risk** | filing date ≠ current mapping era | flag `asof_risk`; don't silently use today's mapping | `resolve.asof_risk` |

## Operational health metrics (the dashboard view)
- **Coverage:** % filings successfully ingested · % expected Items present · % sections parsed.
- **Extraction health:** parse-failure rate · retry rate · events/section.
- **Quality:** grounding rate · resolution rate · ambiguity rate · as-of-date-risk rate.

These are exactly what an on-call/observability view would show — the pipeline's
*operational* health alongside its *quality*.

## Why this is here
"It works on Apple's latest 10-K" is a demo. **"It degrades gracefully, records
every failure as a measured signal, and tells you its own operational health"** is
a system. The second is what you run in a regulated, high-consequence environment —
and it's the orchestration maturity this project is meant to demonstrate.
