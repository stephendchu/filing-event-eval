# Artifacts & Absence Handling

A 10-K's value is in **specific, typed artifacts** — not fuzzy "events." And the
reliability question that matters in a high-consequence pipeline is: **what happens
when the artifact you asked for isn't there?** This documents the artifact types
and, for each, *how absence is handled* — because graceful, honest absence is the
whole point.

## Three kinds of "missing" — handled differently
1. **`not_disclosed`** — the filing simply doesn't report it (e.g. Apple stopped
   disclosing unit sales in 2018). This is a **positive finding**, not an error,
   and **never** a reason to fabricate a number.
2. **`incomplete`** — the artifact is present but missing fields (a value with no
   period/unit). Keep what's there, flag the gap; don't infer the rest.
3. **`section_missing`** — an expected Item wasn't parsed (we saw Item 1A drop out
   on Apple). Record a **coverage gap** and degrade gracefully (extract from the
   sections we do have).

## The anti-fabrication rule (the spine)
> The model **may** answer `not_disclosed`. Any **claimed value must carry a
> verbatim citation that grounds in the source**; if it doesn't, we reject it as
> `ungrounded` — a likely fabrication. So "not in the filing" can only ever surface
> as `not_disclosed` or `ungrounded` — **never** as a confident fake number.

This reuses the grounding check from the eval: the citation is the proof, and a
value without a real citation doesn't count.

## Artifact types — fields + how absence is addressed
| Artifact | Key fields | If the piece is missing → handling |
|---|---|---|
| **Identity / reference** | name, ticker, CIK, fiscal period | not found → `unresolved`; >1 match → `ambiguous` (candidates, no guess); old filing → `asof_risk`. *(resolver, done)* |
| **Quantitative fact** (e.g. "revenue up") | metric, value, unit, period, direction, citation | **metric not disclosed → `not_disclosed`** (the iPhones-sold case); value w/o unit/period → `incomplete`; value only in a table → `low_confidence`; claimed but uncited → `ungrounded` (rejected). |
| **Forward-looking commitment** | claim, subject, deadline, citation | no deadline → `not_settleable`; vague/conditional → `low_settleability`; none in filing → simply not emitted (empty is valid). |
| **Legal / regulatory event** | matter, status, citation | outcome/date unknown → keep as open question, flag `unresolved_outcome`. |
| **Subsequent event** (Item 9B) | description, date, citation | Item 9B empty/absent → no subsequent events (valid absence). |
| **Risk factor** | risk, category, citation | Item 1A not parsed → `section_missing` coverage gap; boilerplate → low priority. |

## Flagship example: "iPhone unit sales"
Apple stopped disclosing unit sales in 2018, so it is **not in the 10-K**:
- `find_metric("iPhone unit sales", ...)` → **`not_disclosed`** (correct).
- If a model invents *"230 million units,"* its citation won't ground in the text →
  **`ungrounded`** → rejected.
- Contrast: `find_metric("research and development expense", ...)` → **`disclosed`**
  with a grounded citation.

That single contrast — *honest absence on one, grounded fact on the other* — is the
clearest demonstration of the pipeline's reliability posture.
