---
date: 2026-08-12
status: PRE-REGISTERED, rev 4 — not yet run. No label collected, no agreement statistic computed.
extends: prereg-2026-08-10-llm-annotator-agreement-rev3.md (rev 3.1), which is COMPLETE
evidence_base: rev3-results.md (B1 refuted, B3 confirmed, B2 does not replicate),
  mast-full-dataset-replication.md (the published labels score alpha 0.047 against themselves)
author: claude, for juniper
---

# Pre-registration rev 4: is the null about scale, or about the taxonomy?

## §0 The one-line rebuttal this study exists to answer

Rev 3.1 established that six open-weight coders do not agree on MAST's taxonomy
(**pooled α = 0.173**), that the result is not an artifact of the prompt (every
coder passed a framing-sensitivity gate first), and not an artifact of the
question's shape either (**B3: free-form α 0.149 vs per-cell α 0.046, gap
0.103**).

It has one obvious rebuttal, and it is fatal if unanswered:

> *You used 8–12B models. Of course they can't do it.*

Every coder in rev 3.1 was between 2B and 12B parameters. **Nothing in that study
distinguishes "this taxonomy cannot be annotated reliably" from "small models
cannot annotate it."** Those two worlds imply completely different papers, and we
do not currently know which one we are in.

This study is designed to be decisive between them and nothing else.

- **If frontier coders also fail to agree** → the finding is about **the
  taxonomy**. MAST's 14 cells do not carry enough operational definition for
  independent annotators to converge, at any capability level we can buy. That is
  a strong claim with direct consequences for every paper using an LLM panel as
  an annotation reference.
