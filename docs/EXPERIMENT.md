# Experiment: naive whole-filing vs section-aware extraction

**Pilot, n = 2 filings (AAPL, MSFT). Directional — not conclusive at this scale;
the value here is the controlled design and the honest read, not the magnitude.**

## The metric: grounding (a.k.a. faithfulness)
When the model extracts an event it must attach a **citation** — a quote it claims
came from the filing. **Grounding** verifies that quote is real: normalize
whitespace/case, then check it's a **verbatim substring** of the source. Real →
grounded; not found → ungrounded (paraphrased or fabricated). **Grounding rate** =
fraction of cited events whose citation actually appears in the source. It's the
cheapest, most objective hallucination check — no LLM judge, just string matching.

## The two arms (one variable changes: *how* the filing is read)
- **Baseline (control)** — *naive whole-filing*: dump the entire 10-K (truncated to
  ~60k chars to fit context) into one prompt; ask for all events + citations. One shot.
- **Treatment** — *section-aware*: parse the 10-K into its Items, then extract from
  each section separately (a focused prompt per section).

## Hypothesis — what we expected, and why
1. **Better grounding** (focused context → less fabrication): quoting from one short
   section should be more accurate than quoting from a giant truncated blob.
2. **More coverage** (no truncation): the baseline never sees most of the filing;
   the treatment walks every section.

## Results
| | Baseline | Treatment |
|---|---|---|
| **AAPL** grounding (grounded/cited) | 0.571 (8/14) | 0.538 (14/26) |
| **MSFT** grounding | 0.889 (8/9) | 0.909 (20/22) |
| **Settleable candidates** | — | **0** (both) |

## Findings (honest)
- **Coverage bet — confirmed.** Treatment surfaced ~**2× more** grounded events
  (saw every section; the baseline was truncated).
- **Grounding bet — *not* confirmed.** Grounding rates were ~**tied**. Once the model
  is *asked* to cite, it quotes about as faithfully from a big blob as from a small
  section — the fabrication-reduction we expected didn't appear here.
- **Settleability = 0 — and it's real.** Spot-checking the rejects validated the
  filter: the extracted events are **risk factors** ("margins *may* face volatility"
  — not binary, no deadline) and **historical facts** ("R&D *increased* 10%" — already
  happened, not a future event). Most 10-K statements simply **aren't contractable**.

## The insight
Generic extraction pulls *risk + historical* events, which are structurally
non-settleable. **To source event-contract candidates, extraction must specifically
target forward-looking, *dated* statements.** Acting on that is what turns
valid-candidate-yield from 0 into real candidates — the next iteration.

## The takeaway
The "focused context → fewer hallucinations" intuition *sounded* right; the data
said grounding was **tied** and the real win was **coverage**. That's the point of
measuring instead of assuming — and reporting the tied grounding honestly is what
makes the coverage result trustworthy.

## Caveats
n = 2, single fiscal period; grounding is a strict *verbatim* check (no judge bias,
but it doesn't credit semantically-supported paraphrases); section parsing is
MVP-grade. Scale to ~10 filings + a forward-looking-targeted extractor next.

## Reproduce
```bash
PYTHONPATH=src python scripts/run_experiment.py --tickers AAPL MSFT --sections 3
```
