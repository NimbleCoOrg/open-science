---
date: 2026-08-10
study: prereg-2026-08-10-llm-annotator-agreement-rev3.md (rev 3.1)
status: COMPLETE — all five hypotheses scored. 672/672 per-cell calls collected.
verifier: pipeline/rev3_score.py
data: data/llm-agreement/results-rev3.json, data/llm-agreement/raw/frame-rev3-C*.jsonl
supersedes_in_part: llm-agreement-null-result.md (rev 2) — A2's confirmation does not replicate
---

# The null was real, and the family effect was not

> **Corrected 2026-08-12 by `rev4-results.md`. Read this document's scope
> narrowly.** Every coder here was 2–12B. Running the identical frame, prompt and
> parser against larger models gives **α 0.360 at 70B and 0.598 at frontier**,
> against 0.173 here — D2 confirmed at 0.425. **The null below is about model
> scale, not about the taxonomy.** Nothing in this document is retracted; the
> sentence it invites — *this taxonomy cannot be annotated reliably* — is not
> supported and is refuted by rev 4.

Rev 2 concluded two things: LLM coders do not agree with each other (A1 refuted,
α = 0.152), and what agreement exists is a family effect (A2 confirmed,
0.534). Both were computed on batch-14, an instrument that
`task-shape-is-the-instrument.md` then showed returns its own framing.

Rev 3.1 re-tested both on an instrument whose frame-insensitivity was
demonstrated *before* any trace was coded (`rev3-admission-result.md`).

**One survives and one does not.**

| | statistic | 95% CI | verdict | rev 2's counterpart |
|---|---|---|---|---|
| **B1** pooled α ≥ 0.40 | **0.173** | [0.127, 0.207] | **REFUTED** | A1 refuted, 0.152 |
| **B2** within − between ≥ 0.15 | **0.127** | [0.035, 0.208] | **AMBIGUOUS** | **A2 confirmed, 0.534** |
| **B3** \|α(free-form) − α(per-cell)\| ≤ 0.15 | **0.103** | | **CONFIRMED** | none — rev 2 could not ask |
| **B4** pooled α − α(coder, published) ≥ 0.15 | **0.150** | [0.082, 0.222] | **AMBIGUOUS** | A4 confirmed, 0.224 |
| **B5** per-cell IQR > 0.30 | **0.076** | [0.047, 0.170] | **REFUTED** | A5 refuted, 0.117 |

24 clean-key traces, six admitted coders, 180 responses, cluster bootstrap over
traces, `seed=20260810`, 2,000 iterations. Substrate audit passes with 24
distinct annotation blocks over 24 traces, no warnings, no failures. No coder
missed more than 20% of traces; none was excluded from B4 by marking rate.

## B1 — the null is a property of the task, not the prompt

**α = 0.173, CI [0.127, 0.207].** Rev 2's 0.152 sits inside that interval.

This is the outcome §7 pre-designated as the strong one. Rev 2 could not
distinguish "these models cannot annotate this taxonomy" from "batch-14 is a
degenerate instrument", because the same data supported both. Rev 3.1 separates
them: every coder here was shown to move with the trace and hold still under a
framing sentence before it coded anything, and agreement is **unchanged**.

Changing the instrument from fourteen simultaneous binaries to free-form naming
moved pooled α by 0.021.

> Open-weight models at this scale do not agree on MAST's taxonomy, and the
> earlier null was not an artifact of how they were asked.

**What this does not say.** It does not say the models cannot read the traces —
`rev3-admission-result.md` shows they can, and `mistral:7b` volunteers
trace-grounded evidence unprompted. It says they do not converge on the *same*
labels. Those are different failures, and only the second one is measured here.

## B2 — rev 2's headline does not replicate

**0.127, CI [0.035, 0.208], AMBIGUOUS**, against rev 2's **0.534 CONFIRMED**.

Per-family, against a between-family mean of **0.121**:

