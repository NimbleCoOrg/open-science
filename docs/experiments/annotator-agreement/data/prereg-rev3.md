---
date: 2026-08-10
status: PRE-REGISTERED, rev 3.1 — not yet run. No label collected, no agreement statistic computed on this design.
revision: "rev 3.1 (2026-08-10, same day, before any collection). Reading
  probe_task_shape.py to implement §2 showed that the free-form prompt this
  document designated as the primary instrument ALREADY CONTAINS A FAILURE FRAME
  ('a trace that is known to have failed') and does supply the cell names. §2.1
  described it wrongly on both counts, and the probe's encouraging free-form
  results are therefore frame-contaminated evidence. §2.1, §2.3, §4.2 and §7 are
  corrected: the admission gate now runs on the PRIMARY instrument rather than on
  a 4-cell proxy, which is both cheaper and a stricter test. No model had been
  called. Rev 3.0 is preserved in git at 8494396."
supersedes: prereg-2026-08-07b-llm-annotator-agreement.md (rev 2), which ran and
  is reported in llm-agreement-null-result.md. Rev 2's A1–A5 are not re-used.
evidence_base: task-shape-is-the-instrument.md (the instrument defect),
  mast-full-dataset-replication.md (the substrate defect),
  reciprocal-frame-recheck.md (what a contaminated frame does and does not damage),
  llm-agreement-null-result.md rev 2 (the results being re-tested)
author: claude, for juniper's approval before execution
---

# Pre-registration rev 3: LLM annotator agreement, with an instrument that is not the finding

## §0 What rev 2 established, and why that forces a new study

Rev 2 ran. Its verdicts stand as post-hoc corrected results. Three of them are
now known to be statements about the measuring instrument rather than about
annotation, which is why this is a new pre-registration and not an amendment.

| Rev 2 | Result | What rev 3 does with it |
|---|---|---|
| A1 pooled α ≥ 0.40 | **0.152 REFUTED** | Re-test. The refutation was obtained on batch-14, which `task-shape-is-the-instrument.md` showed returns its own framing. |
| A2 within − between ≥ 0.15 | **0.534 CONFIRMED** | Re-test with three two-member families. All three within-family pairs in rev 2 were Alibaba. |
| A3 lineage above family | −0.024 AMBIGUOUS | Dropped. Under-powered by construction and not the interesting question. |
| A4 pooled α − α(coder, published) ≥ 0.15 | **0.224 CONFIRMED**, interpretation withdrawn | Re-test on uncontaminated keys only. |
| A5 per-cell IQR > 0.30 | 0.117 REFUTED | Re-test. A near-constant instrument cannot produce per-cell spread, so A5 never got a fair test. |

**The single fact this study is built around:** adding one neutral sentence —
*"this corpus was collected from runs that failed"* — moved all three probed
models from marking 0.00 cells to marking 14.00 cells on every trace, with one
distinct output vector in both states. An instrument that a framing sentence can
saturate is not measuring traces, and every α computed over it is an α about
prompts.

## §1 Substrate, and the correction rev 2's §1 needs

Rev 2's §1 claimed of `MAD_full_dataset.json`: *"1,242 distinct trace payloads,
no duplicated-annotation defect, and one taxonomy throughout."* **Two of those
three claims are false** (`mast-full-dataset-replication.md`): 1,211 distinct
payloads, and ten of fourteen source keys carry replicated annotation sequences
covering 510 records (41%).

Rev 3 uses the same file, because it is still the best available substrate, and
handles the defect by **design rather than by caveat**:

- Source keys are partitioned into **clean** (`AG2_GSM_Plus_Claude`,
  `AG2_MMLU_GPT4o_Mini`, `AG2_Olympiad_GPT4o`, `Magentic_One_GPT4o` — 732
  records) and **affected** (the other ten — 510 records).
- **The frame is drawn from clean keys only.**
- Affected keys appear only in a separate contrast set (§3.3) whose sole purpose
  is to show what including them does.

`reciprocal-frame-recheck.md` is the precedent: a contaminated frame damages
exactly the quantities that read the contaminated column, and nothing else. Here
that column is read by B4 alone, so B4 alone is protected by construction.

