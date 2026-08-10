# Every method and every caveat, in full

Companion document to **The Failure Atlas**. The page states findings in plain
words. This document holds the machinery behind them: what each detector looks
for, how often each one was right, how incidents were judged, how our incidents
were cross-walked against the field's standard taxonomy, which predictions we
registered in advance and what happened to them, everything we know is wrong
with the study, and how to run the same pipeline over your own logs.

It is written for the reader who clicked through. It is technical, but it
explains its terms. Nothing here is internal shorthand.

---

## 0. How to read this, and which numbers are which

**Data version.** Every figure below comes from the data package
`data/dashboard-data.json` built on 2026-08-07 from an ingest that finished
2026-08-06T15:17Z. The corpus grows nightly, so session, event and incident
counts move between builds. Experiment cohorts were frozen at the date each
experiment ran and are smaller than the current corpus; where that matters it is
said in the text.

**Two different severity scales, do not mix them.**

- *Incident severity* is a machine-computed number between 0 and 1: the peak
  detector score, plus 0.12 for each additional distinct detector in the
  cluster, plus 0.02 per signal up to ten, capped at 1. It is a crowding
  measure, not a judgment.
  (`pipeline/incidents.py`, function `severity`.)
- *Adjudicated severity* is a 1 to 5 rating assigned by a language-model judge
  reading the full transcript window. Mean adjudicated severity per confirmed
  mode ranges from 1.0 to 3.2 in this corpus.
  (`pipeline/adjudication_ingest.py`, field `severity_1_5`.)

**Citations.** Paths in `pipeline/` are shipped alongside the page and are the
code that produced the numbers. Paths in `experiments/` and `data/` are lab
records that stay on the operator's machine; they are cited so that each claim
has a named source, and so that a future version of this study can be checked
against them. No transcript text leaves the machine, by design (see §8).

**A standing warning about this study's own numbers.** On 2026-08-07 the data
generator was found to be hand-typing values. Two figures that had reached the
page existed in no source record at all. The fix and the full disclosure are in
§9. Read that section before trusting any number here, including the ones we
now believe.

---

## 1. The corpus

Two ecosystems, one pipeline, one schema.

| | Coding agents | Assistant fleet |
|---|---:|---:|
| Top-level sessions | 631 | 2,150 |
| Transcript files | 4,308 | 2,734 |
| of which agent-spawned sidechains | 3,677 | 584 |
| Logged events | 599,362 | 110,481 |

Totals: **2,781 sessions, 7,042 transcript files, 709,843 events, 4,662
incidents**, spanning **2026-01 to 2026-08**.
(Source: `data/dashboard-data.json` keys `corpus.*`, `totals.*`; derived by
`pipeline/analyze.py` from the `sessions` table.)

**Coding agents** are one operator's Claude Code sessions across three config
roots. This is a single-operator corpus, and that is its largest limitation
(§7).

**Assistant fleet** is a fleet of chat-assistant bots that many different people
talk to across four chat platforms. It is genuine multi-human, multi-agent
traffic, not one person. It is the reason the study can say anything at all
about how detection behaves outside one workflow.
(`corpus.note`, `corpus._n_chat_platforms` = 4.)

### What counts as a "session" and what counts as an "event"

A **session** here means a top-level run that a human started. 85% of Claude
Code transcript files are agent-spawned sidechains, not sessions. An earlier
draft of this study reported "4,059 sessions" by counting files, overstating
real sessions by roughly 6.5 times. Per-event rates were unaffected. The
correction is logged rather than quietly edited, because it is an instance of
the exact failure the study catalogs: asserting a number without checking what
it means. (`FINDINGS.md`, correction note.)

An **event** is one content block at parse time: a message, a tool call, or a
tool result. The published event total, 709,843, is the sum of per-session event
counts recorded during extraction. The stored `events` table holds 696,686 rows,
because it is keyed on (session, transcript line) and a single transcript line
carrying several content blocks collapses to one stored row. The gap is 13,157
rows, about 1.9% of events. Two consequences, both real:

1. Rates published "per 10k events" use the 709,843 denominator.
2. Detectors see the stored rows, so where one transcript line carried both a
   tool call and its result, only the last block on that line is visible to
   them. This is an undisclosed-until-now limitation of the extractor, found
   while writing this document.

(Verified read-only against `data/atlas.db`: `SELECT COUNT(*) FROM events`
returns 696,686; `SELECT SUM(n_events) FROM sessions` returns 709,843. Schema:
`pipeline/extract.py`, `PRIMARY KEY(session_key, line_no)`.)

---

## 2. The pipeline

Six stages. Stages 1 to 4 are mechanical and reproducible. Stage 5 uses a
language model. Stage 6 is optional and produces countermeasures rather than
findings.

**1. extract** (`pipeline/extract.py`) parses every session transcript under
your Claude config roots into a local SQLite store. Full text is kept only where
detection needs it: user and assistant text, and error results. Everything else
is recoverable through a `(source_file, line_no)` pointer. This is deliberate:
the shareable output must never contain transcript text, so counts are computed
from a store that structurally separates text from counts.
(`DECISIONS.md` D2.)

**1b. thinking traces** (`pipeline/thinking_extract.py`) preserves reasoning
blocks into a separate table. That table is **local-only, permanently**. It
never feeds `analysis.json`, the dashboard package, or any pooled artifact, and
nothing derived from it appears on the page or in this document.
(`DECISIONS.md` D9; `README.md` privacy model.)

**2. detect** (`pipeline/detectors.py`) runs 13 high-recall detectors plus 2
unvalidated candidate detectors over the event store, writing one row per
(event, detector) hit with a score in [0,1] and a JSON evidence payload.
Detectors are deliberately over-sensitive. Nothing they emit is treated as
ground truth. Full specifications in §3.

**3. incidents** (`pipeline/incidents.py`) clusters signals. An incident is a
maximal run of signals inside one session separated by no more than **25 events
and 600 seconds**. Each incident carries the full multiset of detectors that
fired, a severity, a source pointer, and a **primary mode** chosen by a fixed
precedence order that puts semantic detectors above mechanical ones, because a
human calling out a false claim *is* the phenomenon whereas a tool error is only
a candidate symptom. The precedence order is:

> honesty_challenge, frustration_lex, error_loop, subagent_failure,
> model_escalation, stuck_repetition, user_interrupt, permission_friction,
> api_error, abandonment, tool_error, interagent_challenge, self_correction,
> then the two unvalidated candidates last.

Because the full detector multiset is stored on every incident, any alternative
precedence can be recomputed without re-extracting anything.
(`DECISIONS.md` D5.)