| family | members admitted | within-family pairs | within-family α | clears bar? |
|---|---|---|---|---|
| Meta | `llama3.2`, `llama3.1:8b` | 1 | **0.282** | yes |
| Google | `gemma3:12b`, `gemma3:4b` | 1 | 0.215 | no |
| Alibaba | `qwen3.5:9b` only | **0** | — | — |
| Mistral | `mistral:7b` only | 0 | — | — |

B2's pre-registered falsifier requires **at least two** families to clear the bar
individually. One does.

**The mechanism rev 2 suspected but could not test.** Rev 2's A2 rested on three
Alibaba pairs, two of which were `qwen2.5-coder` at two sizes. Its write-up
flagged this — *"'family effect' and 'Alibaba effect' are not separable in this
design"* — and proposed a second two-member family as the fix. What actually
happened is sharper: **both `qwen2.5-coder` models failed admission for
constancy**, one marking 0.000 cells on every trace under both frames. Two
near-constant coders agree with each other on absence at whatever rate absence is
common, and α does not distinguish that from agreement.

Rev 2's within-family α of 0.515 was, in substantial part, two constant
classifiers agreeing about nothing.

**The honest reading is "unresolved", not "refuted".** The CI's lower bound is
0.035, so a positive family effect is not excluded — it spans the falsifier at
0.05 and does not reach the bar at 0.15. What died is the *confirmation*, not the
hypothesis.

### The power cost of the quality gate

This is the study's sharpest self-inflicted limitation, and it is a design
lesson rather than a mistake.

The roster was built with **three** two-member families precisely to break rev
2's confound. Admission then excluded both Alibaba coders, leaving **2
within-family pairs against 13 between-family pairs**. B2 is therefore
under-powered by the gate that made it trustworthy: the same rule that removed
the artifact removed a third of the design's leverage.

**A gate that excludes coders changes the estimand, not only the sample.** A
family that loses both members stops being a family in the analysis. Any future
version must over-recruit per family on the assumption that admission will take
some — three members per family to guarantee one surviving pair, not two.

## B3 — CONFIRMED: the null is not an instrument artifact

**Gap 0.103, under the 0.15 bar.** Computed over the four coders admitted under
*both* instruments (C1, C2, C6, C7) on the 12-trace subset designated before
collection.

| instrument | α |
|---|---|
| free-form naming | **0.149** |
| per-cell yes/no | **0.046** |

Two instruments with almost nothing in common — one asks for a list of names in a
single pass, the other asks fourteen separate yes/no questions and re-sends the
trace each time — land within 0.10 of each other, both near zero.

**This is the hypothesis rev 2 needed and could not ask.** Rev 2's null was
computed on a single instrument that later turned out to be degenerate, so
"models cannot do this task" and "this prompt is broken" were indistinguishable.
B1 separated those by demonstrating frame-insensitivity first. B3 closes the
remaining gap from the other side: change the *shape* of the question entirely
and the answer does not move.

Had B3 fired, the finding would have been methodological — that agreement
statistics in this literature are instrument-dependent and are being quoted
without instruments. It did not fire. **Agreement on MAST's taxonomy is low
across instrument shape**, and an α from this line of work can be quoted without
naming its instrument.

The per-cell α is the lower of the two, which is worth noting rather than
smoothing over: the more expensive, more deliberate instrument produced *less*
agreement, not more.

### The per-cell admission gate — 4 of 6, and it disagrees with free-form

### The per-cell admission gate — 4 of 6, and it disagrees with free-form

Run in full (480 calls) before any collection:

| coder | frame shift | min vectors | |
|---|---|---|---|
| C1 `gemma3:12b` | 0.075 | 3 | admitted |
| C2 `gemma3:4b` | 0.125 | 7 | admitted |
| C3 `qwen3.5:9b` | 0.025 | **2** | **excluded (F2)** |
| C6 `mistral:7b` | 0.275 | 4 | admitted |
| C7 `llama3.2` | 0.000 | 4 | admitted |
| C8 `llama3.1:8b` | 0.025 | **1** | **excluded (F2)** |

**Admission is instrument-specific, and this is the evidence.** Both exclusions
passed the free-form gate comfortably; `llama3.1:8b` collapses to a single
distinct vector under per-cell questioning. Again no coder failed F1 — the
largest frame shift is 0.275, under the 0.30 bar.

