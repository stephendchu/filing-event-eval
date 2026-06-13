# Project Plan — AI for Event-Contract Sourcing from SEC Filings

*(Plan for review. Public data only — SEC EDGAR. No proprietary content.)*

## 1. One line
An AI pipeline that **sources event-contract candidates from SEC filings (10-K/8-K)** —
extracting events, grounding each in a citation, resolving the entities with
as-of-date integrity, and filtering to what's actually *settleable* — wrapped in a
**rigorous eval harness** and full **observability**. Headline = "AI for event
contracts" (hot); under the hood = reference-data/symbol-processing rigor (deep, un-fakeable).

## 2. Pipeline
```
ingest (EDGAR 10-K/8-K)
   ▼  section-aware parse
extract events + citations          → faithfulness / citation eval
   ▼
entity / symbol resolution (as-of-date) → reference-data integrity eval
   ▼
contractability filter (settleable?) → settleability eval
   ▼
observability (Phoenix / OpenTelemetry) across every stage
```
The output is **event-contract *candidates***, not securities. Listing/settlement is
the exchange's regulated process — out of scope by design (keeps it credible).

## 3. Hypothesis & control (run it as an experiment, not a demo)
**H1 (primary):** a grounded, staged pipeline (cited extraction → as-of-date entity
resolution → settleability filter) yields materially more *valid* candidates than a
naive single-prompt LLM — and the gap is **measurable**.
- **Control / baseline:** one LLM call — *"Here's a 10-K; list binary/tradeable events."*
  No retrieval, no citation requirement, no entity resolution, no settleability gate.
- **Treatment:** the full staged pipeline.
- **Primary metric:** *valid-candidate yield* = (grounded AND correctly-attributed AND
  settleable) / proposed. Plus **hallucination rate** = 1 − faithfulness.

**H2 (the personal edge):** as-of-date entity resolution beats naive "resolve to today"
on historical filings where tickers/issuers changed — measurable attribution-error reduction.

This mirrors the rigor of my prior eval study (strong baseline, controlled comparison,
honest reporting).

## 4. Best evals (the centerpiece — ranked)
1. **Faithfulness / grounding** *(primary)* — does the cited passage actually *entail* the
   extracted event? (LLM-judge entailment + span check.) This is the hallucination metric
   W&B/Arize literally sell.
2. **Citation validity** — the cited span exists and supports the claim (citation precision).
3. **Extraction precision/recall** — vs a small **hand-labeled gold set** (~10 filings);
   precision weighted (a false event = a bad contract).
4. **Entity-resolution accuracy (as-of-date)** — correct issuer/instrument mapping; handles
   ticker reuse / renames. *(My differentiator.)*
5. **Settleability rate** — % of events reframable into a clean settleable contract
   (binary + dated + authoritative future settlement source). Most won't survive — that
   number *is* a finding.
6. **(Extension) Resolution accuracy + calibration** — longitudinally, did the named
   settlement source resolve them? Brier/calibration on any stated confidence.
- **Judge validation (don't skip):** calibrate the LLM-judge against ~30–50 human-labeled
  items; report agreement. Never ship an unvalidated judge.

## 5. What employers (W&B / Arize / Galileo / Anthropic) want to see
- **Traces of every LLM call** (prompt, context, raw + parsed output, cost, latency).
- A **repeatable eval suite** with multiple metrics + a results view.
- **Offline eval** (vs a dataset) *and* **online/production monitoring** (live traces).
- **Baseline vs treatment** comparison (rigor) + **failure analysis** (show caught hallucinations).
- Reproducibility, honest nulls/limits — *not* a flashy demo.
- Built on **their stack** (Phoenix / Weave / OTel) → "already knows the product."
- Core signal: *"can make LLM behavior measurable, traceable, improvable."*

## 6. Do we need complicated RAG? — No (and saying so is the senior move)
- A 10-K is **one large structured doc**. The task is extraction *within* a known doc, not
  retrieval across a huge corpus → **section-aware parsing (by Item) + map-reduce over
  sections** is cleaner and *more faithful* than semantic retrieval.
- Use **vector RAG only** for cross-filing or query-driven tasks (later slice).
- Knowing **when not to reach for a vector DB** is a maturity signal. Sophistication lives in
  **extraction + entity resolution + eval**, not the retriever.

## 7. Logging & orchestration (where we show chops)
- **Observability (deep):** OpenTelemetry spans + Phoenix on **every stage**; OpenInference
  conventions; capture full I/O, token cost, latency, eval scores; tag spans by stage.
  This is exactly what these companies sell — instrument it well.
- **Orchestration (tight, not bloated):**
  - MVP: a clean typed linear pipeline, fully traced.
  - Upgrade: **LangGraph** 4-node graph (extract → resolve → contractability → critic),
    structured outputs (tool use / JSON schema), retries, guardrails (reject non-settleable).
  - Avoid 10-agent theater. A small, instrumented, *evaluable* graph beats a sprawling one.

## 8. Stack
Python · Anthropic Claude (SDK) · section-aware filing parser · Chroma (only when vector RAG
is justified) · **Arize Phoenix + OpenTelemetry** · LangGraph (upgrade slice) · LLM-as-judge evals.

## 9. Build slices
- **MVP (weekend):** EDGAR ingest (1 filing) → cited extraction → faithfulness eval → traced. Baseline vs treatment on 1–3 filings.
- **Interview version (2–4 wks):** + entity resolution (as-of-date) + settleability filter + eval suite over ~10 filings + Phoenix dashboard.
- **Offer version (6–10 wks):** + LangGraph multi-node + critic + calibration/longitudinal resolution + benchmark (baseline vs pipeline) with a writeup.

## 10. Scope discipline (don't drift)
- It **sources candidates**, doesn't mint securities (regulated — out of scope).
- Don't over-RAG; don't become a trading bot; don't ship an unvalidated judge.
- Public EDGAR data only.

## 11. Open questions for review
- Best primary metric framing: *valid-candidate yield* vs reporting each eval separately?
- Gold-set size/labeling effort vs using a stronger model as silver reference?
- Phoenix vs W&B Weave for the headline traces (or both)?
- Is H2 (as-of-date resolution) worth a dedicated experiment, or a feature + spot-check?