**4. analyze** (`pipeline/analyze.py`) produces `analysis.json`: aggregate
rates, co-occurrence counts, position-in-session distributions, outcome
distributions, model-tier splits. No transcript text. This is the file designed
to be poolable across installations.

**5. adjudicate** (`pipeline/context_window.py`, `pipeline/adjudication_ingest.py`)
draws a stratified sample per detector, renders the full transcript window around
each incident from the original file, and has a language model rule on what
really happened. This is where detector precision comes from. Full protocol in
§4.

**6. augment** turns confirmed, avoidable failure clusters into conditional
hooks and small on-demand memory files rather than standing instructions.
Nothing auto-installs, and a baseline snapshot is taken first so that every
countermeasure names the metric that has to drop. Not a finding-producing stage;
listed for completeness.

---

## 3. The thirteen detectors

Each detector is a heuristic candidate generator. The interesting result is not
what they found but **how often each was right**, which is measured in §3.2 and
is itself one of the study's findings.

### 3.1 What each one looks for

| Detector | Fires on | Known confound |
|---|---|---|
| `tool_error` | Any tool result the harness marked as an error, sorted into 10 categories by regex (exit_nonzero, not_found, edit_mismatch, timeout, hook_block, network, user_rejected, permission_denied, interrupt, other) | Test-driven-development red phases; searches that legitimately find nothing |
| `error_loop` | 3 or more tool errors inside a sliding window of 12 events; re-emits at run lengths 3, 5 and 8 | Long, legitimate debugging runs |
| `stuck_repetition` | The same (tool, exact input) called 3 or more times with mean spacing under 60 seconds. Task-list and monitor tools excluded as polling | Any genuine retry-until-ready pattern that is faster than 60 seconds |
| `user_interrupt` | A human turn containing the harness's interrupt marker | Benign redirection; the user changing their mind is not a failure |
| `frustration_lex` | Human turns scored over 20 strong markers, 14 medium markers, and a shouting test (over 60% capitals across at least 12 letters). Threshold 0.15 | Casual profanity; quoting someone else's anger |
| `honesty_challenge` | Human turns matching 11 accusatory patterns ("you didn't actually", "made that up", "doesn't exist", "you claimed X but") | Genuine questions. Generic verification requests ("are you sure", "show me") were **removed after round 1** because they measured 25% precision |
| `self_correction` | Assistant turns matching 14 admission patterns ("I was wrong", "my mistake", "I misread", "correction:") | Politeness with no underlying error. This confound was never fully solved |
| `api_error` | The transcript's own recorded API or harness fault | Infrastructure noise, essentially never the agent's fault |
| `permission_friction` | A tool error whose text matches one of 7 rejection or guardrail patterns (user rejected, permission denied, hook block, protected branch, consent needed) | Guardrails **working correctly** are indistinguishable from guardrails misfiring, at the log level |
| `model_escalation` | A low-to-high model-tier jump after a failure signal, in-session; plus a cross-session variant (same working directory, next session within 2 hours, prior session had failure signals) | Routine model switching. Runtime auto-swaps measured 17% precision in round 1 and were excluded |
| `subagent_failure` | A sidechain transcript whose last substantive event is an error | Expected negative results from a subagent doing its job |
| `abandonment` | A non-sidechain session with more than 10 content events whose final content event is an error or a frustrated human turn, with no substantive assistant close-out (200 characters or more) after it | The user going to dinner is indistinguishable from the user giving up |
| `interagent_challenge` | Honesty-challenge markers on a **sidechain** "user" turn, which is an orchestrator prompt rather than a human | Adversarial-verification prompts are protocol language, not failure |