The roster therefore differs by instrument: six coders on free-form, four on
per-cell. Rev 3.1's §4.2 requirement that B3 be computed only over coders
admitted under **both** is doing real work — a naive B3 would have compared six
coders' free-form α against four coders' per-cell α and called the difference an
instrument effect.

### What it cost to collect

**672 of 672 calls, on the fourth attempt.** Three earlier runs ended with the
model endpoint unreachable mid-sweep. The circuit breaker halted the second
rather than filling the arm with holes; the resume key counts successful calls
only, so each retry filled exactly the gaps.

**The endpoint was never down.** The first diagnosis was that the local model
server had crashed twice and the host was too loaded for unattended sweeps.
Both claims were wrong: the server had 20+ days of continuous uptime and was
never restarted. What died was the network forward in front of it.
`RemoteDisconnected` followed by `Connection refused` on a *localhost* port is a
dead forward, not a dead server — the second error means nothing is listening on
*this* machine, which says nothing at all about the remote. Fixed by removing the
flapping hop from the path.

*(Lab network topology elided in the published copy.)*

**The cost was underestimated at design time, and the error is instructive.**
Per-cell was specified as "14× per trace", counted in calls. It is also 14× in
*prompt processing*: every one of the fourteen calls re-sends the entire trace,
so a 6,000-token trace is processed fourteen times to produce one 14-cell
vector. Measured median **36.5 s per call** (mean 40.5, max 92.4) against
free-form's ~5 s on the same traces.

Free-form gets a 14-cell vector out of one pass over the trace. Per-cell pays
fourteen passes for the same vector. **That is a ~14× cost for an α that comes
out 0.10 lower**, which — now that B3 has been answered — is the practical
argument for free-form as the default instrument in any future round.

## B4 — concordance, with its interpretation bounded in advance

**0.150, CI [0.082, 0.222], AMBIGUOUS.** No coder was excluded by the marginal
gate; marking rates ran 0.051 (`qwen3.5`) to 0.437 (`llama3.2`), all inside
[0.05, 0.60].

Rev 2's A4 was confirmed at 0.224 and then had its **interpretation withdrawn**,
because a near-constant coder scored against a marking reference produces a
negative α mechanically. Rev 3.1 pre-registered the marginal-rate exclusion to
prevent exactly that, and with genuinely non-constant coders the effect is
smaller and no longer resolves.

**This remains concordance with a published label set, never accuracy.** That
label set scores **α = 0.047, CI [−0.065, 0.157]** against itself on the file's
own repeats.

### The contamination contrast set (§3.3, demonstration only)

Folding in the 6 affected-key traces moves B4 from **0.1496 to 0.1481**.

Nearly nothing — and worth stating plainly, because the clean-key-only frame was
this study's most expensive design decision (it is why the frame is AG2- and
Magentic-heavy, and why no clean-key short non-AG2 cell exists). On *this*
statistic, at *this* n, the contamination the frame was built to avoid would have
changed the third decimal place.

That is not a licence to reuse the contaminated keys. It is a bound: the copied
annotations do not perturb a concordance figure computed over six coders whose
own agreement is near zero. A study with coders that agreed would have more to
lose.

## B5 — agreement is uniformly near zero, not unevenly distributed

**IQR 0.076, CI [0.047, 0.170], REFUTED.** Per-cell α spans −0.119 to 0.085:

| | α | | α | | α |
|---|---|---|---|---|---|
| 1.1 | −0.046 | 2.1 | 0.076 | 3.1 | 0.031 |
| 1.2 | −0.112 | 2.2 | 0.033 | 3.2 | −0.035 |
| 1.3 | **0.085** | 2.3 | 0.057 | 3.3 | 0.019 |
| 1.4 | **−0.119** | 2.4 | −0.020 | | |
| 1.5 | −0.020 | 2.5 | 0.001 | | |
| | | 2.6 | 0.000 | | |

