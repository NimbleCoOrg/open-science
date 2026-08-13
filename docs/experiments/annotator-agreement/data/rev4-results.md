---
date: 2026-08-12
study: prereg-2026-08-12-frontier-annotator-agreement-rev4.md
status: COMPLETE — D1, D2, D4 scored; D3 descriptive; D5 secondary.
verifier: pipeline/rev4_score.py
data: data/llm-agreement/results-rev4.json, data/llm-agreement/raw/rev4-*.jsonl
corrects: rev3-results.md — its null is a statement about model scale, not about the taxonomy
---

# The null was about scale, and rev 3.1's headline has to narrow

Rev 3.1 found six open-weight coders agreeing at **α = 0.173** on MAST's
taxonomy, established it was not an artifact of the prompt (every coder passed a
framing gate first) and not an artifact of the question's shape
(B3: free-form 0.149 vs per-cell 0.046). The one thing it could not rule out was
the obvious one: **every coder was between 2B and 12B parameters.**

Rev 4 ran the identical frame, the identical prompt and the identical parser
against larger and frontier models.

| | statistic | 95% CI | verdict |
|---|---|---|---|
| **D1** frontier pooled α ≥ 0.40 | **0.598** | [0.499, 0.670] | **CONFIRMED** |
| **D2** α(T3) − α(T1) ≥ 0.15 | **0.425** | [0.326, 0.497] | **CONFIRMED** |
| **D3** monotone gradient | — | | descriptive |
| **D4** α(T3) − concordance ≥ 0.15 | **0.612** | [0.502, 0.710] | **CONFIRMED** |

**D2 is confirmed, and it is the answer the study was built to get.** The rev 3.1
null is a statement about **model scale**, not about the taxonomy.

## The gradient

| tier | coders | α |
|---|---|---|
| T1 open-weight small (2–12B, rev 3.1) | 6 | **0.173** |
| T2 open-weight large (70B-class) | 2 | **0.360** |
| T3 frontier | 4 | **0.598** |

**Smooth, not stepped.** Agreement roughly doubles from T1 to T2 and rises again
to T3, with no discontinuity that would suggest a capability threshold. D3 was
pre-registered precisely so a two-point comparison could not be mistaken for a
gradient, and the middle point earns its place: it turns "small models fail,
frontier models work" into a continuum.

Cross-tier agreement (T2 against T3) is **0.362**, sitting between the two tiers
rather than at either end — the tiers are not annotating past each other, they
are annotating the same thing with different precision.

## What has to be said plainly

**The claim rev 3.1 licensed is narrower than the claim it appeared to make.**
Its write-up says "open-weight models at this scale do not agree on MAST's
taxonomy, and the earlier null was not an artifact of how they were asked." Every
clause of that is still true. But the sentence people would have taken from it —
*this taxonomy cannot be annotated reliably* — is **not** supported, and rev 4
refutes it.

Frontier coders reach α = 0.598. That is below the 0.667 conventionally treated
as the floor for reliable annotation, so this is not "solved". But it is a
different world from 0.173, and any write-up that leant on the low number without
the scale caveat would have been wrong.

**The instrument work still holds.** Rev 3.1's framing gate and its B3
instrument-comparison were not wasted: without them, this result would be
ambiguous between "frontier models are better annotators" and "frontier models
follow instructions better." Every coder here passed the same framing gate, with
shifts of 0.000–0.029 against a 0.30 bar — markedly *less* frame-sensitive than
the small models. The comparison is between annotators, not between
instruction-followers.

## D4 — they converge, and not on the published labels

**0.612, CI [0.502, 0.710].** Frontier coders agree with each other far more than
any of them agrees with MAST's published annotation. No coder was excluded by the
marginal-rate gate; marking rates ran 0.146–0.229, a tight band and much closer to
the corpus's own ~0.16 than the open-weight roster's 16-fold spread.