(All specifications read from `pipeline/detectors.py`. Lexicon sizes counted
from the module's own lists.)

Two further detectors run but are **unvalidated**: `bare_done_claim` (a
completion claim with no verification language in the same turn, when the turn
followed real tool work) and `unqualified_metric_claim` (a metric asserted with
an achievement verb and no co-located sample size, split, or interval). They
have no adjudicated precision, they rank last in incident precedence so they can
never become an incident's primary mode, and they are reported separately so
they inform without contaminating measured results. `bare_done_claim` is
nonetheless the second-largest signal generator in the corpus, at 2,676 firings.

**One detector was reclassified.** `interagent_challenge` measured 8.3%
precision: orchestrators telling subagents to "adversarially verify" is protocol
language, not distress. It is kept in the pipeline at second-to-last precedence,
so it fires 275 signals but is the primary mode of only 4 incidents. Earlier
write-ups described it as "excluded from incidents"; that is not what the code
does, and the current numbers are the ones above.
(Verified read-only against `data/atlas.db`.)

### 3.2 How often each one was right

**Precision** here means: given that the detector fired, how often was the
underlying phenomenon real? It is estimated on a stratified sample of 12
incidents per detector, judged against the full transcript window (§4). The
interval is a **Wilson 95% interval**, which is a range that would contain the
true rate 95% of the time under repeated sampling; with only 12 judgments per
detector these intervals are wide, and that width is the honest picture.

| Detector | Precision | 95% interval | Judged | Round | Share where the agent was at fault | Mean severity (1 to 5) |
|---|---:|---|---:|---:|---:|---:|
| `api_error` | 1.00 | 0.76 to 1.00 | 12 | 1 | 0.00 | 2.08 |
| `subagent_failure` | 1.00 | 0.76 to 1.00 | 12 | 2 | 0.08 | 2.08 |
| `user_interrupt` | 1.00 | 0.76 to 1.00 | 12 | 1 | 0.42 | 1.83 |
| `tool_error` | 0.83 | 0.55 to 0.95 | 12 | 1 | 0.60 | 1.80 |
| `permission_friction` | 0.83 | 0.55 to 0.95 | 12 | 1 | 0.20 | 2.10 |
| `frustration_lex` | 0.58 | 0.32 to 0.81 | 12 | 1 | 0.86 | 2.86 |
| `self_correction` | 0.50 | 0.25 to 0.75 | 12 | 2 | 1.00 | 2.50 |
| `stuck_repetition` | 0.50 | 0.25 to 0.75 | 12 | 1 | 0.83 | 2.00 |
| `error_loop` | 0.42 | 0.19 to 0.68 | 12 | 1 | 1.00 | 2.20 |
| `model_escalation` | 0.42 | 0.19 to 0.68 | 12 | 2 | 1.00 | 2.40 |
| `abandonment` | 0.33 | 0.14 to 0.61 | 12 | 2 | 0.25 | 2.25 |
| `honesty_challenge` | 0.25 | 0.09 to 0.53 | 12 | 2 | 1.00 | 2.67 |
| `interagent_challenge` | 0.08 | 0.02 to 0.35 | 12 | 1 | 1.00 | 3.00 |

(Source: `data/precision.json`, computed by `pipeline/adjudication_ingest.py`;
mirrored into `data/dashboard-data.json` key `precision`.)

**Read the shape, not the decimals.** Every row rests on twelve judgments. A
single reclassification moves a precision by 0.083. Two detectors sharing a
precision value share it because they had the same count of valid cases out of
twelve, not because they are equally good.

The pattern across rows is the finding: **mechanical signals are nearly
perfectly detectable from logs, and the semantic failures anyone actually cares
about are exactly the ones where lexical detection decays.** Interrupts, API
faults and tool errors are at or near 1.00. Caught dishonesty is at 0.25. The
detectors that are almost always right catch cheap things; the ones that catch
things with real weight are mostly wrong.

Two rows need their story attached, because the number alone misleads:

- **`subagent_failure` at 1.00** looks like a triumph of detection. It is not a
  finding about agents. Ten of its twelve valid cases were the human
  mass-interrupting a swarm of verifier subagents, not subagents failing.
  (`FINDINGS.md` instrument table.)
- **`honesty_challenge` at 0.25** was stable across both rounds, and its three
  true hits all share one mechanism: the agent asserted something it had not
  verified.

### 3.3 What the detectors surfaced

Signals fired (raw detector hits) against incidents where that detector is the
primary mode:

| Detector | Signals | Incidents (primary) | per 10k events | Mean incident severity (0 to 1) |
|---|---:|---:|---:|---:|
| `tool_error` | 7,999 | 1,165 | 16.41 | 0.361 |
| `bare_done_claim` (unvalidated) | 2,676 | n/a | n/a | n/a |
| `self_correction` | 1,195 | 530 | 7.47 | 0.457 |
| `frustration_lex` | 1,135 | 902 | 12.71 | 0.456 |
| `permission_friction` | 758 | 276 | 3.89 | 0.713 |
| `error_loop` | 756 | 491 | 6.92 | 0.937 |
| `api_error` | 654 | 541 | 7.62 | 0.360 |
| `user_interrupt` | 401 | 256 | 3.61 | 0.682 |
| `stuck_repetition` | 309 | 180 | 2.54 | 0.767 |
| `interagent_challenge` | 275 | 4 | 0.06 | 0.595 |
| `abandonment` | 186 | 139 | 1.96 | 0.967 |
| `honesty_challenge` | 155 | 135 | 1.90 | 0.678 |
| `unqualified_metric_claim` (unvalidated) | 81 | n/a | n/a | n/a |
| `subagent_failure` | 33 | 26 | 0.37 | 0.917 |
| `model_escalation` | 19 | 17 | 0.24 | 0.672 |

(Signals: read-only query against `data/atlas.db`. Incidents, rates and
severities: `data/dashboard-data.json` key `incidents_by_mode`. Signal counts
exceed incident counts because clustering merges runs, and because a signal can
land in an incident whose primary mode is a different detector.)

What tool errors actually are, by category:

| Category | Count |
|---|---:|
| exit_nonzero | 2,503 |
| other | 2,105 |
| not_found | 1,530 |
| edit_mismatch | 452 |
| timeout | 400 |
| hook_block | 376 |
| network | 238 |
| user_rejected | 205 |
| permission_denied | 184 |
| interrupt | 6 |

(`data/dashboard-data.json` key `error_categories`.)

---

## 4. How incidents were adjudicated

### 4.1 The sample

For each of the 13 detector modes, 12 incidents were drawn by a deterministic
pseudo-random ordering over the incident identifier, so the sample is
reproducible and is spread across severities rather than picking the worst
cases. (`pipeline/context_window.py`, `--list-sample`.)

That is **12 judgments per detector, 13 detectors**. It is a small sample and it
sets the width of every interval in §3.2.

### 4.2 What the judge saw

For each sampled incident, `pipeline/context_window.py` re-reads the **original
transcript file**, not the truncated store, and renders a plain-text window
around the incident with 15 events of padding on each side. Roles, timestamps,
tool names and tool inputs are shown; the lines where signals fired are marked
with `>>>`. Thinking blocks are shown only as a character count. Long bodies are
truncated at 2,400 characters with the omission stated inline.

The judge was a language model reading that window. It is from the same model
family as many of the agents being judged, which is a structural bias the study
has never removed. It is listed in §7.

### 4.3 What "valid" means

For each incident the judge returned a fixed record:

| Field | Meaning |
|---|---|
| `valid` | Is the phenomenon the detector claims to have found actually present in this window? This is the field precision is computed from. |
| `confirmed_mode` | What actually went wrong, from a fixed list of outcome modes, independent of which detector fired. |
| `agent_at_fault` | Was the agent responsible, as opposed to infrastructure, the human, or the environment? |
| `root_cause`, `prevention`, `notes` | Free text. |
| `avoidable_by` | Which intervention would have prevented it. |
| `severity_1_5` | Impact rating. |

A firing is **valid** when the phenomenon is real, which is not the same as
"the agent failed" and not the same as "this mattered". A correctly detected
permission block that was the guardrail working as designed is valid and is not
an agent failure. Both facts are recorded, which is why `precision` and
`agent_fault_share` are separate columns in §3.2 and frequently disagree
(`api_error`: precision 1.00, agent fault 0.00).

### 4.4 The two rounds

**Round 1** judged all 13 modes, 12 each, for 156 labels. Round 1 findings then
fed back into the detectors: the generic verification patterns were cut from
`honesty_challenge`, the runtime model-swap noise was cut from
`model_escalation`, `abandonment` was rewritten to require the final content
event to be a failure, and `subagent_failure` was rewritten to require the error
to be at the end of the sidechain.

**Round 2** re-judged the five modes those fixes touched, 12 each, for 60 more
labels. Total 216 label events. The published precision for each mode is from
its most recent round, tagged in the table above.

The round-2 rerun of `subagent_failure` and `honesty_challenge` took four
attempts across three execution paths, because the judging infrastructure kept
hitting overload errors. The study's own second-ranked failure cluster occurred
while it was measuring that cluster. (`FINDINGS.md` known limits.)

### 4.5 The identifier bug, and why only 60 labels back the eval suite

Incident identifiers were originally positional, assigned by iteration order.
Re-running the pipeline renumbered incidents, so adjudication labels keyed by
identifier silently drifted onto the **wrong incidents**. One label recorded
against a Claude "both PRs merged" case ended up pointing at an unrelated
assistant-fleet abandonment.

The fix was content-addressed identifiers:
`inc-` + `sha1(session_key | first_signal_line | last_signal_line)`, truncated,
which is stable across re-runs and corpus growth. Recovery
(`pipeline/remap_adjudications.py`) reconstructed the old identifier to
(session, line-range) map from the adjudication transcripts, which had printed
the context windows, and re-pointed labels by session and line overlap.

Honest outcome:

- **185 labels** survive in the store, of which 89 are valid firings and 96 are
  confirmed false positives.
- **60** of those still resolve to an incident in the current incident set.
  Those 60 are the eval suite.
- The remaining 125 were labeled against earlier incident definitions that the
  round-2 detector fixes changed: 76 were false positives the improved detectors
  correctly no longer emit, and 49 were real failures whose incident boundaries
  moved.
- `data/precision.json` is unaffected, because precision is computed per round
  at label time, before any re-run.

60 correctly aligned labels beat 177 misaligned ones. Re-adjudicating against
current incidents would grow the suite and has not been done.
(`DECISIONS.md` D9; counts verified read-only against `data/atlas.db`:
`SELECT COUNT(*) FROM adjudications` returns 185; the join against `incidents`
returns 60.)

### 4.6 What the judge concluded

Of the 89 valid firings, the confirmed modes were:

| Confirmed mode | n | Mean severity | Agent at fault |
|---|---:|---:|---:|
| guardrail_friction | 21 | 2.00 | 1 |
| infra_api_fault | 11 | 2.00 | 0 |
| premature_completion_claim | 10 | 2.90 | 10 |
| tool_misuse | 6 | 2.33 | 6 |
| loop_no_progress | 6 | 2.50 | 6 |
| other | 6 | 2.00 | 3 |
| wrong_edit | 5 | 3.20 | 4 |
| instruction_ignored | 5 | 2.40 | 5 |
| user_changed_mind | 4 | 1.00 | 0 |
| hallucinated_fact | 4 | 3.00 | 4 |
| context_loss | 3 | 1.67 | 3 |
| benign_false_positive | 3 | 1.00 | 0 |
| env_breakage | 2 | 2.50 | 0 |
| subagent_noncompliance | 1 | 3.00 | 1 |
| spec_misunderstanding | 1 | 3.00 | 1 |
| over_scope | 1 | 2.00 | 1 |

And what would have prevented them:

| Avoidable by | n |
|---|---:|
| not_avoidable | 29 |
| agent_should_have_verified | 26 |
| harness_config | 12 |
| infra_fix | 7 |
| bigger_model | 6 |
| agent_should_have_asked | 5 |
| better_prompt | 4 |

(`data/dashboard-data.json` keys `confirmed_modes`, `avoidability`.)

The three agent-caused modes with the highest severity, `wrong_edit` (3.2),
`hallucinated_fact` (3.0) and `premature_completion_claim` (2.9), share one
mechanism: **asserting before enumerating or checking**. That is the study's
central substantive claim, and it rests on 19 adjudicated cases.

---

## 5. The MAST cross-walk

### 5.1 What MAST is

**MAST** is the Multi-Agent System Failure Taxonomy (Cemri, Pan, Yang et al.
2025, arXiv:2503.13657): 14 failure modes in 3 categories, built from roughly
1,600 execution traces across 7 conversational multi-agent frameworks. It is the
field's standard vocabulary for describing how agent systems fail.

Its three categories:

- **FC1, specification and system design.** Disobeying the task spec, disobeying
  a role, repeating a completed step, losing conversation history, not
  recognising a stopping condition.
- **FC2, inter-agent misalignment.** Conversation reset, failing to ask for
  clarification, task derailment, withholding information, ignoring another
  agent's input, reasoning-action mismatch. This is MAST's **largest** category
  in its own corpus, at roughly 42%.
- **FC3, task verification and termination.** Premature termination, no or
  incomplete verification, incorrect verification.

(Mode-by-mode definitions as used by our coders are in
`experiments/prereg-2026-08-06-external.md` §A.1.)

### 5.2 What we asked

One narrow question: **when our 13 detectors fire, how often does the underlying
incident fit a real MAST mode, and what does the residue look like?**

This is coverage measurement. There is no treatment, no contrast, and no
significance to report. (`experiments/mast-coverage.md`.)

Coders assigned **one label per incident** from an 18-label set: the 14 MAST
modes, three proposed extension families, and UNCLEAR. MAST took precedence
whenever a mode genuinely applied, and UNCLEAR was used rather than forcing a
fit. Coders saw the incident packet with detector names stripped.
(`experiments/mast-coding-scheme.md`.)

The three extension families we proposed, because MAST has no cell for them:

- **E1, human-in-the-loop interaction failure.** The decisive breakdown lives at
  the human-agent boundary: the human corrects, rejects, overrides or interrupts,
  or the agent mishandles that steering.
- **E2, single-session infrastructure failure.** An environment or platform
  fault untied to any coordination decision: quota kills, permission and sandbox
  blocks, network outages, isolated tool faults.
- **E3, fan-out coordination failure.** An orchestrator scatters work to
  non-conversing workers and the coordination itself fails: a worker returns
  nothing, a shard is dropped, an ensemble vote is lost.

### 5.3 Why the answer is a range and not a number

Four coding settlements exist over the same 142 incidents, and they disagree:

| Settlement | Raw MAST share | Population-weighted share |
|---|---:|---:|
| Round 1, single coder, published | 21.3% | 18.7% |
| Round 1, blind two-coder consensus (n=73) | 21.9% | 18.5% |
| Enlargement combined (n=142) | 21.1% | 16.5% |
| Settled, after the amendment recode (n=142) | 25.4% | 22.4% |

The published claim is therefore a range: **MAST reaches 21% to 25% raw and
16.5% to 22.4% population-weighted**. Range endpoints are the minimum and
maximum across those settlements. Neither endpoint is typed by hand; the
generator derives both.
(`data/dashboard-data.json` key `mast_coverage_settled`, sub-key
`settlement_readings`.)

Displayed endpoints are rounded **outward**, low end floored and high end
ceiled, so a displayed range can never look tighter than the evidence behind it,
and the complement (the share MAST does *not* cover, 74% to 79%) is derived from
those same endpoints rather than rounded independently.

**"Raw" versus "population-weighted".** Raw is the share among the coded
incidents. Population-weighted takes each detector mode's coded distribution and
weights it by that mode's incident count across the whole atlas, which is what
you want if you are asking about the corpus rather than about the sample. The
weights are frozen at N=4016 incidents for comparability across rounds; the
atlas has since grown to 4,662, and the weights will be re-derived when the
scheme is next revised. (`experiments/mast-enlargement.md`, notes.)

Weighting barely moves MAST but reshapes the residue, because the two largest
detectors by population, `tool_error` and `api_error`, are heavily E2.

### 5.4 The current settled picture

At n=142, pooled across both coding rounds: **36 incidents fit a real MAST mode,
67 need an extension family, 39 are UNCLEAR.**
(`data/dashboard-data.json` key `mast_chart`.)

The infrastructure family E2 is **31.7% to 34.5% raw and 40.8% to 47.2%
population-weighted**, which makes it the largest single family under every
settlement, larger than everything MAST covers combined.
(Read from `data/mast-settled.json` and `data/mast-combined.json`, keys
`combined_raw.E2` and `combined_weighted.E2`.)

Three structural claims are invariant across the entire range, every coder and
every settlement:

1. **The infrastructure family is the largest**, in every weighting.
2. **E3 drew zero cases in 142 codings.** It is a structural prediction, not an
   observation. This is the claim in the extension proposal most likely to be
   wrong, and it may be a category with no members.
3. **MAST's largest category is our smallest.** FC2, inter-agent misalignment,
   is roughly 42% of MAST's own corpus. In the enlargement round's consensus
   labels at n=142 it is 8 incidents, against FC3's 13 and FC1's 9.
   (`experiments/mast-enlargement.md`.)

Why FC2 collapses: it is defined around agents that converse. Our systems are
orchestrators fanning work to workers that never talk to each other, and agents
in a loop with a human. There is no peer dialogue to misalign. What survives
translation is FC3, an agent failing to verify its own output, which is
single-agent-shaped.

Note that a previously published explanation for the FC2 gap, that our
architecture is fan-out over parallel stateless workers, **was cut** after the
external validation round found no coding evidence for that architecture in this
corpus or in either foreign corpus checked. Why FC2 is absent is now an open
question. (`data/dashboard-data.json` key `mast_crosswalk.structural`.)

### 5.5 Agreement between coders, in plain terms

**Cohen's kappa** measures how much two coders agree beyond what you would
expect if they were both guessing at their own observed rates. 0 means no better
than chance. 1 means perfect. In taxonomy work, above 0.6 is usually treated as
usable, 0.4 to 0.6 as moderate and caveated, below 0.4 as not usable.

| Round | Coders | n | Agreement on the family (5 buckets) | Agreement on the exact mode (18 labels) |
|---|---|---:|---:|---:|
| Reliability round | Two blind, plus tiebreak | 73 | percent 72.6, **kappa 0.632** | percent 63.0, **kappa 0.536** |
| Enlargement round | Two blind, plus tiebreak | 69 | **kappa 0.516** | **kappa 0.541** |

(`experiments/mast-irr.md`, `experiments/mast-enlargement.md`;
`data/dashboard-data.json` keys `kappa_bucket_irr`, `kappa_full_label_irr`,
`kappa_bucket_enlargement`.)

Read that as: **coders agree on which family a failure belongs to far more often
than on which exact mode**, and the reliability round cleared its
pre-registered 0.6 bar while the enlargement round did not, landing in the 0.4
to 0.6 band where the frozen rule says the numbers carry an explicit caveat and
no further enlargement happens.

Where the disagreement lives is more informative than the coefficient. In round
1, of 27 disagreements, the modal pattern (10) was one coder assigning a MAST
verification mode where the other coded UNCLEAR: the boundary between "completed
work with a skipped check" and "successful work the detector false-fired on" is
the scheme's soft spot. In round 2, of 26 disagreements, that boundary appeared
again (8) alongside a new one, infrastructure-versus-MAST (7): an environment
fault occurring inside agent work that also shows a reasoning defect.

### 5.6 The amendment that failed its own bar

A scheme amendment (v1.1) was written to tighten those two boundaries, and two
fresh blind coders recoded only the 26 previously-disagreed incidents under the
amended text. The pre-registered success bar was 60% agreement. **Observed:
11 of 26, 42%** (46% at family level). **The amendment failed**, and is reported
as a failure rather than quietly revised.
(`experiments/mast-recode-results.md`; `recode_agreement` = 0.423 in the data
package.)

What the failure taught: the new rules moved coders toward each other on the
windows they were written for and opened a new seam, namely what to call an
agent that gets blocked by its own governance layer and then routes around the
block. That needs its own named category, not a precedence rule. Enlargement is
gated closed until the scheme is redefined rather than clarified.

---

## 6. The pre-registered experiments

"Pre-registered" means the hypothesis, the cohort rule, the statistic and the
kill line were written down and committed **before** the numbers were computed.
The point is to make it impossible to move the goalposts after seeing the data.

The honest summary: **most of them did not survive.** That is the section.

### 6.1 The objectivity axis, in full

This is the study's own headline finding and its own retraction. Both runs stay
in the record. Run 02 supersedes run 01.

**The hypothesis, unchanged across both runs.** Work with an objectively
checkable answer should fail *mechanically* (tool errors, error loops, stuck
repetition). Work with no such check should fail *relationally* (frustration,
challenged claims, self-correction). The statistic is a ratio of ratios:
mechanical-to-relational in the objective cohort, divided by
mechanical-to-relational in the subjective cohort.

**Pre-registered thresholds, identical in both runs: pass at 2.0 or above, kill
below 1.5.**

#### Run 01, keyword cohorts (2026-08-05)

Cohorts were defined by project-name keywords. "Objective" meant the working
directory matched a list of code-project patterns and was not the org hub.
"Subjective" meant hub sessions whose path or branch matched a 13-word
memory/knowledge/writing list.

| Cohort | Sessions | Events | Mechanical | Relational | Mech:Rel |
|---|---:|---:|---:|---:|---:|
| Objective | 41 | 7,948 | 23 | 10 | 2.30 |
| Subjective | 50 | 55,315 | 83 | 179 | 0.464 |
| Ambiguous, excluded | 531 | 273,665 | | | |

**Ratio of ratios: 4.96.** Two-proportion z on mechanical share: 4.29.

It was adversarially verified: a second agent independently re-derived every
denominator, count, rate and weight, and agreed exactly. It survived four
robustness checks:

| Variant | Ratio of ratios |
|---|---:|
| Headline | 4.96 |
| Narrow cohort (contaminated keyword removed) | 4.376 |
| Precision-weighted | 4.733 |
| Narrow and precision-weighted | 4.183 |
| Largest project dropped | 4.583 |
| Sidechains included | 6.150 |

Full range across every logged variant: **4.183 to 6.150**.
(`data/dashboard-data.json` key
`experiment_objectivity_axis.run_01_keyword_cohorts`;
`experiments/objectivity-axis-01/RESULTS.md` and `log.jsonl`.)

The run **disclosed its own degree of freedom**: the 13-word subjective keyword
list was fixed after seeing session composition, before seeing incident counts.

#### Run 02, behavioral cohorts (2026-08-05, same day)

Run 02 closed that degree of freedom. The objective pole was redefined by an
actual machine-checkable signal, committed before counts were read:

- **Objective** = the session ran at least one test command (a shell call
  matching pytest, npm/pnpm/yarn test, cargo test, go test, jest, vitest, tox,
  make test, or a PR-checks call).
- **Subjective** = zero such test executions **and** at least 3 edits to prose
  files.
- Everything else excluded and counted.

| Cohort | Sessions | Mechanical | Relational | Mech:Rel |
|---|---:|---:|---:|---:|
| Objective | 194 | 500 | 618 | 0.809 |
| Subjective | 88 | 183 | 249 | 0.735 |
| Excluded | 340 | | | |

**Ratio of ratios: 1.101.** Two-proportion z on mechanical share: 0.84, not
significant. The kill line was 1.5. **The effect is gone.**
(`experiments/objectivity-axis-02/result.json` and `RESULTS.md`;
`data/dashboard-data.json` key
`experiment_objectivity_axis.run_02_behavioral_cohorts`.)

#### Why 02 supersedes 01

Run 01 was measuring **project type, not objectivity**. The keyword split put
agent-infrastructure work, which is tool-error-heavy for reasons that have
nothing to do with whether a task has a checkable answer, on one side, and
writing and memory work on the other.

Run 01's robustness checks could not have caught this. Dropping the largest
project, weighting by precision and including sidechains are all perturbations
*inside* the keyword framing. **Robustness to variations inside a framing is not
robustness of the framing.** The one disclosed degree of freedom turned out to
be the whole finding.

**Two caveats on run 02 itself**, so they do not have to be discovered: the
test-execution proxy is coarse (a session can run tests and still be doing
subjective work), and the subjective cohort is small at 88 sessions. A stronger
design would label objectivity per session by adjudication rather than by proxy.
But 1.101 is not 4.96, and the 01 headline cannot stand as written.

(Run 02's own write-up quotes the 01 result as "4.4x". That is a rounding of
01's narrow-cohort sensitivity variant, 4.376, not of its headline, 4.96. The
headline is the pre-registered statistic and is the figure used here.)

**The honest state of the objectivity hypothesis for this corpus: undetermined,
leaning negative.**

One further consequence: the cross-ecosystem "texture" difference reported
elsewhere in this study, that the assistant fleet leans relational while the
coding corpus leans mechanical, may be the same confound. It is reported with
that flag attached.

**A number that was removed rather than re-typed.** Run 02's write-up prose
quotes a second figure, 1.23, for a "broad grouping". Neither the pre-registered
spec nor the run script defines a broad grouping, and the script computes and
logs exactly one grouping, so the figure cannot be reproduced from any record.
It was cut from the data package.
(`data/dashboard-data.json` key `experiment_objectivity_axis.cut_claims`.)

### 6.2 The four phase-2 contrasts

Four contrasts were pre-registered against the atlas. Three were adversarially
re-derived and then killed or wounded, all on the same confound.
(`experiments/phase2-findings.md`; `data/dashboard-data.json` key
`what_didnt_hold`.)

| Prediction | Status | What happened |
|---|---|---|
| Agents self-correct far more with a human in the loop | **killed** | The headline was 4.93x. But 79% of human-present self-corrections fire on **one politeness token** that requires a preceding interlocutor by construction, and the autonomous arm produces the same token to its orchestrator. Drop that token and a real effect does survive: a turn-adjacency gap of 3.0% vs 1.4%, z = 3.0, which **is** significant. It is killed on construct validity, not on significance, because it appears in both arms and measures interlocutor adjacency rather than a human-versus-delegation disposition. |
| Orchestrator subagents fail more mechanically than human sessions | **wounded** | Mostly a tautology: the relational detectors that cannot fire without a human message are 78% of top-level relational incidents. The honest residual is a marginal 1.85x lower self-initiated correction under delegation, 2.4% vs 1.3%, z = 2.28, p about 0.02. |
| The chat platform shapes the failure mode | **killed** | The same bot on two platforms is indistinguishable, and within one platform the bot-to-bot spread is wider than the entire cross-platform range. It is bot deployment, not platform. |
| Group chats fail differently than one-to-one | **null** | No significant difference, z = 0.674. |
| Objective work fails mechanically far more than subjective work | **killed** | §6.1. |

The single mechanism behind four of these five: **our detectors split into
human-text detectors and tool-output detectors, and any cohort axis that
correlates with human presence will manufacture a large, robust-looking gap that
is really just the human-text detectors switching off on one side.**

"None of five survived" is true. "We found nothing" is not: two of the five left
a real, smaller effect behind after the flawed part was stripped out, and both
are recorded above with their statistics.

### 6.3 The external validation round

On 2026-08-06 a pre-registration was frozen
(`experiments/prereg-2026-08-06-external.md`) covering three arms against
outside datasets. The scored results are in
`experiments/external-validation-findings-2026-08-06.md`. Fifteen lines were
scored: twelve numbered predictions, plus one arm-level verdict, one secondary
measure and one registered caveat.

**Scorecard: four confirmed (two of them uninformative or unusable), five
refuted, three untested, one split, one mixed, one caveat triggered.**

Three results are worth carrying:

**Arm 1, the reciprocal test.** We coded our incidents against MAST and found it
reached about one in five. So we ran it backwards: coded 149 traces from MAST's
own annotated corpus against **our** extension families. Our families reach
**5 of 149, 3.36%** (95% interval 1.44% to 7.61%), and the two families that
carry the extension proposal, human-in-the-loop and infrastructure, reach
**1 of 149, 0.67%**. The blindness is reciprocal: their taxonomy does not
describe our corpus and our families do not describe theirs. That is evidence
the gap is architectural rather than an oversight by either side.

The registered decision rule gated declaring that conclusion on agreement
between two coders. **Only one coder ran.** Agreement is therefore not low, it
is uncomputable, and the conclusion is provisional by its own rule.
(`experiments/reciprocal-mast-test.md`.)

**Arm 2, do our detectors generalise?** The detector suite was run over four
independent trajectory corpora from other people's agents. The answer splits
three ways and conflating any two of them is the easiest way to get this wrong:

1. **The mechanical core transfers.** `tool_error`, `error_loop` and
   `stuck_repetition` fire in all four corpora and clear their pre-registered
   floors in all four. They are not artifacts of our own logging. This is the
   strongest thing the arm produced.
2. **The magnitudes were wrong, in both directions, and partly instrumental.**
   On one corpus at least 31.8% of derived errors sit on file listings;
   suppressing them moves `tool_error` from 7.56x to 5.16x. On another, 50.03%
   of derived errors fire on a lexical clause alone with no exit code.
3. **Nine of thirteen detectors could not be exercised at all.** Their zeros
   were declared structural before any corpus was opened, and must never be read
   as measured zeros. They key on things that are properties of a *production
   harness*, a human turn, an interrupt, a governance block, harness telemetry,
   a sidechain, not properties of an agent. **Those are exactly the territory
   the extension proposal rests on.** This arm is structurally incapable of
   validating the part of the atlas that most needs validating.

Two specific failures from this arm are worth naming because they are the
sharpest instrument criticism in the study:

- **The guardrail detector was predicted to return exactly zero on all four
  outside corpora, and fired in all four**: 64, 73, 27 and 7 firings, 171 total,
  every one a false positive. It was matching an ordinary Unix permission
  message rather than a governance block.
- **The frustration detector fired 14 times on the one corpus with real human
  turns, and all 14 were inspected and all 14 are false positives**, all from a
  single marker, while genuine escalating frustration in another language went
  unseen. That corpus was then **voided** by its own pre-registered adapter
  check (61.1% agreement against an 80% bar), so the relational half of the
  atlas is **unvalidated: not validated, not refuted, untested.**
- **The self-correction detector spans 172x across four corpora** that differ
  only in scaffold, from 6.727 per 1k to 0.039 per 1k. A detector whose rate
  varies that much across corpora that are all machine-facing and human-free is
  not measuring one construct. The construct generalises; the operationalisation
  does not.

Anyone reading "the atlas generalises" off the mechanical core is reading four
detectors and calling it thirteen.

**Arm 3, cross-taxonomy agreement.** Against a third-party failure-attribution
dataset, the label-family concordance test was **refuted outright**: kappa
0.2215, below its own 0.25 falsifier line. Two of the three arm-3 predictions
were never attempted.

**What did not run at all, in any arm: every second coder.** Six coder roles
were registered and zero were run. Every arm-1 and arm-3 result is single-coder.

### 6.4 One pre-registration is open and unrun

`experiments/prereg-2026-08-07-disagreement-structure.md` registers the next
study: measuring **where taxonomy disagreement actually lives**, against a
reference standard of roughly 900 human annotation events with three independent
human annotators per row. Its motivating observation is that **the disagreement
about what counts as a failure at all is larger than the disagreement about
which cell it goes in**. Status: pre-registered, no statistic computed. Nothing
from it appears on the page or in this document.

---

## 7. Every known limitation, consolidated

Ranked roughly by how much each one should change your reading.

**1. The corpus is one operator plus one fleet.** The coding half is a single
person's Claude Code sessions. Every rate, every position-in-session
distribution and every model-tier split is that person's workflow as much as it
is anything about agents. The assistant fleet is genuinely multi-human, which is
why it is in the study, but two ecosystems is not a sample of ecosystems.

**2. The detectors define the sampling frame.** This study can only measure
failures our 13 detectors fire on. Anything they miss is invisible to it,
including failures MAST would catch that we have no detector for. "MAST reaches
21% to 25%" is coverage of *our detected incidents*, not of agent failures in
general, and says as much about our detector set as about MAST. The external
round (§6.3) established that nine of the thirteen cannot even be tested on
benchmark corpora.

**3. Twelve judgments per detector.** Every precision figure and every interval
in §3.2 rests on 12 adjudicated incidents. One reclassification moves a
precision by 0.083. The intervals are published precisely so the width is
visible.

**4. Single coder on most results.** The MAST coverage work has two blind coders
and a tiebreak, and reports its kappas. The reciprocal test, the cross-taxonomy
arm and the detector-generalisation precision checks are **single-coder**; six
registered coder roles never ran. Where a decision rule required two coders, the
conclusion is marked provisional rather than quietly declared.

**5. Every coder and every judge is a Claude-family model.** The MAST reliability
plan called for two different model families and got two Claude models plus a
Claude tiebreak. The adjudication judge shares a family with many of the judged
agents. Agreement figures may be inflated by shared training biases relative to
human coders. This is the study's largest remaining reliability caveat and it
has never been removed.

**6. n is about 6 per detector mode in the MAST coverage sample.** Every
per-mode fraction feeding the population weighting is a point estimate off six
draws, or three for the smallest detector. Reclassifying one incident in a
high-population mode moves the weighted total by percentage points. Read the
direction, not the decimals.

**7. UNCLEAR conflates two different things.** "Genuinely unplaceable" and
"detector false positive on successful work" are both coded UNCLEAR. The roughly
28% UNCLEAR share is therefore partly a taxonomy gap and partly a precision
problem in our own frame, and this study does not separate them.

**8. Population weights are frozen and now stale.** MAST weighting uses N=4016
incidents for cross-round comparability. The atlas now holds 4,662.

**9. `abandonment` cannot tell "gave up" from "went to dinner"** without joining
the next session. The bridging machinery exists but has not been extended
intra-ecosystem, so `abandonment` at 0.33 precision is partly a design limit,
not just a tuning failure.

**10. The frustration lexicon is English-only and register-blind.** Its 0.58
precision measures the damage. In the one outside corpus with human turns, real
frustration in another language was invisible to it.

**11. Assistant-fleet tool-error detection is weaker than Claude-side.** That
ecosystem has no native error flag, so detection is regex over content. Any
cross-ecosystem tool-error contrast is therefore partly instrumental.

**12. Model-tier comparisons are descriptive only.** Incidents per 10k events by
maximum model tier in session: tier 0 (unlabeled) 134.5, tier 1 28.17, tier 2
67.44, tier 3 64.97, tier 4 61.05. Tier choice correlates with task difficulty
and with date, so this is not a capability ranking.
(`data/dashboard-data.json` key `by_model_tier`.)

**13. Timeline is confounded.** Failure rate climbed from January to May 2026
and fell afterwards. That is confounded with model generation and with the
operator's own workflow maturation. Flagged, never causally attributed.
(`data/dashboard-data.json` key `timeline`.)

**14. Incident-level significance tests are optimistic.** Incidents cluster
within sessions, so the independence assumption behind the z-tests is violated.
No session-level clustered inference was run. Treat every z and p in this
document as directional.

**15. The extractor loses about 1.9% of parsed events to its own primary key**
(§1). Found while writing this document; not previously disclosed.

**16. The study is inside its own corpus.** The sessions that built this
pipeline are in the data it analyses.

**17. Cross-session escalation uses a working-directory plus 2-hour window**, so
it misses escalations across repositories. 596 bridge candidates, 86 above the
strong threshold of 0.5. (`data/dashboard-data.json` key
`escalation_bridges`.)

---

## 8. Running it on your own logs

The pipeline is standard-library Python 3.9 and nothing else. Four commands:

```bash
python3 pipeline/extract.py    --db data/atlas.db   # parse transcripts
python3 pipeline/detectors.py  --db data/atlas.db   # run the 13 detectors
python3 pipeline/incidents.py  --db data/atlas.db   # cluster into incidents
python3 pipeline/analyze.py    --db data/atlas.db   # → analysis.json
```

**Pass `--db` explicitly.** The scripts default to the lab's own path
(`labs/failure-atlas/data/atlas.db`) and will fail if that directory does not
exist in your layout.

`extract.py` defaults to `~/.claude` and `~/.claude-*` as its roots; override
with `--roots`. A test suite ships at `pipeline/test_pipeline.py`.

### The privacy model

This matters more than the code.

- **Raw transcripts never move.** They stay where the harness wrote them.
- **The store keeps truncated text only where detection needs it**, plus
  `(file, line)` pointers for everything else.
- **The shareable layer is counts and rates.** `analysis.json` contains no
  transcript text, no session keys and no paths.
- **Thinking traces are local-only, permanently.** They never enter
  `analysis.json`, the dashboard package, or any pooled artifact.
- **The read-only HTTP API** (`pipeline/atlas_api.py`) binds to localhost only,
  opens the database read-only, rejects anything but GET, and is never exposed
  publicly. The store contains private messages.

Pooling installations means pooling `analysis.json` files, not data: a common
schema, local data, shared statistics. That is the OMOP model from clinical
research, applied to agent logs. **This is why the atlas is worth anything only
if other people run it.** One operator's atlas is an anecdote with error bars.

### Adjudication, if you want precision numbers of your own

```bash
python3 pipeline/context_window.py --db data/atlas.db --list-sample 12
python3 pipeline/context_window.py --db data/atlas.db --incident inc-XXXX
```

Feed each rendered window to a judge, collect the label records described in
§4.3, and run `pipeline/adjudication_ingest.py`. Precision is computed per
round at label time, which is the only way it stays correct across detector
changes.

---

## 9. Provenance, and the correction trail

### 9.1 The generator was caught fabricating

The lab's standing rule is: never hand-edit numbers into the page, regenerate
from the data package. On 2026-08-07 that rule was found to be defeated one
level up. **The generator itself typed values.** The page then validated against
the package, and the claim-binding map bound page prose back to those same typed
strings. A fabricated number validated itself, three times over.

Two figures were outright fabrications, existing in no source record at any
rounding:

- A ratio-of-ratios of **4.38** with a sensitivity range of [4.38, 6.2]. The run
  record reports **4.96**, range 4.183 to 6.150.
- The phrase **"self-initiated corrections show no significant gap (z about
  1.1)"**. No z of 1.1 exists anywhere in the lab record. The finding it
  described was **significant** (z = 3.0) and was killed on construct validity.
  The old string both invented the statistic and inverted the reason the finding
  died.

