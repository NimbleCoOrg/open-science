---
date: 2026-08-13
status: DRAFT — venue undecided. Content complete and sourced; framing is venue-neutral.
sources:
  - experiments/rev4-results.md (rev 4 — frontier tier, D1/D2/D4)
  - experiments/rev3-results.md (rev 3.1 — small open-weight tier, B1–B5; carries a correction banner)
  - experiments/mast-full-dataset-replication.md (published-label self-agreement)
  - experiments/prereg-2026-08-12-frontier-annotator-agreement-rev4.md (pre-registration)
  - experiments/prereg-2026-08-10-llm-annotator-agreement-rev3.md (pre-registration)
verifiers: pipeline/rev4_score.py, pipeline/rev3_score.py
---

# Three findings about annotating a multi-agent failure taxonomy

Three results came out of this line of work. They are **independent** — none is
a step toward another, and any one could stand while the other two fell.

1. The reference labels for MAST's taxonomy do not reproduce against themselves.
2. Agreement on that taxonomy scales with annotator model size.
3. Frontier annotators converge on something, and that something is not the
   published labels.

Every number below is pre-registered, scored by a committed verifier, and backed
by raw model output committed alongside the statistic.

---

## 1. The published labels do not reproduce against themselves

MAST's released dataset contains duplicated trace payloads carrying **conflicting
annotations**. Treated as what it structurally is — a repeat-annotation
experiment the authors did not intend to run — the published labels score

> **Krippendorff α = 0.047, 95% CI [−0.065, 0.157]**
> (434 units = 31 traces × 14 cells)

**The interval contains zero.** On the file's own repeats, the published
annotation is not distinguishable from chance agreement with itself.

This is a property of the artifact, not an inference about the annotators'
process. It needs no access to their procedure, no re-annotation, and no human
ground truth — only the released file.

**Caveat that must travel with this number.** The human reference material is
**8 annotation blocks across 19 records**, not 19 independent annotations. Any
inter-rater claim built on it has to establish substrate independence first, or
it is measuring copied columns. The α above is computed over duplicated *trace*
units precisely to avoid that trap, and the cluster bootstrap is over traces.

---

## 2. Agreement scales with annotator model size

Rev 3.1 ran six open-weight coders at 2–12B against the taxonomy and found
α = 0.173 — a null. It controlled the obvious confounds: every coder passed a
framing-sensitivity gate *before* any trace was coded, and a pre-registered
instrument comparison (B3) showed the question's shape moved α by only 0.103
(free-form 0.149 vs per-cell 0.046).

The one thing it could not rule out was the plainest one: **every coder was
small.**

Rev 4 ran the identical frame, the identical prompt and the identical parser
against larger models. Reusing those as literal objects — not re-drawn, not
re-typed — is what makes the comparison interpretable at all.

| tier | coders | pooled α |
|---|---|---|
| T1 open-weight small (2–12B) | 6 | **0.173** [0.127, 0.207] |
| T2 open-weight large (70B-class) | 2 | **0.360** |
| T3 frontier | 4 | **0.598** [0.499, 0.670] |

> **D2, the tier gap: 0.425, 95% CI [0.326, 0.497] — CONFIRMED.**
> This was the decisive pre-registered test.

**The gradient is smooth, not stepped.** Agreement roughly doubles T1→T2 and
rises again to T3, with no discontinuity suggesting a capability threshold. The
middle tier earns its place: it turns "small models fail, frontier models work"
into a continuum. Cross-tier agreement (T2 against T3) is **0.362**, sitting
between the two tiers rather than at either end — the tiers are annotating the
same thing at different precision, not annotating past each other.

**This is a comparison between annotators, not between instruction-followers.**
Every frontier coder passed the same framing gate with shifts of 0.000–0.029
against a 0.30 bar — markedly *less* frame-sensitive than the small models.
Without rev 3.1's gate and instrument work, this result would be ambiguous
between "frontier models are better annotators" and "frontier models follow
instructions better."

**It is not solved.** 0.598 sits below the 0.667 conventionally treated as the
floor for reliable annotation. But it is a different world from 0.173, and a
write-up that leant on the low number without the scale caveat would have been
wrong.

### The correction this forced

