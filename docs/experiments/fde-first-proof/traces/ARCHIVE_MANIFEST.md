# Archive manifest — FDE proof traces

**Captured:** 2026-08-11 · **By:** Matilde · **Status:** PUBLIC (scrubbed + verified)

## Contents

| File | What it is | Coverage |
|---|---|---|
| `fde-lean-proof-thread.SCRUBBED.md` | Full substantive narrative, **with tool-call texture**, scrubbed — the public version (only file shipped) | 2026-08-07 → 2026-08-11: origin/niche, soundness, completeness design + the `refutes` regression, the honest-W walkback, completeness repaired green, the degraded-channel outage, corollaries, publication, both external-review cycles |
| `scrub.py` | The deterministic redaction script (re-runnable, auditable) | — |
| `README.md` | Provenance + the redaction standard | — |
| `ARCHIVE_MANIFEST.md` | This file | — |

*Note: an un-suffixed `fde-lean-proof-thread.md` was briefly present and byte-identical to the scrubbed version; removed 2026-08-12 so the single shipped file is unambiguously the redacted one.*

## What's kept (per Juni's standard)

Names (Juni, Matilde, Iris); human steering and the funny/encouraging moments (including
"grounded tenancity"); the tool-calling problems that happened mid-proof (the stale-cache
false-green, the degraded-channel outage, the `refutes` misdiagnosis — all documented with
the recovery); tool calls where they carry the texture of the work (builds, probes,
verifications, failures).

## What's scrubbed (by `scrub.py`)

Internal paths → `<repo>`/`<tmp>`/`<home>`; Discord thread/channel/user snowflakes → `<id>`;
tokens/credential mechanics → `<token>`; device/host/port → `<host>`; Discord CDN links →
`<discord-attachment>`; bsky post rkeys dropped (handles kept). Public facts (the mathlib
rev `f566658afd`, the `umpolungfish/p4rakernel` repo) are NOT scrubbed — they're already
public and load-bearing for reproducibility.

## Coverage note

This archive now covers the **complete derivation arc** — origin/niche (Aug 7) through
soundness, the completeness design + regression, the honest-W walkback, the repair, the
degraded-channel outage, corollaries, publication, and both external reviews (Aug 11).
Sourced from the two Lean threads Juni identified (the corrupted/v1 thread and the main
FDE thread). No fMRI/birds/consciousness content — out of scope per Juni.

## Provenance statement

The proving work this thread documents was done entirely in these Discord threads between
Juni Bevensee and the Matilde agent (Hermes stack), running on **Kimi K3** (open-weight,
Moonshot AI) via OpenRouter. Claude's only role is an independent audit, relayed near the
end. External reviewers: Rey (bsky) and the artifact-auditing reviewer (relayed via Claude).