A third claim, "4 of 6 relational detectors cannot fire without a human", was
also removed: the source record says "four relational detectors" and gives their
share of top-level relational incidents; it states no denominator of six. The
share is published instead of the invented fraction.

(`experiments/generator-provenance-fix.md`;
`data/dashboard-data.json` keys `what_didnt_hold_cut_claims`,
`experiment_objectivity_axis.cut_claims`.)

### 9.2 What now prevents it

The generator carries a top-level `provenance` block mapping every emitted
figure to the file and key it was read from, and three assertion passes that are
all fatal:

1. **Coverage.** Every numeric leaf in the emitted package must sit under a
   registered provenance path.
2. **Prose.** Every digit token inside every emitted string must be a rendering
   of a value provenanced **for that exact path**. A global token pool was tried
   first and rejected, because it let a fabricated `1.1` borrow legitimacy from
   an unrelated live `1.101` elsewhere in the package.
3. **Fidelity.** The emitted value at each provenanced path must equal the
   derived value, so a provenanced path cannot become a place to type over the
   derivation.

Negative tests were run and their failures quoted in the fix record: reinstating
either original fabrication now kills the build.

There are no silent fallbacks. A missing experiment result used to substitute a
typed value; it now raises.

### 9.3 The rounding rule

Shares are converted to percentages and rounded half-up to one decimal place.
Range endpoints are additionally published as integers rounded **outward**, low
end floored and high end ceiled, so a displayed range can never look tighter
than the evidence behind it. Complement ranges are derived from those same
endpoints rather than rounded independently. Consumers render the display
strings and must not re-round the decimal endpoints.

