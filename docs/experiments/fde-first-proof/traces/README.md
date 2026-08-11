# FDE Proof — Conversation Traces (public, scrubbed)

**Status: public.** The redaction pass (`scrub.py`, below) has been run and the output
verified clean. This archive shipped alongside the experiment as the durable record behind
the claim "the process is rerunnable."

These are the session transcripts for the FDE formalization work the open-science experiment
page references. They preserve the texture of the work — tool calls, builds, the failures and
recoveries — with operational detail (infra paths, IDs, tokens, hostnames) deterministically
scrubbed.

## What's here

- `fde-lean-proof-thread.SCRUBBED.md` — the complete "FDE LEAN Proof" record
  (Cyborg.Garden #open-science), covering the completeness assembly, corollaries, both
  external-review cycles, and the repo/publication work. This is the public, scrubbed file
  (the `.SCRUBBED` suffix marks it as the redacted version — the only one shipped).
- `ARCHIVE_MANIFEST.md` — what was captured, from where, when, and the redaction standard.
- `scrub.py` — the deterministic redaction script, so the scrub is auditable and re-runnable.

## Provenance

Captured 2026-08-11 by the Matilde agent from the Discord channel history.
The proving work was done entirely in these Discord threads between Juni Bevensee and the
Matilde agent, running on **Kimi K3** (open-weight, Moonshot AI) via OpenRouter. Iris appears
as a supporting agent (comms/encouragement), not as a prover. Claude's only role in the
project is an independent audit, relayed near the end.

**Coverage:** the complete derivation arc — origin/niche search (Aug 7), soundness,
completeness (design, the `refutes` regression, the honest-W walkback, the repair), the
degraded-channel outage, corollaries (Aug 9–10), publication, and both external-review
cycles (Aug 10–11). Sourced from the two Lean threads (the corrupted/v1 thread and the main
FDE thread).

## Redaction standard (per Juni, 2026-08-11) — applied

The scrub has been run and verified. The standard it applied:

KEEP — these are part of the honest record:
- Names: Juni and Matilde are fine to appear.
- Human steering and our interactions, including the encouraging/funny moments.
- The tool-calling problems that happened mid-proof — that's useful, realistic context.

STRIPPED before publication — anything vulnerable or personal:
- Port numbers, device names, internal links / hostnames.
- Private repo references that aren't meant to be public.
- The Discord thread / channel IDs and the Discord link itself.
- Any keys, tokens, or credential mechanics.
- User IDs / snowflakes.
- Internal filesystem paths (→ `<repo>` etc.) — genericized.