**Integrity gate, and the specific failure it must not repeat.** Rev 2 named
`audit_corpus_integrity.py` as its gate; that script globs `*.parquet` plus two
Who&When directories and **never opens `MAD_full_dataset.json`**. Its silence was
recorded as a clean bill of health. Rev 3's gate must therefore assert its own
substrate by name:

1. `verify_mast_full_replication.py` runs and its output **names
   `MAD_full_dataset.json`** and reproduces the 510-record / 52-vector figure.
2. The file's sha256 equals `a182daad…`.
3. The frame builder asserts every drawn `trace.key` is in the clean set, and
   fails loudly otherwise.

If any of the three fails, the study does not start.

## §2 Instrument — the part rev 2 got wrong

**Batch-14 is dropped.** Fourteen simultaneous binary judgments is the shape that
produced two constant coders and an α about prompts.

Two shapes are carried forward, both endorsed by the task-shape probe, and
**both are run**, because "which instrument" is now itself a live question.

### §2.1 Primary — free-form naming

The coder is shown the trace and the **list of 14 cell names** (names only — no
definitions, no checkboxes, no JSON schema) and asked to list every failure mode
it sees evidence for, one per line, by name, or `NONE`. The response is mapped to
the 14-cell vector afterwards by the parser in §2.3.

Rationale: it was the only shape where every probed model produced varying,
trace-grounded output, including `mistral:7b` volunteering
`Disobey task specification (Did not use 'print' function for output)` unprompted.

**Correction, rev 3.1 — the probed version of this prompt is frame-loaded.**
`probe_task_shape.py`'s `FREEFORM` opens *"You are reviewing a multi-agent system
execution trace that is known to have failed."* That is the same class of prior
whose effect on batch-14 is this study's founding observation. The probe's
free-form numbers are therefore **not evidence that free-form is
frame-insensitive** — they were collected under a failure frame, and nobody ran
the neutral counterpart.

Two consequences, both binding:

1. The instrument used here is the **neutral-frame** variant. The words "known to
   have failed" and any equivalent prior are removed; the coder is told it is
   reviewing a trace and asked which failure modes, **if any**, occurred.
2. **Free-form is exactly what the §4.2 admission gate must test**, because its
   frame-sensitivity is unmeasured. Rev 3.0 gated on a 4-cell per-cell proxy,
   which would have admitted coders on one instrument and run them on another.

This was caught by reading the probe source while implementing §2, before any
model was called. It is recorded here rather than fixed silently because the
whole point of rev 3 is that instrument defects are findings.

### §2.2 Confirmatory — per-cell yes/no

One cell per call: the cell's published definition, the trace, and a yes/no
question. Fourteen calls per trace per coder. Run on a **pre-designated 12-trace
subset** of the frame (§3.2), not the whole frame, because it costs 14×.

Rationale: it recovered variance from `llama3.2`, which batch-14 reported as a
constant classifier carrying no information — 4 distinct vectors across 4 traces.

### §2.3 Parser, fixed now

The probe's free-form parser matched a cell name **anywhere** in the response, so
a name inside a parenthetical counted as a mark, inflating `mistral`'s count.
Rev 3's parser:

- considers only lines that are list items (leading `-`, `*`, or `N.`);
- matches a cell if a canonical name or a registered synonym appears in that
  line's **first clause** (before the first `(`, `:` or `—`);
- marks each cell at most once per response;
- the synonym table is written and committed **before collection** and is not
  edited afterwards.

**Every raw response is written to disk before any parsing**, and the parse is a
separate pass over the raw file, so the parser can be re-run without re-calling a
model. This is enforced by `test_raw_output_discipline.py`, not by intention:
rev 2's write-up recorded "keep raw output" as a lesson and the very next probe
shipped discarding it.

## §3 Frame

**Eligibility.** `trajectory` ≤ 8,000 estimated tokens (`len(text) // 4`), the
same estimator rev 2 used. Every coder sees the complete trace; nothing is
truncated. The 28.5%-longest-traces exclusion from rev 2 §3 carries over
unchanged, including its stated bias: **results describe short-to-medium traces
only.**

