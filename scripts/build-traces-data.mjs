#!/usr/bin/env node
/**
 * build-traces-data.mjs — emit docs/experiments/fde-first-proof/traces-data.json
 *
 * Builds the dataset for the "process, visualized" page from verified anchors.
 * Every event carries the Discord message id it was sourced from, so a reader can
 * audit each point against the (public, scrubbed) traces archive.
 *
 * Deterministic: same input → same output. Re-run after any archive correction.
 *
 * Counting rules (printed on the page):
 *   buildEvent   = a `lake build` result the agent reported in-thread (green or red),
 *                  NOT every internal compile. Job counts recorded where stated.
 *   processEvent = a failure / recovery / pitfall the agent itself flagged, or an
 *                  external-review catch, with who-caught-it attribution.
 *   messageVolume= per-day per-actor message counts from the two Lean threads
 *                  (status pings excluded).
 *   cost         = from Hermes session telemetry (OpenRouter, Kimi K3); estimated,
 *                  not provider-actual. See VIZ_SPEC §4b.
 */
import { writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dir = dirname(fileURLToPath(import.meta.url));
const OUT = join(__dir, '..', 'docs', 'experiments', 'fde-first-proof', 'traces-data.json');

/* ---- Build events: green ▲ / red ▼ / false-green (ring) -------------------- */
/* result: green | red | false-green. jobs recorded where the agent stated them. */
const buildEvents = [
  { t: '2026-08-07T05:47:40Z', result: 'green', label: 'scaffold / semantics', jobs: null, msg: '1535162495537250305', note: 'Basic.lean green; truth tables 16/16 ground-truthed' },
  { t: '2026-08-07T06:29:58Z', result: 'green', label: 'soundness', jobs: null, msg: '1535173139171123300', note: '0 sorries, 22 declarations, full build' },
  { t: '2026-08-07T07:54:29Z', result: 'red', label: 'refutes regression', jobs: null, msg: '1535194406154403850', note: '2 sorries left in Saturated.refutes; owned, recovery path recorded' },
  { t: '2026-08-08T23:58:15Z', result: 'green', label: 'refutes fixed', jobs: null, msg: '1535799335978139738', note: 'canonical countermodel green after antecedent-only valuation restored' },
  { t: '2026-08-09T01:49:36Z', result: 'false-green', label: 'stale-cache green', jobs: 8658, msg: '1535827359582789763', note: 'full build "completed" on broken source; module-targeted build surfaced ~20 errors' },
  { t: '2026-08-09T03:29:51Z', result: 'green', label: 'completeness (module-targeted)', jobs: 8657, msg: '1535852588946296883', note: 'real re-elaboration; the verification checklist passes' },
  { t: '2026-08-09T03:43:28Z', result: 'green', label: 'completeness verified', jobs: 8658, msg: '1535856013956219051', note: '0 sorries; #print axioms clean both directions' },
  { t: '2026-08-10T10:26:03Z', result: 'green', label: 'corollaries', jobs: null, msg: '1536319714685358080', note: '0 sorries, 17 declarations, axioms checked per-theorem' },
  { t: '2026-08-10T20:51:27Z', result: 'green', label: 'full build (all 5 modules)', jobs: 8660, msg: '1536477100557471855', note: '8658→8660 confirms Completeness+Corollaries in default target' },
  { t: '2026-08-10T21:49:40Z', result: 'red', label: 'mathlib restore broken', jobs: null, msg: '1536491753207496895', note: 'hardlink I/O artifact during repo prep; restored + re-verified' },
  { t: '2026-08-10T21:53:45Z', result: 'green', label: 'repo tree green', jobs: 8658, msg: '1536492781827260447', note: '8658 jobs green from the committed state before push' },
  { t: '2026-08-11T00:00:00Z', result: 'green', label: 'post-review re-verify', jobs: 8658, msg: '1536499171446755428', note: 'rebuilt after Claude\u2019s killed clone wiped the olean tree; 8658 jobs, EXIT=0' },
];

/* ---- Process events: who caught it ------------------------------------------ */
/* caughtBy: self | human | external. kind: pitfall | recovery | walkback | outage | design */
const processEvents = [
  { t: '2026-08-07T06:55:20Z', kind: 'pitfall', caughtBy: 'self', label: 'refutingVal wrong for FDE', msg: '1535179524805763185', note: 'read truth-support from succedent; reverted to clean sorry, recorded honestly' },
  { t: '2026-08-07T07:54:29Z', kind: 'pitfall', caughtBy: 'self', label: 'refutes valuation misdiagnosis', msg: '1535194406154403850', note: 'mistook a tactic bug for a math bug; caught by exhaustive #eval ground truth' },
  { t: '2026-08-09T01:42:31Z', kind: 'walkback', caughtBy: 'self', label: 'honest-W walkback', msg: '1535832898215612458', note: 'nearly claimed the W on stale cache; module-targeted verification caught it' },
  { t: '2026-08-09T02:09:37Z', kind: 'pitfall', caughtBy: 'self', label: 'replace_all corrupted 12 sites', msg: '1535832396052566117', note: 'naive string replace clobbered antecedent/succedent perm orientations' },
  { t: '2026-08-09T02:33:12Z', kind: 'outage', caughtBy: 'self', label: 'tool calls misfiring', msg: '1535838329554215002', note: 'refused to patch blind; stopped and handed off' },
  { t: '2026-08-09T21:20:14Z', kind: 'outage', caughtBy: 'self', label: 'tool channel degraded (recur)', msg: '1536121956414390302', note: 'reads execute but results never arrive; refused to prove blind' },
  { t: '2026-08-09T22:36:04Z', kind: 'recovery', caughtBy: 'human', label: '191 results / 10 ids diagnosed', msg: '1536141039822438511', note: 'Juni: tool_call_id collision; assembler drops unpairable results' },
  { t: '2026-08-10T10:22:07Z', kind: 'pitfall', caughtBy: 'self', label: 'Or/∃ eliminate only into Prop', msg: '1536318724712177694', note: 'three Type-valued decider architectures failed; fix = prove-in-Prop-then-lift' },
  { t: '2026-08-10T10:23:52Z', kind: 'pitfall', caughtBy: 'self', label: 'valid_of_perm orientation recurs', msg: '1536319163566391366', note: 'same perm trap as completeness session, now on the decider inr side' },
  { t: '2026-08-10T21:44:36Z', kind: 'review', caughtBy: 'external', label: 'Rey redlines (3)', msg: '1536490277261279395', note: 'missing-import false-W; "constructive" overstated; open-model scope. 2 conceded, 1 held' },
  { t: '2026-08-11T00:00:00Z', kind: 'review', caughtBy: 'external', label: 'Claude artifact audit', msg: '1536502968008843515', note: 'Classical.choice attribution wrong (real error, corrected); stale headers; novelty scoped' },
];

/* ---- Message volume (per-day per-actor, status pings excluded) -------------- */
/* Discord-visible prose messages in the FDE sessions, status pings and tool-only echoes
 * excluded (counted from Hermes session telemetry). Iris (comms agent) is excluded —
 * she's a supporting agent, not a prover, and her volume isn't part of the proving arc. */
const messageVolume = [
  { day: '2026-08-07', matilde: 111, juni: 9 },
  { day: '2026-08-08', matilde: 13, juni: 1 },
  { day: '2026-08-09', matilde: 121, juni: 16 },
  { day: '2026-08-10', matilde: 320, juni: 24 },
  { day: '2026-08-11', matilde: 109, juni: 16 },
];

/* ---- Cost (Hermes session telemetry; OpenRouter, Kimi K3) ------------------- */
const cost = {
  sessions: 7,
  inputTokens: 9438922,
  outputTokens: 337468,
  cacheReadTokens: 99876544,
  estimatedCostUsd: 63.34,
  costStatus: 'estimated',
  phases: [
    { label: 'origin + soundness (Aug 7)', sessions: 2, inputTokens: 1306683, outputTokens: 78173, cacheReadTokens: 15700224, estimatedCostUsd: 9.80 },
    { label: 'completeness (Aug 8\u20139)', sessions: 4, inputTokens: 2542380, outputTokens: 122402, cacheReadTokens: 26540672, estimatedCostUsd: 17.43 },
    { label: 'corollaries + publication + reviews (Aug 10\u201311)', sessions: 1, inputTokens: 5589859, outputTokens: 136893, cacheReadTokens: 57635648, estimatedCostUsd: 36.11 },
  ],
};

/* ---- Timeline window --------------------------------------------------------- */
const window = { start: '2026-08-07T00:00:00Z', end: '2026-08-11T23:59:59Z' };

const data = {
  generated: new Date().toISOString(),
  window,
  buildEvents,
  processEvents,
  messageVolume,
  cost,
  countingRules: [
    'buildEvent = a lake build result the agent reported in-thread (green or red), not every internal compile; job counts where stated.',
    'processEvent = a failure / recovery / pitfall the agent flagged, or an external-review catch; who-caught-it: self, human (Juni/Iris), external (Rey/Claude).',
    'messageVolume = per-day per-actor message counts from the two Lean threads; status pings excluded.',
    'cost = Hermes session telemetry (OpenRouter, Kimi K3); ESTIMATED, not provider-actual; cache-read shown separately (billed at a discount).',
  ],
  provenance: 'Anchors hand-verified against the two Lean Discord threads; every event carries the source message id. Scrubbed traces archive: see the experiment page link.',
};

writeFileSync(OUT, JSON.stringify(data, null, 2) + '\n');
console.log('wrote', OUT);
console.log(`buildEvents=${buildEvents.length} processEvents=${processEvents.length} messageVolumeDays=${messageVolume.length}`);
