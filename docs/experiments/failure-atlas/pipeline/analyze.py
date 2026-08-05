#!/usr/bin/env python3
"""Stage 4: analyses over the incident dataset.

Produces:
  data/analysis.json  — aggregate statistics ONLY (no transcript text): this is
                        the share-results-not-data layer
  data/FINDINGS-draft.md — human-readable draft (exemplar pointers, no raw text)

Analyses:
  A. corpus overview                     E. position-in-session of failures
  B. incident rates by mode/root/kind    F. detector co-occurrence
  C. project-category failure mix        G. incident outcomes (what happened next)
  D. model-tier analysis                 H. exemplars (pointers only)
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

# EDIT ME: map your own projects to categories. These are example rules —
# replace the patterns with your repo/project names so the category-mix
# analysis reflects your work. Matching is on project + cwd, first rule wins.
CATEGORY_RULES = [
    ("infra", re.compile(r"infra|platform|backend|api|pipeline", re.I)),
    ("web", re.compile(r"site|web|frontend|ui|landing", re.I)),
    ("experiments", re.compile(r"tmp|scratch|probe|test|sandbox", re.I)),
]


def categorize(project: str | None, cwd: str | None) -> str:
    s = f"{project or ''} {cwd or ''}"
    for name, rx in CATEGORY_RULES:
        if rx.search(s):
            return name
    return "other"


def tier_of(models: str) -> int:
    t = 0
    for m in (models or "").split(","):
        if "haiku" in m: t = max(t, 1)
        elif "sonnet" in m: t = max(t, 2)
        elif "opus" in m: t = max(t, 3)
        elif "fable" in m or "mythos" in m: t = max(t, 4)
    return t


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="labs/failure-atlas/data/atlas.db")
    ap.add_argument("--outdir", default="labs/failure-atlas/data")
    args = ap.parse_args()
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    out: dict = {"generated_at": datetime.now(timezone.utc).isoformat()}

    # A. corpus overview
    out["corpus"] = {
        r["root"]: {"sessions": r["n"], "events": r["ev"], "sidechains": r["sc"],
                    "first": r["t0"], "last": r["t1"]}
        for r in con.execute("""
            SELECT root, COUNT(*) n, SUM(n_events) ev, SUM(is_sidechain) sc,
                   MIN(start_ts) t0, MAX(end_ts) t1
            FROM sessions GROUP BY root""")}

    # B. incident rates
    total_events = con.execute("SELECT SUM(n_events) FROM sessions").fetchone()[0]
    out["incidents_by_mode"] = {}
    for r in con.execute("""
        SELECT primary_mode, COUNT(*) n, AVG(severity) sev,
               SUM(is_sidechain) side FROM incidents GROUP BY primary_mode"""):
        out["incidents_by_mode"][r["primary_mode"]] = {
            "count": r["n"], "avg_severity": round(r["sev"], 3),
            "share_sidechain": round((r["side"] or 0) / r["n"], 3),
            "per_10k_events": round(r["n"] / total_events * 10000, 2)}

    # C. project-category failure mix
    mix = defaultdict(Counter)
    sess_events = defaultdict(int)
    for r in con.execute("SELECT project, cwd, n_events FROM sessions"):
        sess_events[categorize(r["project"], r["cwd"])] += r["n_events"] or 0
    for r in con.execute("SELECT project, cwd, primary_mode FROM incidents"):
        mix[categorize(r["project"], r["cwd"])][r["primary_mode"]] += 1
    out["category_mix"] = {
        cat: {"events": sess_events.get(cat, 0),
              "incidents": dict(c),
              "incidents_per_10k_events": round(
                  sum(c.values()) / max(1, sess_events.get(cat, 1)) * 10000, 2)}
        for cat, c in mix.items()}

    # D. model-tier analysis: incident density of sessions whose max tier is T
    tier_events, tier_inc = Counter(), Counter()
    sess_tier = {}
    for r in con.execute("SELECT session_key, models, n_events FROM sessions"):
        t = tier_of(r["models"])
        sess_tier[r["session_key"]] = t
        tier_events[t] += r["n_events"] or 0
    for r in con.execute("SELECT session_key, primary_mode FROM incidents"):
        tier_inc[sess_tier.get(r["session_key"], 0)] += 1
    out["by_model_tier"] = {
        str(t): {"events": tier_events[t], "incidents": tier_inc[t],
                 "per_10k_events": round(tier_inc[t] / max(1, tier_events[t]) * 10000, 2)}
        for t in sorted(set(tier_events) | set(tier_inc))}
    out["escalations"] = [dict(r) for r in con.execute(
        "SELECT session_key, evidence_sample FROM incidents "
        "WHERE primary_mode='model_escalation'")]
    # strip evidence to scope+models only
    for e in out["escalations"]:
        try:
            evs = json.loads(e.pop("evidence_sample"))
            e["evidence"] = [{k: v for k, v in ev.items()
                              if k in ("scope", "from_model", "to_model", "from_tier",
                                       "to_tier", "after_failure", "gap_s")} for ev in evs]
        except (json.JSONDecodeError, TypeError):
            e["evidence"] = "unparsed"

    # E. where in the session do failures happen (normalized position deciles)
    pos = defaultdict(Counter)
    n_ev = {r["session_key"]: r["n_events"] for r in
            con.execute("SELECT session_key, n_events FROM sessions")}
    for r in con.execute("SELECT session_key, primary_mode, start_line FROM incidents"):
        ne = n_ev.get(r["session_key"]) or 0
        if ne > 20:
            decile = min(9, int(r["start_line"] / ne * 10))
            pos[r["primary_mode"]][decile] += 1
    out["position_deciles"] = {m: [c.get(d, 0) for d in range(10)] for m, c in pos.items()}

    # F. detector co-occurrence within incidents
    co = Counter()
    for r in con.execute("SELECT detectors FROM incidents WHERE n_signals > 1"):
        dets = sorted(json.loads(r["detectors"]))
        for i, a in enumerate(dets):
            for b in dets[i + 1:]:
                co[f"{a}+{b}"] += 1
    out["cooccurrence_top"] = dict(co.most_common(25))

    # G. outcomes: for each non-tail incident, what appears in the next 30 events?
    outcomes = defaultdict(Counter)
    inc_by_sess = defaultdict(list)
    for r in con.execute(
            "SELECT session_key, primary_mode, end_line FROM incidents"):
        inc_by_sess[r["session_key"]].append((r["end_line"], r["primary_mode"]))
    sig_by_sess = defaultdict(list)
    for r in con.execute("SELECT session_key, line_no, detector FROM signals"):
        sig_by_sess[r["session_key"]].append((r["line_no"], r["detector"]))
    for sk, incs in inc_by_sess.items():
        sigs = sorted(sig_by_sess.get(sk, []))
        ne = n_ev.get(sk) or 0
        for end_line, mode in incs:
            if ne and end_line >= ne - 5:
                outcomes[mode]["session_end"] += 1
                continue
            window = [d for (ln, d) in sigs if end_line < ln <= end_line + 30]
            if not window:
                outcomes[mode]["recovered_clean"] += 1
            elif "self_correction" in window:
                outcomes[mode]["self_corrected"] += 1
            elif "model_escalation" in window:
                outcomes[mode]["escalated"] += 1
            else:
                outcomes[mode]["further_failures"] += 1
    out["outcomes"] = {m: dict(c) for m, c in outcomes.items()}

    # H. exemplars: top severity per mode, pointers only
    out["exemplars"] = {}
    for mode in out["incidents_by_mode"]:
        rows = con.execute(
            "SELECT incident_id, session_key, root, source_file, start_line, end_line, "
            "severity FROM incidents WHERE primary_mode=? ORDER BY severity DESC, "
            "n_signals DESC LIMIT 5", (mode,)).fetchall()
        out["exemplars"][mode] = [dict(r) for r in rows]

    outdir = args.outdir
    with open(f"{outdir}/analysis.json", "w") as f:
        json.dump(out, f, indent=1, default=str)

    # draft report (numbers only; interpretation happens downstream)
    with open(f"{outdir}/FINDINGS-draft.md", "w") as f:
        f.write("# Failure Atlas — draft aggregates (machine-generated)\n\n")
        f.write(f"Corpus: {json.dumps(out['corpus'], indent=1, default=str)}\n\n")
        f.write("## Incidents by mode\n\n|mode|n|avg sev|/10k events|sidechain share|\n|-|-|-|-|-|\n")
        for m, d in sorted(out["incidents_by_mode"].items(), key=lambda kv: -kv[1]["count"]):
            f.write(f"|{m}|{d['count']}|{d['avg_severity']}|{d['per_10k_events']}|{d['share_sidechain']}|\n")
        f.write("\n## Category mix (incidents per 10k events)\n\n")
        for cat, d in sorted(out["category_mix"].items()):
            f.write(f"- **{cat}**: {d['incidents_per_10k_events']}/10k over {d['events']} events — {json.dumps(d['incidents'])}\n")
        f.write("\n## By max model tier in session\n\n")
        f.write(json.dumps(out["by_model_tier"], indent=1) + "\n")
        f.write("\n## Outcome distribution after incident\n\n")
        f.write(json.dumps(out["outcomes"], indent=1) + "\n")
        f.write("\n## Top co-occurrences\n\n")
        f.write(json.dumps(out["cooccurrence_top"], indent=1) + "\n")
        f.write("\n## Position deciles (start→end of session)\n\n")
        f.write(json.dumps(out["position_deciles"], indent=1) + "\n")
    print(f"wrote {outdir}/analysis.json and {outdir}/FINDINGS-draft.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