**Stratification.** Rev 2's signal lived entirely in traces over 3k tokens, and
in its frame "clean and long" was n = 3 — length and key hygiene were
confounded. Clean-key-only drawing removes hygiene as a variable; length and
system are then separable pairwise. Eligible counts, computed from the corpus
before drawing:

| Stratum | Available | Drawn |
|---|---|---|
| S1 AG2, short (< 3k est tokens) | 549 | **8** |
| S2 AG2, long (3k–8k) | 18 | **8** |
| S3 Magentic, long (3k–8k) | 34 | **8** |

**n = 24.** Two contrasts are un-confounded by construction:

- **length, system-matched:** S1 vs S2, both AG2
- **system, length-matched:** S2 vs S3, both long

There is no clean-key Magentic-short cell — clean short traces are 100% AG2 — so
a full 2×2 is not available in this corpus and is not claimed.

### §3.2 The per-cell subset

The 12 traces for §2.2 are the **first 4 drawn from each stratum** under the
frame seed, designated in `frame.json` before any model call.

### §3.3 The contamination contrast set

6 additional traces drawn from affected keys, long stratum, systems as available.
Used **only** to report B4 recomputed with contaminated labels included. It is a
demonstration of the defect's effect, not a hypothesis, and no verdict rests on it.

### §3.4 Mechanics

Sampling happens once, `seed=20260810`, before any coder runs. Drawn ids are
written to `data/llm-agreement/frame-rev3.json` and **committed before the first
model call**. Admission traces (§4) and warm-up traces are drawn from the
eligible pool *after* the frame is removed, so no frame trace is ever seen before
the roster is fixed.

## §4 Coders, and the admission criterion that is the point of this revision

### §4.1 Roster

Rev 2's A2 is confirmed and under-determined: **all three within-family pairs
were Alibaba**, so "family effect" and "Alibaba effect" are not separable. The
fix is a second and third family with two members each.

| Coder | Model | Family | Status |
|---|---|---|---|
| C1 | `gemma3:12b` | Google | local |
| C2 | `gemma3:4b` | Google | **must be pulled** |
| C3 | `qwen3.5:9b` | Alibaba | local |
| C4 | `qwen2.5-coder:32b` | Alibaba | local |
| C5 | `qwen2.5-coder:latest` | Alibaba | local |
| C6 | `mistral:7b` | Mistral | local |
| C7 | `llama3.2:latest` | Meta | local |
| C8 | `llama3.1:8b` | Meta | **must be pulled** |

Three two-member families (Google, Alibaba, Meta) plus one singleton (Mistral).
Identical prompt, temperature 0, identical cell definitions (MAST's published 14,
verbatim). Coders are blind to `mast_annotation`, to each other, and to this
document.

**If either pull is unavailable, B2 is reported as under-determined in exactly
the way rev 2's A2 was, and is not scored as confirmed.** No silent fallback to a
one-family design.

### §4.2 Framing-sensitivity admission — F1 and F2

**This runs before the frame, and its exclusions are a published result, not
housekeeping.**

**Rev 3.1 — the gate runs on the primary instrument.** Rev 3.0 gated on a 4-cell
per-cell proxy; that would have admitted coders on one instrument and run them on
another, and it left free-form's frame-sensitivity — the very thing §2.1 now
shows was never measured — untested. The gate below is both cheaper (160 calls,
not 640) and stricter.

Each candidate coder is run over **10 admission traces** (off-frame, off-warm-up,
drawn with `seed=20260810`) under the **§2.1 free-form instrument**, under two
frames:

- **neutral frame:** the trace, the 14 names, and the question — no prior about
  outcome. This is the instrument the study runs on.
- **failure frame:** the identical prompt plus the single sentence
  *"This corpus was collected from runs that failed, so most traces contain at
  least one failure mode."* — the wording the task-shape probe used, reused
  verbatim so the two studies' frame effects are comparable.

The two prompts differ **only** by that sentence; both are built by one function
with a boolean, so they cannot drift apart.