Set beside `mast-full-dataset-replication.md` — where the published labels score
**α = 0.047, CI [−0.065, 0.157]** against themselves on the file's own repeats —
this is the sharpest result in the whole line of work:

> **Four frontier models, annotating independently, agree with each other about
> ten times better than MAST's published labels agree with themselves.**

That is not a claim that the models are right. It is a claim about which
reference is more stable, and it is measurable without any human ground truth.

## Secondary

**Family effect, at frontier scale.** Within-family α **0.642** (2 pairs:
Anthropic, OpenAI) against between-family **0.428**. A gap of 0.214, on two pairs.
Rev 3.1's B2 was AMBIGUOUS at 0.127 with the same problem — too few within-family
pairs — so this is *suggestive of the same effect at a larger size*, reported with
no threshold and no verdict. The strongest pair in the study is `gpt-5.6-sol`
against `gpt-5.6-terra` at **0.735**, and the weakest frontier pairing is
`claude-opus-5` against `llama-3.3-70b` at 0.212.

**Two non-admissions**, neither a capability judgement:

- `qwen/qwen-2.5-72b-instruct` — genuine F2 exclusion, one distinct vector across
  ten traces, 62% parseability.
- `google/gemini-3.6-flash` — **UNAVAILABLE**. Its endpoint refuses
  `reasoning.enabled=false` outright, so it cannot run the study's instrument at
  all. Recorded rather than substituted: swapping in another Google model after
  the other coders' numbers were visible is exactly the discretion §6 forbids.
  T3 keeps four coders across two vendors, so D2 remains scoreable — but the
  study has **no Google coder**, and that is a real gap in vendor coverage.

## Cost

**$3.00 total** — $0.70 admission, $2.30 collection, 324 calls. The pre-run
projection was $5 and the cap was $75; neither trigger fired.

## The instrument bug that nearly became a finding

The first admission run reported **claude-opus-5 failing the parseability gate at
20% and claude-sonnet-5 producing no content at all**, and would have been
written up as *frontier models cannot follow this output format*.

It was wrong. `max_tokens=300` was being consumed entirely by reasoning tokens:
`finish_reason=length`, `completion_tokens=300`, empty content. The same call with
`reasoning.enabled=false` answers in **5 tokens**.

This is the third appearance of one failure mode in this lab. Rev 2 hit it with
`qwen3.5` under ollama and fixed it with `think: False`
(`llm-agreement-instrument-note.md`). Rev 4 hit it again through a different
transport and did not recognise it until the payloads were opened.

Two guardrails came out of it:

1. **`finish_reason == "length"` is now a failed call, not a parsed one.** A
   truncated list would otherwise parse into a shorter cell vector and quietly
   lower α — indistinguishable from a coder that marked fewer cells.
2. **Reasoning is disabled explicitly on every call, for every coder**, which is
   also what D2 requires: comparing tiers across different reasoning settings
   would not be comparing like with like.

All data collected on the pre-fix instrument was discarded before any statistic
was computed.

## Guardrails

**A null result is only as broad as its roster.** Rev 3.1 controlled the prompt,
the frame, the instrument shape and the substrate — carefully, and at real cost —
and still produced a headline that a single uncontrolled variable overturns.
Scale was named in its §8 as a limitation and then not treated as urgent. **The
limitation section is where the next experiment is, not where the caveats go to
die.**

**"Cannot follow the format" is almost always the harness.** Three times now a
capable model has looked mute because the caller measured the wrong field or
budgeted the wrong tokens. The cheap check is to open one raw payload before
believing any claim about a model's competence — which is what the
raw-before-parsed rule is for, and why it kept paying.

**Refusing a substitution costs coverage and is still correct.** Dropping Google
leaves the study with two frontier vendors instead of three. Substituting a
different Google model after seeing the others' numbers would have bought that
coverage with exactly the researcher discretion the pre-registration exists to
prevent. The gap is reported instead.
