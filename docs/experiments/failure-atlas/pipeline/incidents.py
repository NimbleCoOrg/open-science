#!/usr/bin/env python3
"""Stage 3: cluster raw signals into incidents.

An incident = a maximal run of signals in one session separated by no more than
GAP_LINES events AND GAP_SECONDS seconds. Each incident gets:
  - the multiset of detectors that fired, total/max score, severity
  - a primary_mode chosen by precedence (semantic detectors outrank mechanical
    ones, because a user calling out a lie IS the phenomenon while a tool error
    is only a candidate symptom)
  - a context pointer (source file + line range) so adjudicators/analysts can
    recover the full transcript window without the dataset carrying raw text

Writes `incidents` table + data/incidents.jsonl export.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import Counter

GAP_LINES = 25
GAP_SECONDS = 600

# Precedence: earlier = more semantically primary.
PRECEDENCE = [
    "honesty_challenge", "frustration_lex", "error_loop", "subagent_failure",
    "model_escalation", "stuck_repetition", "user_interrupt",
    "permission_friction", "api_error", "abandonment", "tool_error",
    "interagent_challenge", "self_correction",
    # evidence-drift candidates rank last: they inform but never outrank a
    # validated detector as an incident's primary_mode
    "bare_done_claim", "unqualified_metric_claim",
]
RANK = {d: i for i, d in enumerate(PRECEDENCE)}

SCHEMA = """
DROP TABLE IF EXISTS incidents;
CREATE TABLE incidents(
  incident_id TEXT PRIMARY KEY,
  session_key TEXT, root TEXT, project TEXT, cwd TEXT, slug TEXT,
  entrypoint TEXT, is_sidechain INTEGER, models TEXT,
  start_line INTEGER, end_line INTEGER, start_ts REAL, end_ts REAL,
  n_signals INTEGER, detectors TEXT, primary_mode TEXT,
  severity REAL, max_score REAL, source_file TEXT, evidence_sample TEXT
);
CREATE INDEX ix_inc_mode ON incidents(primary_mode);
CREATE INDEX ix_inc_session ON incidents(session_key);
"""


def severity(sigs: list[tuple]) -> float:
    """Blend of peak score and diversity: an incident where frustration,
    error loops and an interrupt co-occur is worse than one lone error."""
    max_score = max(s[3] for s in sigs)
    kinds = len({s[2] for s in sigs})
    return round(min(1.0, max_score + 0.12 * (kinds - 1) + 0.02 * min(len(sigs), 10)), 3)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="labs/failure-atlas/data/atlas.db")
    ap.add_argument("--out", default="labs/failure-atlas/data/incidents.jsonl")
    args = ap.parse_args()
    con = sqlite3.connect(args.db)
    con.executescript(SCHEMA)

    sess_meta = {r[0]: r[1:] for r in con.execute(
        "SELECT session_key, root, project, cwd, slug, entrypoint, is_sidechain, models, file "
        "FROM sessions")}

    n_inc = 0
    rows_out = []
    cur = con.execute(
        "SELECT session_key, line_no, ts, detector, score, evidence FROM signals "
        "ORDER BY session_key, line_no")
    current_sk, cluster = None, []

    def flush(sk, cluster):
        nonlocal n_inc
        if not cluster:
            return
        # drop pure-noise incidents: single low-score mechanical signal
        if len(cluster) == 1 and cluster[0][3] < 0.25 and cluster[0][2] in ("tool_error", "api_error"):
            return
        # Candidate/low-precision detectors don't form incidents ALONE — they
        # only contribute when co-occurring with a validated signal. interagent
        # _challenge (8% r1 precision) and the unvalidated evidence-drift
        # detectors are informative context, not standalone failures.
        CANDIDATE_ONLY = {"interagent_challenge", "bare_done_claim",
                          "unqualified_metric_claim"}
        if all(c[2] in CANDIDATE_ONLY for c in cluster):
            return
        root, project, cwd, slug, entrypoint, sidechain, models, file = sess_meta.get(
            sk, ("?", "?", None, None, None, 0, "", "?"))
        sigs = [(ln, ts, det, sc, ev) for (ln, ts, det, sc, ev) in cluster]
        detectors = Counter(s[2] for s in sigs)
        primary = min(detectors, key=lambda d: RANK.get(d, 99))
        n_inc += 1
        # Content-addressed id: stable across re-runs and corpus growth, so
        # adjudication labels keyed by incident_id never drift onto the wrong
        # incident. (Positional ids caused exactly that after a mid-study
        # re-ingest — see DECISIONS D9.) Keyed on the incident's location, not
        # its detector set, so a detector tweak that shifts boundaries by a line
        # still resolves to the same labeled incident via the remap tool.
        iid = "inc-" + hashlib.sha1(
            f"{sk}|{sigs[0][0]}|{sigs[-1][0]}".encode()).hexdigest()[:12]
        def load_ev(raw):
            if not raw:
                return {}
            try:
                return json.loads(raw)
            except json.JSONDecodeError:  # evidence may be truncated at store time
                return {"truncated": raw[:300]}
        ev_sample = [load_ev(s[4]) for s in sorted(sigs, key=lambda s: -s[3])[:3]]
        rows_out.append((
            iid, sk, root, project, cwd, slug, entrypoint, sidechain, models,
            sigs[0][0], sigs[-1][0], sigs[0][1], sigs[-1][1], len(sigs),
            json.dumps(dict(detectors)), primary, severity(sigs),
            max(s[3] for s in sigs), file,
            json.dumps(ev_sample, default=str)[:3000]))

    for sk, line_no, ts, det, score, ev in cur:
        if sk != current_sk:
            flush(current_sk, cluster)
            current_sk, cluster = sk, []
        if cluster:
            last_ln, last_ts = cluster[-1][0], cluster[-1][1]
            if (line_no - last_ln > GAP_LINES) or (
                    ts and last_ts and ts - last_ts > GAP_SECONDS):
                flush(sk, cluster)
                cluster = []
        cluster.append((line_no, ts, det, score, ev))
    flush(current_sk, cluster)

    con.executemany(
        "INSERT INTO incidents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows_out)
    con.commit()

    with open(args.out, "w") as f:
        cols = [d[0] for d in con.execute("SELECT * FROM incidents LIMIT 1").description]
        for row in con.execute("SELECT * FROM incidents"):
            f.write(json.dumps(dict(zip(cols, row)), default=str) + "\n")

    for mode, cnt, sev in con.execute(
            "SELECT primary_mode, COUNT(*), ROUND(AVG(severity),3) FROM incidents "
            "GROUP BY primary_mode ORDER BY 2 DESC"):
        print(f"  {mode:22s} {cnt:6d}  avg_sev={sev}")
    print(f"done: {n_inc} incidents → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
