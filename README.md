# filing-event-eval

An **agent that extracts events from SEC filings (10-K / 8-K) for event-contract
markets** — each extracted event grounded in a citation back to the source
passage — with a **rigorous evaluation harness** (faithfulness, extraction
accuracy, citation correctness) and full **observability** (Arize Phoenix +
OpenTelemetry).

Built as a learning + portfolio project for AI-evals roles (W&B Weave / Arize /
Galileo). Aligns with regulated-markets + event-contracts domain. **Public data
only (SEC EDGAR); no proprietary content.**

## The task
Given a company's 10-K (or 8-K), the agent identifies the **events** described —
material events, risk factors, and forward-looking statements — and for each
returns:
- a short **event statement** (e.g. "Company expects to close the X acquisition by Q3"),
- a **citation** (the exact source passage it came from),
- a **type** (material event / risk factor / forward-looking),
- (later) a **binary resolvable form** for event contracts ("Will X close by Q3?") + a confidence.

The point isn't the extraction — it's **measuring whether the extraction is
grounded and correct**, which is the hard, valuable part.

## Architecture
```
EDGAR (10-K/8-K) ─► ingest (chunk + embed) ─► Chroma
                                                 │
                          retrieve (RAG) ────────┘
                                 │
                                 ▼
                      event-extraction agent (Claude)
                                 │  events + citations
                                 ▼
                        ┌────────────────────┐
                        │   EVAL HARNESS      │  ← the centerpiece
                        │ - faithfulness      │
                        │ - precision/recall  │
                        │ - citation accuracy │
                        │ - (calibration)     │
                        └─────────┬───────────┘
                                  ▼
                    observability (Phoenix / OTel traces)
```

## Eval harness (the differentiator)
1. **Grounding / faithfulness** — every extracted event must map to a real passage; fabricated events are flagged (the hallucination metric these companies sell).
2. **Extraction precision / recall** — vs a small hand-labeled reference set (or a stronger model as silver reference).
3. **Citation accuracy** — does the cited span actually support the event? (entailment check, LLM-judge.)
4. **(Extension) Event-contract calibration** — events → binary "will it happen?" questions; score stated confidence vs realized outcome over time (Brier score / calibration curve). This isolates decision quality from noise.

## Build slices
- [ ] **Slice 1 — EDGAR ingest:** fetch 10-K/8-K from EDGAR, chunk (section-aware), embed → Chroma.
- [ ] **Slice 2 — extraction agent:** retrieve → extract events with citations (structured JSON).
- [ ] **Slice 3 — eval harness:** faithfulness + citation accuracy + precision/recall, traced.
- [ ] **Slice 4 — event-contract framing + calibration.**

## Stack
Python · Anthropic Claude (SDK) · Chroma · sentence-transformers · **Arize Phoenix + OpenTelemetry** · LLM-as-judge evals.

## Quickstart
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add ANTHROPIC_API_KEY

python -m rageval.ingest --ticker AAPL --form 10-K   # fetch + embed a filing
python -m rageval.extract --ticker AAPL              # extract events + citations
python -m rageval.eval --ticker AAPL                 # score grounding + citations
```
*Learning + portfolio project — public, SEC EDGAR data only, no proprietary content.*
