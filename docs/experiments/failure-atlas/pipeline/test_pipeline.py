#!/usr/bin/env python3
"""End-to-end smoke test on a synthetic transcript fixture.

Builds a fake Claude config root with one session containing known failure
patterns, runs extract → detectors → incidents, and asserts each expected
signal is found and each known confound is NOT flagged. Run:
    python3 pipeline/test_pipeline.py
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def make_fixture(root: Path) -> None:
    proj = root / "projects" / "-tmp-demo"
    proj.mkdir(parents=True)
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

    def ts(i):
        return (t0 + timedelta(seconds=20 * i)).isoformat().replace("+00:00", "Z")

    lines = []
    i = 0

    def add(o):
        nonlocal i
        o.setdefault("timestamp", ts(i))
        o.setdefault("sessionId", "s1")
        o.setdefault("uuid", f"u{i}")
        o.setdefault("cwd", "/tmp/demo")
        i += 1
        lines.append(o)

    def user(text, sidechain=False):
        add({"type": "user", "isSidechain": sidechain,
             "message": {"role": "user", "content": text}})

    def asst(blocks, model="claude-haiku-4-5-20251001", sidechain=False):
        add({"type": "assistant", "isSidechain": sidechain,
             "message": {"role": "assistant", "model": model, "content": blocks}})

    def tool_err(text):
        add({"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": f"t{i}", "is_error": True,
             "content": text}]}})

    # benign start
    user("please fix the login bug")
    asst([{"type": "text", "text": "Sure, looking."}])
    # error loop: 3 bash failures
    for _ in range(3):
        asst([{"type": "tool_use", "id": f"t{i}", "name": "Bash",
               "input": {"command": "npm test"}}])
        tool_err("Exit code 1\nFAIL tests/login.test.js")
    # frustration + honesty challenge (human, non-sidechain)
    user("NO. you keep doing the same thing — did you actually read the test file? you made that up")
    # self-correction
    asst([{"type": "text", "text": "You're right, I apologize — I misread the fixture."}])
    # interrupt
    user("[Request interrupted by user for tool use]")
    # escalation to bigger model
    asst([{"type": "text", "text": "resuming with more capability"}], model="claude-opus-5")
    # sidechain orchestrator prompt must NOT be human frustration/honesty
    user("Adversarially verify this claim: did you actually check X? refute if wrong",
         sidechain=True)
    asst([{"type": "text", "text": "sidechain working"}], sidechain=True)
    # continuation-summary echo must NOT fire detectors
    user("Caveat: the messages below were generated during a prior session. wtf you lied")
    # long quiet stretch (> cluster gap) so the tail forms a second incident
    for _ in range(30):
        asst([{"type": "text", "text": "working..."}])
    tool_err("Exit code 128\nfatal: repository not found")

    with open(proj / "s1.jsonl", "w") as f:
        for o in lines:
            f.write(json.dumps(o) + "\n")


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "fakeclaude"
        make_fixture(root)
        db = Path(td) / "atlas.db"
        for cmd in (
            [sys.executable, HERE / "extract.py", "--roots", str(root), "--db", db],
            [sys.executable, HERE / "detectors.py", "--db", db],
            [sys.executable, HERE / "incidents.py", "--db", db,
             "--out", Path(td) / "inc.jsonl"],
        ):
            r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
            if r.returncode != 0:
                print(r.stdout, r.stderr)
                print(f"FAIL: {cmd}")
                return 1
        con = sqlite3.connect(db)
        dets = {d for (d,) in con.execute("SELECT DISTINCT detector FROM signals")}
        expected = {"tool_error", "error_loop", "frustration_lex", "honesty_challenge",
                    "self_correction", "user_interrupt", "model_escalation",
                    "abandonment", "interagent_challenge"}
        missing = expected - dets
        ok = True
        if missing:
            print(f"FAIL missing detectors: {missing}")
            ok = False
        # confound checks: no human-frustration signal on sidechain or Caveat lines
        for det in ("frustration_lex", "honesty_challenge"):
            for (ln,) in con.execute(
                    "SELECT line_no FROM signals WHERE detector=?", (det,)):
                ev = con.execute(
                    "SELECT is_sidechain, text FROM events WHERE line_no=? AND session_key LIKE '%s1%'",
                    (ln,)).fetchone()
                if ev and (ev[0] or (ev[1] or "").startswith("Caveat:")):
                    print(f"FAIL {det} fired on sidechain/echo at line {ln}")
                    ok = False
        n_inc = con.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
        if n_inc < 2:
            print(f"FAIL expected >=2 incidents, got {n_inc}")
            ok = False
        print(("PASS" if ok else "FAIL") + f": detectors={sorted(dets)} incidents={n_inc}")
        return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