### 9.4 Corrections logged rather than edited away

Four things this study got wrong and published as corrections rather than
quietly fixing:

- Counting transcript files as sessions, overstating sessions by roughly 6.5x
  (§1).
- Positional incident identifiers that silently drifted labels onto the wrong
  incidents, costing 125 of 216 adjudication labels (§4.5).
- The objectivity axis, killed by its own follow-up (§6.1).
- A scheme amendment that failed its own 60% agreement bar (§5.6).

---

## 10. Source-record index

| Topic | Record |
|---|---|
| Data package and provenance map | `data/dashboard-data.json` |
| Detector specifications | `pipeline/detectors.py` |
| Incident clustering and precedence | `pipeline/incidents.py` |
| Adjudication windows and sampling | `pipeline/context_window.py` |
| Precision computation | `pipeline/adjudication_ingest.py`, `data/precision.json` |
| Design decisions and their falsification paths | `DECISIONS.md` |
| Findings summary and detector honesty table | `FINDINGS.md` |
| MAST coverage study | `experiments/mast-coverage.md` |
| Coding scheme | `experiments/mast-coding-scheme.md` |
| Inter-rater reliability round | `experiments/mast-irr.md` |
| Enlargement round | `experiments/mast-enlargement.md` |
| Amendment recode, failed | `experiments/mast-recode-results.md` |
| Settlement files | `data/mast-settled.json`, `data/mast-combined.json` |
| Objectivity axis run 01 | `experiments/objectivity-axis-01/SPEC.md`, `RESULTS.md`, `log.jsonl` |
| Objectivity axis run 02 | `experiments/objectivity-axis-02/SPEC.md`, `RESULTS.md`, `result.json` |
| Phase-2 contrasts | `experiments/phase2-findings.md` |
| External-corpus pre-registration | `experiments/prereg-2026-08-06-external.md` |
| External-corpus scored findings | `experiments/external-validation-findings-2026-08-06.md` |
| Reciprocal MAST test | `experiments/reciprocal-mast-test.md` |
| Open pre-registration | `experiments/prereg-2026-08-07-disagreement-structure.md` |
| Generator fabrication fix | `experiments/generator-provenance-fix.md` |

Records under `pipeline/` ship with the page. Records under `experiments/` and
`data/` are lab files that stay on the operator's machine, cited so each claim
has a named source.

---

*The page states what we think is true. This document states how much of it we
had to take back.*