Rev 3.1's write-up says: *open-weight models at this scale do not agree on this
taxonomy, and the earlier null is not an artifact of how they were asked.* Every
clause of that is still true. But the sentence a reader would take from it —
*this taxonomy cannot be annotated reliably* — is **not supported**, and rev 4
refutes it. `rev3-results.md` carries a correction banner to that effect;
nothing in it is retracted, its scope is narrowed.

---

## 3. Frontier annotators converge, and not on the published labels

Among the four frontier coders:

| | value |
|---|---|
| inter-coder agreement, α | **0.598** |
| mean concordance with the published labels | **−0.014** |
| **D4 gap** (α − concordance) | **0.612**, CI [0.502, 0.710] — **CONFIRMED** |

Four models, annotating independently, agree with **each other** substantially,
and with the published labels at a level indistinguishable from chance.

No coder was excluded by the marginal-rate gate. Marking rates ran 0.146–0.229 —
a tight band, and much closer to the corpus's own ~0.16 than the open-weight
roster's 16-fold spread. So the convergence is not an artifact of coders marking
wildly different amounts.

Set beside finding 1:

> Four frontier models, annotating independently, agree with each other about
> **an order of magnitude better than the published labels agree with
> themselves** (0.598 against 0.047).

**This is concordance, never accuracy.** It is not a claim that the models are
right. It is a claim about which reference is more *stable*, and it is
measurable without any human ground truth — which is the whole reason it is
worth stating.

---

## What is not claimed

- **Not** that frontier models annotate this taxonomy correctly. There is no
  ground truth here, by construction.
- **Not** that the taxonomy is reliable. 0.598 is below the conventional floor.
- **Not** that MAST's annotators were careless. Finding 1 is a measurement on a
  released artifact; the mechanism behind it is not established here.
- **Not** a general claim about LLM annotation. One taxonomy, one corpus,
  short-to-medium traces.

## Limits

- **No Google coder.** `gemini-3.6-flash` was recorded UNAVAILABLE — its endpoint
  refuses `reasoning.enabled=false`, so it cannot run the instrument. It was not
  substituted: swapping in another Google model after the other coders' numbers
  were visible is exactly the discretion the pre-registration forbids. T3 keeps
  four coders across **two** vendors, so D2 remains scoreable, but vendor
  coverage is a real gap. Closing it is a cheap rev 5.
- **The family effect is under-powered at both scales.** Within-family α 0.642
  vs between-family 0.428 at frontier — but on two pairs, reported with no
  verdict. Rev 3.1's B2 had the same problem (0.127, AMBIGUOUS) after its
  admission gate excluded both members of one family. Future rosters need three
  members per family so a gate can take one and leave a pair.
- **n = 24 traces**, short-to-medium only (≤8,000 tokens), three strata.
- **A reciprocal-test figure is unrecomputable** — the 2026-08-06 per-unit
  codings were never committed, so a clean-key split of that study's agreement
  figure needs re-coding.

## Provenance — and why the standing redaction rule does not gate this

All three findings rest on **MAST's public released dataset** (AG2 and Magentic
traces) plus model output generated for these studies. None of them uses the
lab's internal session corpus, and none requires naming the harness that corpus
came from.

The standing redaction rule — harness name and corpus provenance stay out of
anything public — therefore **does not constrain this write-up**. It still binds
the corpus-side work in `FINDINGS.md`, which is a separate line.

## Cost

Rev 4: **$3.00 total**, 324 calls, against a pre-registered $75 cap and a $5
projection. Neither trigger fired.

---

## Method notes worth keeping in any version of this

**A null result is only as broad as its roster.** Rev 3.1 controlled the prompt,
the frame, the instrument shape and the substrate — carefully, and at real cost —
and still produced a headline that one uncontrolled variable overturns. Scale was
named in its own limitations section and not treated as urgent. *The limitations
section is where the next experiment is, not where the caveats go to die.*

**"Cannot follow the format" is almost always the harness.** Rev 4's first
admission run reported frontier models failing the output-format gate. It was
wrong: `max_tokens=300` was being consumed entirely by reasoning tokens —
`finish_reason=length`, empty content. The same call with reasoning disabled
answers in 5 tokens. All pre-fix data was discarded before any statistic was
computed. Two guardrails came out of it: `finish_reason == "length"` is a failed
call rather than a parsed one, and reasoning is disabled explicitly on every call
for every coder — which D2 requires anyway, since comparing tiers across
different reasoning settings is not comparing like with like.

**Refusing a substitution costs coverage and is still correct.** See the Google
gap above.
