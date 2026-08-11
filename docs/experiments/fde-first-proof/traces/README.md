# FDE Proof — Conversation Traces (LOCAL ONLY)

**Status: private working archive. Do NOT commit to any public repo until Juni has done a redaction pass ("alembic clean").**

These are the raw session transcripts for the FDE formalization work that the
open-science experiment page references. They are the durable record behind the
claim "the process is rerunnable" — but they contain operational detail (tool
calls, internal reasoning, infra paths, auth-mechanics references) that must be
reviewed before any public release.

## What's here

- `fde-lean-proof-thread.md` — the main "FDE LEAN Proof" Discord thread
  (Cyborg.Garden #open-science, thread `<id>`), covering the
  completeness assembly, corollaries, both external-review cycles, and the
  repo/publication work.
- `ARCHIVE_MANIFEST.md` — what was captured, from where, when, and what's still
  missing.

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

## Redaction standard (per Juni, 2026-08-11)

KEEP — these are part of the honest record:
- Names: Juni and Matilde are fine to appear.
- Human steering and our interactions, including the encouraging/funny moments.
- The tool-calling problems that happened mid-proof — that's useful, realistic context.

STRIP before any public release — anything vulnerable or personal:
- Port numbers, device names, internal links / hostnames.
- Private repo references that aren't meant to be public.
- The Discord thread / channel IDs and the Discord link itself.
- Any keys, tokens, or credential mechanics.
- User IDs / snowflakes.
- Internal filesystem paths (`<repo>`) — genericize.
