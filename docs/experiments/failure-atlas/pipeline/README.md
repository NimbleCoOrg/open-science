# Failure Atlas

Mine your own Claude Code logs for agent–human interaction failures; share
the statistics, never the data.

## What it does

1. **extract** — parses every session transcript under your Claude config
   roots (`~/.claude`, `~/.claude-*`) into a local SQLite event store.
2. **detect** — runs 13 high-recall failure detectors (tool errors, error
   loops, user frustration, honesty challenges, model escalations, subagent
   failures, …). Heuristics are candidates, not verdicts.
3. **incidents** — clusters signals into incidents with severity, a primary
   failure mode, and pointers back to the source transcript.
4. **analyze** — produces `analysis.json`: aggregate rates, co-occurrence,
   position-in-session, outcome distributions. **No transcript text.**
5. **adjudicate** (optional, LLM) — samples incidents per mode, renders full
   context windows (`context_window.py`), and estimates detector precision +
   root causes + preventability.
6. **augment** — turns confirmed, avoidable failure clusters into targeted
   Claude Code countermeasures (hooks/memory), not CLAUDE.md bloat.

## Run

```bash
python3 pipeline/extract.py            # → data/atlas.db
python3 pipeline/detectors.py
python3 pipeline/incidents.py          # → data/incidents.jsonl
python3 pipeline/analyze.py            # → data/analysis.json (shareable layer)
```

Zero dependencies beyond Python 3.9 stdlib. Everything under `data/` is
gitignored; the only artifact designed to leave your machine is
`analysis.json`, and you choose when.

## Privacy model

Raw transcripts stay where they are; the store keeps truncated text needed for
detection plus `(file, line)` pointers; the shareable layer is counts and
rates only. Pooling installations means pooling `analysis.json` files —
OMOP-style: common schema, local data, shared statistics.