- **If frontier coders agree** → the finding is about **scale**. Rev 3.1 becomes
  a much more modest result ("open-weight models at this size are not viable
  annotators for this taxonomy"), and the honest headline changes.

Both outcomes are publishable. Only one of them is currently being assumed.

## §1 Substrate and frame — deliberately identical to rev 3.1

**No new frame is drawn.** This study re-uses `data/llm-agreement/frame-rev3.json`
exactly: the same 24 clean-key traces, the same three strata (S1 AG2-short, S2
AG2-long, S3 Magentic-long), the same 10 admission traces, the same 5 warm-up
traces, the same `seed=20260810`.

That is the entire point. **A different frame would confound tier with sample**,
and the comparison in D2 would be uninterpretable. The §1 integrity gate from rev
3.1 still applies and still runs: corpus sha256 `a182daad…`, the replication
recomputed from the corpus (10 affected keys / 510 records), and every frame
trace asserted to be on a clean key.

## §2 Instrument — free-form naming, unchanged

The §2.1 neutral free-form prompt from rev 3.1, byte-identical, built by the same
function in `rev3_coders.py`. The §2.3 parser and its frozen synonym table are
unchanged.

**Per-cell is dropped, and B3 is why.** Rev 3.1 pre-registered the comparison and
answered it: the two instruments land within 0.103 of each other, both near zero.
Per-cell costs ~14× (every one of fourteen calls re-sends the whole trace; median
36.5 s vs ~5 s) and produced the *lower* α. Having established that instrument
shape does not move the answer, paying 14× to re-establish it would be
superstition, not rigour.

If a reviewer wants per-cell at frontier scale it can be added as a separate
pre-registered arm. It is not needed to answer §0.

## §3 Coders

**These are different coders, not the same models on better hardware.** Rev 3.1's
roster ran locally on ollama at Q4 quantization. Hosted providers serve their own
weights and their own quantizations, and closed models are not inspectable at
all. Nothing carries over — not admission, not calibration, not the roster.

Three tiers, so scale is tested as a gradient rather than a binary:

| tier | intent | members |
|---|---|---|
| **T1 open-weight small** | rev 3.1, already collected | C1–C8 (2B–32B, local) |
| **T2 open-weight large** | the bridge | two models in the 70B–405B range, ≥2 families |
| **T3 frontier closed** | the rebuttal | two frontier models from ≥2 distinct vendors |

**T2 exists to prevent a false dichotomy.** If T3 succeeds and T1 fails, T2 says
whether the transition is gradual (a scale story) or sharp (something specific to
frontier training). Without it, a two-point comparison is a line through two
points.

**The roster, pinned 2026-08-12 against OpenRouter's live catalogue:**

| coder | slug | tier | family |
|---|---|---|---|
| F1 | `meta-llama/llama-3.3-70b-instruct` | T2 | Meta |
| F2 | `qwen/qwen-2.5-72b-instruct` | T2 | Alibaba |
| F3 | `mistralai/mistral-large-2512` | T2 | Mistral |
| F4 | `anthropic/claude-opus-5` | T3 | Anthropic |
| F5 | `anthropic/claude-sonnet-5` | T3 | Anthropic |
| F6 | `openai/gpt-5.6-sol` | T3 | OpenAI |
| F7 | `openai/gpt-5.6-terra` | T3 | OpenAI |
| F8 | `google/gemini-3.6-flash` | T3 | Google |

T2 spans three families; T3 carries **two members each for Anthropic and
OpenAI**, so the family question rev 3.1's B2 could not settle is at least
askable at frontier scale (reported as secondary, not as a hypothesis).

Slugs, and any version string the API reports per response, are written to
`data/llm-agreement/frame-rev4.json` and committed before the first call. A model
that is unavailable is **recorded as unavailable and its tier reported as
under-populated** — never silently substituted.

**Determinism.** Temperature 0 on every call. Hosted APIs may ignore seeds and
may not be reproducible across dates; where a seed is accepted it is set, and
where it is not, that is recorded per coder. **The response for every call is
written to disk before parsing**, so the analysis is reproducible from raw even
when the API is not.

## §4 Admission — the same gate, re-earned

F1 and F2 from rev 3.1 §4.2, **unchanged thresholds, applied fresh**:

- **F1** — exclude if `|p_failure − p_neutral| > 0.30` over the 10 admission
  traces under the neutral and failure frames.
- **F2** — exclude if fewer than 3 distinct output vectors under either frame.
- **Parseability** — ≥90% on the 5-trace warm-up, failure rate recorded.

Thresholds are inherited rather than re-derived precisely so they cannot be
re-tuned once frontier numbers are visible.

**A frontier model that fails admission is a result, not an embarrassment**, and
is reported with its numbers. Rev 3.1's most useful single finding came from an
exclusion: both `qwen2.5-coder` models failed for constancy, which is what
dismantled rev 2's family effect.

**If fewer than 2 coders per tier survive, that tier is reported as
under-populated and D2 is not scored.**

## §5 Hypotheses

α is Krippendorff's α, cluster bootstrap over traces, `seed=20260812`, 2,000
iterations. **A CI spanning its falsifier is AMBIGUOUS, never resolved toward the
interesting direction.**

**D1 — frontier coders agree with each other above chance.**
Pooled α across admitted T3 coders ≥ 0.40 — the same bar rev 3.1's B1 used.
*Falsifier:* < 0.40.

**D2 — the decisive one. Agreement improves with tier.**
pooled α(T3) − pooled α(T1) ≥ 0.15, where α(T1) = **0.173** from rev 3.1 on the
identical frame.
*Falsifier:* < 0.05, or the sign reverses.
**Confirmation means the rev 3.1 null is about scale** and its headline must be
narrowed to open-weight models at that size. **Refutation means the null is about
the taxonomy**, and survives a capability increase of two or more orders of
magnitude.

**D3 — the gradient is monotone.**
α(T1) ≤ α(T2) ≤ α(T3), each step reported with its CI.
Not a threshold test; scored descriptively. A **sharp** jump between two adjacent
tiers is a different finding from a smooth climb and should not be reported as
the same thing.

**D4 — frontier coders agree with the published labels no better than they agree
with each other.**
pooled α(T3) − mean α(T3 coder, published) ≥ 0.15, clean keys only, with rev
3.1's marginal-rate exclusion (a coder marking < 0.05 or > 0.60 of cells is
excluded from the mean, and the exclusion is stated).
*Falsifier:* within 0.05.
**Bounded in advance:** this is concordance with a label set that scores
**α = 0.047, CI [−0.065, 0.157]** against itself. It is never accuracy.