Let `p_neutral` and `p_failure` be the coder's mean proportion of cells marked
across the 10 traces.

- **F1 — frame sensitivity.** Exclude if `|p_failure − p_neutral| > 0.30`.
- **F2 — constancy.** Exclude if the coder produces **fewer than 3 distinct
  output vectors** across the 10 traces under *either* frame.

**Why 0.30, fixed before collection.** The corpus's typical marked count is
~2.2 of 14 cells, a proportion of ~0.16. A coder whose output moves by more than
0.30 has been shifted by the framing sentence by nearly twice the entire typical
signal. This is a judgement call, it is committed now, and it is not revisited
after the numbers are seen.

**What this would have caught.** Under batch-14 the probe measured
`llama3.2` and `mistral:7b` at 0.00 → 14.00 (shift 1.00) with one distinct vector
in both states, and `qwen2.5-coder:32b` at 0.50 → 14.00 (shift 0.96). All three
fail F1 and two fail F2. Rev 2's five-trace warm-up gate — which tested only
whether output was parseable JSON — passed all of them, and 222 calls were spent
before the problem surfaced.

**Admission is a property of the (model × instrument) pair, not of the model.**
A coder excluded here is excluded for *free-form*, and the write-up says so.

**The per-cell arm carries its own gate.** Because admission is
instrument-specific, coders admitted on free-form are not thereby admitted on
per-cell. Before the §2.2 confirmatory run, admitted coders repeat F1/F2 under
the per-cell shape restricted to 4 fixed cells (`1.1`, `2.2`, `3.1`, `3.3` — one
per MAST category plus a second verification cell) on the same 10 admission
traces. A coder failing there is dropped from the per-cell arm only, and **B3 is
computed on coders admitted under both instruments**, with the count reported.
If fewer than 3 coders clear both, B3 is reported as underpowered rather than
scored.

**The parseability gate carries over** from rev 2 §4: ≥90% parseable on a 5-trace
warm-up, with the failure rate recorded. F1/F2 run on coders that pass it.

**If fewer than 4 coders survive admission, that is the study's headline** and no
agreement statistic is computed. "Two of eight open-weight models can be asked
this question without measuring the question" is a finding, and a better one than
an α over a panel that should not have been admitted.

## §5 Hypotheses, with falsifiers

All α are Krippendorff's α with a cluster bootstrap over traces,
`seed=20260810`, 2,000 iterations. **Any hypothesis whose CI spans its falsifier
is scored AMBIGUOUS, never resolved toward the interesting direction.**

**B1 — admitted coders agree with each other above chance.**
Pooled α across admitted coders, free-form instrument, ≥ 0.40.
*Falsifier:* < 0.40. Below ~0.2 means LLM-as-annotator for this taxonomy is not
viable at open-weight scale **even on an instrument that is not degenerate**,
which is a much stronger claim than rev 2 could make and is worth publishing.

**B2 — agreement is substantially a family effect, and not an Alibaba effect.**
mean within-family α − mean between-family α ≥ 0.15, **and** at least two of the
three two-member families individually show within-family α exceeding the
between-family mean by ≥ 0.15.
*Falsifier:* pooled difference < 0.05, **or** only Alibaba clears the per-family
bar — in which case rev 2's A2 is re-scored as an Alibaba effect and reported as
such.

**B3 — the agreement statistic is not an instrument artifact.**
On the 12-trace subset, |α(free-form) − α(per-cell)| ≤ 0.15.
*Falsifier:* > 0.15. This is the hypothesis rev 2 needed and did not have. If it
fires, **no α from this line of work may be quoted without naming its
instrument**, and that becomes the finding.

**B4 — concordance with the published annotation is much lower than LLM–LLM
agreement, measured on uncontaminated labels.**
pooled LLM–LLM α − mean α(coder, published) ≥ 0.15, computed on the 24 clean-key
frame traces only.
*Falsifier:* within 0.05.
**Interpretation is bounded in advance**, because rev 2's A4 was confirmed and
then had to have its interpretation withdrawn: a near-constant coder scored
against a marking reference produces a negative α mechanically. B4 is therefore
reported alongside each coder's marginal marking rate, and **any coder whose mean
marked proportion is below 0.05 or above 0.60 is excluded from B4's mean** with
that exclusion stated. B4 cannot distinguish "coders wrong" from "published
labels wrong" and will not be reported as if it could.

