#!/usr/bin/env python3
"""Render a human-readable transcript window around an incident.

Usage:
  python3 context_window.py --db data/atlas.db --incident inc-000123 [--pad 15]
  python3 context_window.py --db data/atlas.db --list-sample 12   # stratified sample ids

Reads the ORIGINAL jsonl (via the incident's source pointer), so adjudicators
see full text, not the truncated store. Output is plain text with roles,
timestamps, tool names, and >>> markers on the lines where signals fired.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT_BASES = {
    ".claude": Path.home() / ".claude",
    # Add additional config roots here if you run multiple Claude Code
    # profiles, e.g. ".claude-work": Path.home() / ".claude-work",
}


def render_line(o: dict, marked: bool) -> str:
    mark = ">>> " if marked else "    "
    t = o.get("type")
    msg = o.get("message") if isinstance(o.get("message"), dict) else {}
    role = msg.get("role") or t
    bits = []
    content = msg.get("content")
    if isinstance(content, str):
        bits.append(content)
    elif isinstance(content, list):
        for b in content:
            if not isinstance(b, dict):
                continue
            bt = b.get("type")
            if bt == "text":
                bits.append(b.get("text") or "")
            elif bt == "thinking":
                bits.append(f"[thinking {len(b.get('thinking') or '')} chars]")
            elif bt == "tool_use":
                bits.append(f"[tool_use {b.get('name')}] "
                            + json.dumps(b.get("input"), default=str)[:600])
            elif bt == "tool_result":
                c = b.get("content")
                txt = c if isinstance(c, str) else json.dumps(c, default=str)
                flag = " ERROR" if b.get("is_error") else ""
                bits.append(f"[tool_result{flag}] {txt[:800]}")
    body = "\n".join(x for x in bits if x).strip()
    if len(body) > 2400:
        body = body[:2400] + f"\n…[{len(body)-2400} chars truncated]"
    model = msg.get("model")
    head = f"{mark}#{o.get('_line')} {role}{' (' + model + ')' if model else ''}"
    if o.get("isSidechain"):
        head += " [sidechain]"
    body_ind = body.replace("\n", "\n      ") if body else "(no visible content)"
    return f"{head}:\n      {body_ind}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="labs/failure-atlas/data/atlas.db")
    ap.add_argument("--incident")
    ap.add_argument("--pad", type=int, default=15)
    ap.add_argument("--list-sample", type=int, default=0,
                    help="print a stratified sample of incident ids (N per mode)")
    args = ap.parse_args()
    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row

    if args.list_sample:
        for (mode,) in con.execute(
                "SELECT DISTINCT primary_mode FROM incidents"):
            rows = con.execute(
                # deterministic pseudo-random: hash of id; severity-diverse
                "SELECT incident_id, severity FROM incidents WHERE primary_mode=? "
                "ORDER BY (CAST(substr(incident_id,5) AS INTEGER) * 2654435761) % 4294967296 "
                "LIMIT ?", (mode, args.list_sample)).fetchall()
            for r in rows:
                print(f"{mode}\t{r['incident_id']}\t{r['severity']}")
        return 0

    inc = con.execute("SELECT * FROM incidents WHERE incident_id=?",
                      (args.incident,)).fetchone()
    if not inc:
        print(f"no such incident {args.incident}", file=sys.stderr)
        return 1
    base = ROOT_BASES.get(inc["root"])
    src = base / inc["source_file"] if base else None  # source_file includes projects/
    if not src or not src.exists():
        print(f"source missing: {src}", file=sys.stderr)
        return 1
    lo = max(1, inc["start_line"] - args.pad)
    hi = inc["end_line"] + args.pad
    sig_lines = {r["line_no"] for r in con.execute(
        "SELECT line_no FROM signals WHERE session_key=? AND line_no BETWEEN ? AND ?",
        (inc["session_key"], inc["start_line"], inc["end_line"]))}

    print(f"=== {inc['incident_id']} mode={inc['primary_mode']} sev={inc['severity']} "
          f"detectors={inc['detectors']}")
    print(f"=== session={inc['session_key']} lines {lo}-{hi} "
          f"(signal lines marked >>>)\n")
    with open(src, errors="replace") as fh:
        for ln, line in enumerate(fh, 1):
            if ln < lo:
                continue
            if ln > hi:
                break
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                continue
            if o.get("type") in ("progress", "file-history-snapshot", "queue-operation"):
                continue
            o["_line"] = ln
            print(render_line(o, ln in sig_lines))
            print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