**D5 — cross-tier agreement.**
mean α between T1 and T3 coders, reported with no threshold. If frontier coders
agree with each other but not with small ones, "which annotator do you trust"
becomes a live question rather than a rhetorical one.

## §6 Cost, and the stopping rule that bounds it

**This study spends real money, on a shared key.** Measured from the frame
itself rather than estimated: **49 calls and 125,505 input tokens per coder**
(5 warm-up + 20 admission + 24 frame). Across the eight-coder roster that is
**≈1.0M input tokens and ≈20k output**, costing **≈$5** at the pinned models'
current pricing — an order of magnitude below the first estimate, because the
frame's traces are mostly short.

**The key is the fleet's, and the account has no spend limit.** An overspend
here degrades every NimbleCo agent, not just this study. The cap is therefore a
real safety mechanism, not a formality:

- A **hard cap of $75** is set before the first call. The runner tracks spend
  from API-reported usage and **stops** at the cap rather than continuing.
- Spend is also asserted against the pre-run estimate: if actual cost exceeds
  **10× the $5 projection** the run halts even if the cap is not reached, since
  that means a pricing or token assumption is wrong.
- Cost per coder is recorded and reported.
- If the cap is reached mid-roster, the study reports which coders completed and
  is scored as under-populated. **It does not drop the expensive coder and
  proceed**, which would let budget select the roster.

All other rev 3.1 stopping rules carry over: no coder re-run, dropped, or added
after any agreement statistic is seen; a coder missing > 20% of traces makes the
study underpowered rather than the coder droppable; the corrected
`substrate_audit` runs before any hypothesis is scored.

**No amendment.** If the instrument is wrong, the study stops and rev 5 is
written.

## §7 What gets published under each outcome

- **D2 refuted (frontier also fails):** the strong paper. Annotator agreement on
  MAST's taxonomy is near zero from 2B to frontier, the published labels do not
  reproduce against themselves, and the field's LLM-panel references rest on
  something that does not hold still. This is the result that makes the whole
  line worth writing up.
- **D2 confirmed (frontier succeeds):** rev 3.1's headline narrows to
  open-weight-at-scale, and the interesting question becomes *what* frontier
  models are converging on — the published labels (D4 answers this) or each
  other.
- **A sharp T2→T3 jump:** a capability-threshold finding, more interesting than
  either smooth outcome and worth its own follow-up.
- **Frontier coders fail admission:** framing-sensitivity at frontier scale,
  which would be a genuinely surprising result about instruction-following and
  belongs in the methods literature rather than this paper.

## §8 What this study cannot do

- **No human reference.** Unchanged and unfixable from published data.
- **Short-to-medium traces only** (≤ 8,000 tokens), inherited from rev 3.1 §3.
- **n = 24**, and admission traces are all under 2.3k tokens, so
  frame-insensitivity is demonstrated only in that band.
- **Hosted models are not reproducible artifacts.** They are versioned by the
  provider, can change under a stable name, and may be withdrawn. Raw responses
  are committed so the analysis is reproducible even when the models are not.
- **D4 is concordance, never accuracy.**

## §9 Prerequisites

1. `OPENROUTER_API_KEY` in `.env` (gitignored). **Not currently present** — this
   is the only blocker.
2. Exact model slugs pinned and committed to `frame-rev4.json` before the first
   call.
3. The rev 3.1 §1 integrity gate passing on the unchanged corpus.
4. `test_raw_output_discipline.py` passing, with the new OpenRouter collector
   detected by it.