Rev 2 refuted A5 too, but on an instrument with two constant coders, which forces
per-cell α toward a single value and made the refutation uninformative. Here the
coders vary and the answer holds: **there is no cell on which these models agree.**
The highest is step repetition at 0.085 — a mechanically checkable property, and
still indistinguishable from chance.

This matters more than its verdict suggests. A finding of "uneven" would have
identified a subset of the taxonomy that LLM panels could be trusted with. There
is no such subset.

## Secondary contrasts (no thresholds, no verdicts)

| contrast | α |
|---|---|
| S1 AG2 short (< 3k tokens) | 0.186 |
| S2 AG2 long (3k–8k) | 0.162 |
| S3 Magentic long (3k–8k) | 0.074 |

**Length, system-matched:** 0.186 vs 0.162 — no length effect. This is worth
recording because rev 2 reported that *"all of A2's signal came from traces over
3k tokens"*, and that motivated §3's stratification. On a clean instrument the
length effect is absent. Another rev 2 observation that was probably an
instrument artifact.

**System, length-matched:** AG2 0.162 vs Magentic 0.074. Directionally a real
difference, on 8 traces per cell, and reported without a verdict as
pre-registered.

## What this study cannot say

Unchanged from §8, plus what the results add:

- **No comparison to human coders.** No valid human reference exists in
  published data.
- **Short-to-medium traces only** (≤ 8,000 estimated tokens), and the admission
  traces were shorter still (734–2,215), so frame-insensitivity is demonstrated
  only in that band.
- **n = 24**, six coders, two within-family pairs. B2 in particular is
  under-powered, and by the study's own gate.
- **Clean-key-only means AG2- and Magentic-heavy.** System and key hygiene are
  not separable in this corpus.
- **B4 is concordance, never accuracy.**

## Guardrails

**An instrument check can confirm a null instead of overturning it, and that is
the more useful outcome.** The expectation going in was that rev 2's null was an
artifact — the task-shape probe had shown the instrument was degenerate, and
degenerate instruments usually manufacture nulls. It did not. Fixing the
instrument moved pooled α by 0.021 and left the verdict standing. The
pre-registration's value was in making that a *result* rather than a
disappointment: §7 named "B1 refuted with coders admitted" as publishable before
anyone knew which way it would go.

**The artifact was in the finding nobody doubted.** Effort went into re-testing
A1, the null, because it was the counter-intuitive claim. A2 — the confirmed,
mechanistic-sounding "agreement is family convention" — is the one that
evaporated. A confirmation resting on two constant classifiers looks exactly like
a confirmation resting on a real effect, until something independent removes the
classifiers.

**Quality gates cost statistical power, and the cost lands unevenly.** Admission
removed both members of one family and neither member of two others. Nobody
budgeted for that, and B2 paid for it. Over-recruit per cell when a gate can
delete a whole cell.

**A resumable collector that treats a failed call as done bakes the failure in.**
The first per-cell run lost its SSH tunnel and returned connection-refused on 517
of 672 calls in about a second each — then printed "collection done" and exited
0. The transport failure was bad luck. The defect was that the resume key was
written for every call regardless of outcome, so the retry would have skipped
exactly the calls that needed retrying and reported a complete arm. Failed
responses parse to `None` and are dropped as missing downstream, so B3 would have
been computed on whatever survived, with no signal that anything was wrong. The
same bug was sitting in the admission collector.

**A dead endpoint is fast, and speed reads as progress.** Hundreds of failing
calls completed in ~0.0 s each while the run looked like it was flying. Any
unattended collector needs a circuit breaker on consecutive failures; without
one, the fastest-looking run is the one collecting nothing.

**`Connection refused` on a forwarded port accuses the wrong machine.** The
error arrives from *localhost* — it means nothing is listening on this end of a
dead tunnel, and carries no information about the remote service. It was read
here as "the model server crashed on the remote host", which became "that host is
unstable under load, don't trust it", which was reported to the person who owns
the machine.
The server had 20+ days of uptime throughout. **One `ps -o etime= -p <pid>` on
the remote would have refuted the whole story before it was told**, and it cost
one command to check after the fact.