**B5 — per-cell agreement is uneven.**
IQR of per-cell α across the 14 cells > 0.30, free-form instrument.
*Falsifier:* ≤ 0.30. Rev 2 refuted this at 0.117 on an instrument two of whose
six coders were constant; a constant coder forces per-cell α toward a single
value, so the refutation carried no information.

**Secondary, not hypotheses.** Reported with no threshold and no verdict:
length contrast (S1 vs S2), system contrast (S2 vs S3), B4 recomputed with the
§3.3 contrast set included, and the admission table for all eight candidates.

## §6 Stopping rule

All admitted coders run once over the full frame. **No coder is re-run, dropped,
or added after any agreement statistic is seen.** A coder that fails to return
parseable output on a trace has that trace recorded as missing for it; if any
coder misses > 20%, the study reports as underpowered rather than dropping it.

The `substrate_audit` in `llm_agreement_score.py` runs on the coder output before
any hypothesis is scored — the corrected version, with content-duplication
detection, the per-cell marginal model, and constant-coder warnings that **warn
and do not veto**. Its ten tests must pass, including the non-vacuity one:
sparsity-driven collisions must NOT be flagged as copying.

**Both directions.** Rev 2's gate was invalid because its tests asserted only
that it rejected bad data; nothing asserted it accepted ordinary data. Any gate
added to this study ships with a test in each direction or it does not ship.

**No amendment.** If the instrument is wrong, the study stops and a new
pre-registration is written. Rev 3 is itself the third instance of that rule
being honoured.

## §7 What gets published under each outcome

- **Fewer than 4 coders admitted:** the admission table is the paper. Framing
  sensitivity as an admission criterion for LLM annotator panels, with the exact
  sentence that saturates them.
- **B1 confirmed:** rev 2's null was an instrument artifact, and open-weight
  LLM-as-annotator works for this taxonomy when not asked for 14 simultaneous
  binaries. The instrument comparison is the contribution.
- **B1 refuted with coders admitted:** the null survives a fair instrument. Much
  stronger than rev 2's version, because framing-insensitivity was demonstrated
  first.
- **B2 falsified toward Alibaba-only:** rev 2's headline is corrected in public,
  which is the honest outcome and cheap to have found.
- **B3 fired:** the methodological finding — agreement statistics in this
  literature are instrument-dependent and are being quoted without instruments.
- **Everything ambiguous:** reported as underpowered with the n required.

## §8 What this study explicitly cannot do

- It **cannot** compare LLM coders to human coders. There is no valid human
  reference for this taxonomy in published data — `MAD_human_labelled_dataset.json`
  carries 8 distinct annotation blocks across 19 records, and
  `MAD_full_dataset.json`'s published labels score **α = 0.047, CI [−0.065,
  0.157]** against themselves on the file's own repeats. Any write-up drifting
  toward "more reliable than humans" has left this pre-registration.
- It **cannot** speak to traces over ~8,000 tokens (§3), or to closed models, or
  to model sizes above 32B.
- **B4 is concordance with a published label set, never accuracy.**
- The frame is clean-key-only, which makes it AG2- and Magentic-heavy. **System
  and key hygiene are not separable** in this corpus: no clean key has short
  non-AG2 traces. This bounds every reading of the system contrast, in the same
  way the Alibaba confound bounded rev 2's A2.

## §9 Prerequisites before execution

1. `ollama pull gemma3:4b` and `ollama pull llama3.1:8b` (§4.1). If either
   fails, B2 is reported as under-determined.
2. `MAD_full_dataset.json` present and sha256-verified (§1). `data/` is
   gitignored; the file is re-downloadable from `mcemri/MAST-Data`.
3. The §2.3 synonym table written and committed.
4. `test_raw_output_discipline.py` passing (§2.3).
5. Frame committed before the first model call (§3.4).
