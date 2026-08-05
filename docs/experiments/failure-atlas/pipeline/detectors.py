#!/usr/bin/env python3
"""Stage 2: run failure-signal detectors over the event store.

Writes a `signals` table: one row per (event, detector) hit with a score in
[0,1] and a JSON evidence payload. Detectors are deliberately HIGH-RECALL,
LOW-PRECISION candidates — stage 3 clusters them into incidents and stage 4
(LLM adjudication on samples) estimates each detector's precision instead of
trusting it. Nothing here is treated as ground truth.

Detector registry (id → what it flags → known confounds):
  tool_error          tool_result.is_error=1, categorized     TDD red phases, grep misses
  error_loop          ≥3 errors, same tool, tight window      long legitimate debug loops
  stuck_repetition    ≥3 identical tool calls                 polling loops (sleep/status)
  user_interrupt      [Request interrupted by user...]        benign redirections
  frustration_lex     lexical frustration in user text        quoting someone else's anger
  honesty_challenge   user challenges a factual claim         genuine questions, curiosity
  self_correction     assistant admits error                  politeness without real error
  api_error           harness/API failures                    infra noise, not agent fault
  permission_friction rejected/denied/hook-blocked calls      deliberate guardrails working
  model_escalation    bigger model appears after failures     routine model switching
  subagent_failure    sidechain ends in error state           expected negative results
  abandonment         session ends amid unresolved errors     user just left for dinner
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from collections import defaultdict

MODEL_TIER = [
    (re.compile(r"haiku"), 1),
    (re.compile(r"sonnet"), 2),
    (re.compile(r"opus"), 3),
    (re.compile(r"fable|mythos"), 4),
]


def model_tier(model: str | None) -> int:
    if not model:
        return 0
    for rx, t in MODEL_TIER:
        if rx.search(model):
            return t
    return 0


# --- lexical resources -------------------------------------------------------
FRUST_STRONG = [
    r"\bwtf\b", r"\bffs\b", r"\bfuck", r"\bjfc\b", r"goddamn", r"god damn",
    r"\bstop\b.{0,15}\bstop\b", r"you'?re not listening", r"i already (said|told)",
    r"i told you", r"you ignored", r"read what i", r"why (are|do) you keep",
    r"you keep (doing|making|ignoring)", r"how many times", r"\bugh+\b", r"\bargh+\b",
    r"for the last time", r"literally just", r"did you even",
]
FRUST_MEDIUM = [
    r"^no[.!,]? ", r"\bnot what i (asked|meant|wanted)", r"that'?s (not|still) (right|correct|it|what)",
    r"still (broken|failing|wrong|not working)", r"doesn'?t work", r"\bwrong\b",
    r"\brevert\b", r"\bundo\b", r"as i said", r"\bagain\b[.!?]*$", r"you didn'?t",
    r"^why did you", r"i said\b", r"\bno\b[.!]{2,}",
]
# Accusatory challenges only — generic verification requests ("are you sure",
# "show me", "verify") measured 25% precision in round-1 adjudication because
# they are usually genuine questions, so they were removed.
HONESTY = [
    r"did you actually", r"you didn'?t actually", r"\blied?\b", r"\blying\b",
    r"made (that|this|it) up", r"hallucinat", r"doesn'?t (even )?exist",
    r"that'?s not (true|real)", r"you (claimed|said) .{0,40}but", r"fabricat",
    r"that (file|function|api|method) (isn'?t|is not|doesn'?t)",
]
SELF_CORRECT = [
    r"you'?re (absolutely )?right", r"i apologi[sz]e", r"my mistake", r"i was wrong",
    r"i misread", r"i incorrectly", r"i made an error", r"i should have",
    r"i fabricated", r"i misspoke", r"correction[:,]", r"i claimed .{0,60}(but|however)",
    r"that was (wrong|incorrect|a mistake)", r"i hallucin",
]
REJECTION_RX = [
    r"user doesn'?t want to proceed", r"user rejected", r"permission .{0,30}denied",
    r"hook (error|blocked)", r"PreToolUse:.*(error|block)", r"boundary consent needed",
    r"protected branch",
]
ERROR_CATEGORIES = [
    ("user_rejected", re.compile(r"user doesn'?t want to proceed|user rejected", re.I)),
    ("permission_denied", re.compile(r"permission.{0,30}denied|not allowed", re.I)),
    ("hook_block", re.compile(r"hook (error|blocked)|PreToolUse|boundary consent|protected branch", re.I)),
    ("timeout", re.compile(r"timed? ?out", re.I)),
    ("not_found", re.compile(r"(no such file|not found|does not exist|command not found|ENOENT)", re.I)),
    ("edit_mismatch", re.compile(r"(old_string|string to replace|not.{0,20}unique|has not been read|does not match)", re.I)),
    ("network", re.compile(r"(ECONNREFUSED|ETIMEDOUT|network|fetch failed|ENOTFOUND|rate limit|429|529)", re.I)),
    ("interrupt", re.compile(r"request interrupted", re.I)),
    ("exit_nonzero", re.compile(r"^exit code \d+", re.I)),
]

FRUST_STRONG_RX = [re.compile(p, re.I | re.M) for p in FRUST_STRONG]
FRUST_MEDIUM_RX = [re.compile(p, re.I | re.M) for p in FRUST_MEDIUM]
HONESTY_RX = [re.compile(p, re.I) for p in HONESTY]
SELF_CORRECT_RX = [re.compile(p, re.I) for p in SELF_CORRECT]
REJECT_RX = [re.compile(p, re.I) for p in REJECTION_RX]

SCHEMA = """
CREATE TABLE IF NOT EXISTS signals(
  session_key TEXT, line_no INTEGER, ts REAL,
  detector TEXT, score REAL, evidence TEXT,
  PRIMARY KEY(session_key, line_no, detector)
);
CREATE INDEX IF NOT EXISTS ix_sig_session ON signals(session_key);
CREATE INDEX IF NOT EXISTS ix_sig_det ON signals(detector);
"""


def categorize_error(text: str) -> str:
    for name, rx in ERROR_CATEGORIES:
        if rx.search(text or ""):
            return name
    return "other"


def lex_hits(text: str, rxs) -> list[str]:
    return [rx.pattern for rx in rxs if rx.search(text)]


def caps_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 12:
        return 0.0
    return sum(1 for c in letters if c.isupper()) / len(letters)


def detect_session(rows: list[dict], out: list[dict]) -> None:
    """Run all per-session detectors. rows are events ordered by line_no."""
    sk = rows[0]["session_key"]

    def emit(r, detector, score, **evidence):
        out.append(dict(session_key=sk, line_no=r["line_no"], ts=r["ts"],
                        detector=detector, score=round(min(1.0, score), 3),
                        evidence=json.dumps(evidence, default=str)[:2000]))

    # -- pass 1: per-event lexical/flag detectors
    err_seq = []          # rolling (idx, category) of tool errors
    tool_calls = defaultdict(list)  # (tool, input) -> idxs
    interrupts = []
    for i, r in enumerate(rows):
        text = r["text"] or ""
        role = r["role"]
        if r["is_error"]:
            cat = categorize_error(text)
            base = {"user_rejected": 0.6, "permission_denied": 0.5, "hook_block": 0.4,
                    "interrupt": 0.5}.get(cat, 0.2)
            emit(r, "tool_error", base, category=cat, preview=text[:200])
            err_seq.append((i, cat))
            if any(rx.search(text) for rx in REJECT_RX):
                emit(r, "permission_friction", 0.5, category=cat, preview=text[:160])
        if r["api_error"]:
            emit(r, "api_error", 0.3, status=r["api_error"])
        if r["tool_name"] and r["tool_input"]:
            tool_calls[(r["tool_name"], r["tool_input"])].append(i)

        if role == "user" and text and not r["tool_use_id"]:
            # Sidechain "user" turns are orchestrator prompts, not a human:
            # route them to interagent_challenge instead of human detectors.
            if r["is_sidechain"]:
                hon = lex_hits(text, HONESTY_RX)
                if hon:
                    emit(r, "interagent_challenge", 0.2, markers=hon[:4],
                         preview=text[:160])
                continue
            # Continuation summaries and command transcripts quote old text and
            # trip lexical detectors falsely — skip them.
            if (text.startswith("Caveat:") or "<command-name>" in text[:80]
                    or "This session is being continued" in text[:120]
                    or text.startswith("<local-command")):
                continue
            if "[Request interrupted" in text:
                interrupts.append(i)
                emit(r, "user_interrupt", 0.4,
                     kind="tool" if "for tool use" in text else "plain")
            strong = lex_hits(text, FRUST_STRONG_RX)
            medium = lex_hits(text, FRUST_MEDIUM_RX)
            cr = caps_ratio(text)
            score = 0.45 * min(len(strong), 2) + 0.15 * min(len(medium), 3) + (0.3 if cr > 0.6 else 0)
            if score >= 0.15:
                emit(r, "frustration_lex", score, strong=strong[:4], medium=medium[:4],
                     caps=round(cr, 2), preview=text[:200])
            hon = lex_hits(text, HONESTY_RX)
            if hon:
                emit(r, "honesty_challenge", 0.3 + 0.2 * min(len(hon), 2),
                     markers=hon[:4], preview=text[:200])
        if role == "assistant" and text:
            sc = lex_hits(text, SELF_CORRECT_RX)
            if sc:
                emit(r, "self_correction", 0.25 + 0.15 * min(len(sc), 3),
                     markers=sc[:4], preview=text[:200])

    # -- pass 2: sequences
    # error loops: runs of errors within a sliding window of 12 events
    run = []
    for idx, cat in err_seq:
        if run and idx - run[-1][0] > 12:
            run = []
        run.append((idx, cat))
        if len(run) in (3, 5, 8):
            r = rows[idx]
            emit(r, "error_loop", 0.35 + 0.1 * len(run),
                 run_len=len(run), categories=[c for _, c in run[-8:]])

    # stuck repetition: identical (tool, input) ≥3 times
    for (tool, tin), idxs in tool_calls.items():
        if len(idxs) >= 3 and tool not in ("TaskList", "TaskOutput", "Monitor"):
            # ignore obvious polling (calls spaced > 60s apart on average)
            ts0, ts1 = rows[idxs[0]]["ts"], rows[idxs[-1]]["ts"]
            spacing = ((ts1 - ts0) / max(1, len(idxs) - 1)) if ts0 and ts1 else 0
            if spacing < 60:
                r = rows[idxs[-1]]
                emit(r, "stuck_repetition", 0.3 + 0.1 * min(len(idxs), 5),
                     tool=tool, times=len(idxs), input_preview=tin[:120])

    # In-session model escalation. Round-1 adjudication: routine opus↔fable
    # runtime swaps measured 17% precision, so only low→high jumps (haiku/
    # sonnet → opus/fable) after a failure signal count as escalation.
    tiers = [(i, model_tier(r["model"])) for i, r in enumerate(rows) if r["model"]]
    seen_fail_before = {s["line_no"] for s in out
                        if s["detector"] in ("tool_error", "error_loop", "frustration_lex")}
    for (i1, t1), (i2, t2) in zip(tiers, tiers[1:]):
        if t2 >= 3 and 0 < t1 <= 2:
            had_fail = any(rows[j]["line_no"] in seen_fail_before for j in range(0, i2))
            if not had_fail:
                continue
            r = rows[i2]
            emit(r, "model_escalation", 0.5,
                 from_model=rows[i1]["model"], to_model=r["model"],
                 after_failure=True, scope="in_session")

    # Abandonment. Round-1 adjudication: 8% precision — the tail was full of
    # trailing metadata records (last-prompt, permission-mode, pr-link) so any
    # session with an old error looked abandoned, and clean closes (handoff
    # sent, summary written) were flagged. Now: consider only CONTENT events;
    # require the final content event to be an error/frustrated user message;
    # and treat a substantive assistant message after the last error as a
    # close-out, not abandonment.
    content = [r for r in rows
               if r["role"] in ("user", "assistant")
               and ((r["text_len"] or 0) > 0 or r["is_error"] or r["tool_name"])]
    if len(content) > 10 and not rows[0]["is_sidechain"]:
        tail = content[-3:]
        tail_lines = {r["line_no"] for r in tail}
        tail_sigs = [s for s in out if s["line_no"] in tail_lines
                     and s["detector"] in ("tool_error", "error_loop",
                                            "frustration_lex", "api_error",
                                            "user_interrupt")]
        last = content[-1]
        ends_on_failure = bool(last["is_error"]) or any(
            s["line_no"] == last["line_no"] for s in tail_sigs)
        closing_text_after = (last["role"] == "assistant" and not last["is_error"]
                              and (last["text_len"] or 0) >= 200)
        if tail_sigs and ends_on_failure and not closing_text_after:
            emit(rows[-1], "abandonment", 0.3 + 0.1 * len(tail_sigs),
                 tail_detectors=[s["detector"] for s in tail_sigs])


def detect_subagent_failures(con: sqlite3.Connection, out: list[dict]) -> None:
    """Sidechain sessions that END on an error → subagent_failure.

    Round-1 adjudication (17% precision) showed most flags were sidechains
    with a benign error somewhere near the end but a substantive assistant
    answer after it. Now the error must be at the last event, or be followed
    only by empty/metadata rows."""
    q = """
    SELECT s.session_key, s.agent_id, e.line_no, e.ts, e.text
    FROM sessions s JOIN events e ON e.session_key = s.session_key
    WHERE s.is_sidechain = 1 AND e.is_error = 1
      AND NOT EXISTS (
        SELECT 1 FROM events e2 WHERE e2.session_key = e.session_key
          AND e2.line_no > e.line_no
          AND (e2.text_len > 50 OR e2.tool_name IS NOT NULL))
    """
    for sk, agent_id, line_no, ts, text in con.execute(q):
        out.append(dict(session_key=sk, line_no=line_no, ts=ts,
                        detector="subagent_failure", score=0.5,
                        evidence=json.dumps({"agent_id": agent_id,
                                             "preview": (text or "")[:200]})))


def detect_cross_session_escalation(con: sqlite3.Connection, out: list[dict]) -> None:
    """Session ends with failure signals; within 2h a session starts in the same
    cwd on a strictly higher model tier → cross-session escalation candidate."""
    rows = con.execute("""
        SELECT session_key, cwd, start_ts, end_ts, models FROM sessions
        WHERE is_sidechain = 0 AND cwd IS NOT NULL AND start_ts IS NOT NULL
        ORDER BY cwd, start_ts""").fetchall()
    fail_sessions = {sk for (sk,) in con.execute(
        "SELECT DISTINCT session_key FROM signals WHERE detector IN "
        "('error_loop','frustration_lex','abandonment','tool_error')")}
    by_cwd = defaultdict(list)
    for sk, cwd, st, en, models in rows:
        tier = max((model_tier(m) for m in (models or "").split(",")), default=0)
        by_cwd[cwd].append((sk, st, en or st, tier))
    for cwd, sess in by_cwd.items():
        for (ska, sta, ena, ta), (skb, stb, enb, tb) in zip(sess, sess[1:]):
            # low→high jumps only; opus↔fable flapping is runtime noise
            if tb >= 3 and 0 < ta <= 2 and 0 <= stb - ena <= 7200 and ska in fail_sessions:
                out.append(dict(session_key=skb, line_no=1, ts=stb,
                                detector="model_escalation", score=0.6,
                                evidence=json.dumps({
                                    "scope": "cross_session", "from_session": ska,
                                    "from_tier": ta, "to_tier": tb, "cwd": cwd,
                                    "gap_s": int(stb - ena)})))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default="labs/failure-atlas/data/atlas.db")
    args = ap.parse_args()
    con = sqlite3.connect(args.db)
    con.executescript(SCHEMA)
    con.execute("DELETE FROM signals")
    t0 = time.time()
    out: list[dict] = []
    keys = [k for (k,) in con.execute("SELECT session_key FROM sessions")]
    cols = ["session_key", "line_no", "ts", "type", "role", "model", "tool_name",
            "tool_use_id", "is_error", "api_error", "text", "tool_input",
            "is_sidechain", "text_len"]
    for n, sk in enumerate(keys):
        cur = con.execute(
            f"SELECT {','.join(cols)} FROM events WHERE session_key=? ORDER BY line_no", (sk,))
        rows = [dict(zip(cols, r)) for r in cur]
        if rows:
            detect_session(rows, out)
        if n % 500 == 0 and n:
            print(f"  ...{n}/{len(keys)} sessions ({time.time()-t0:.0f}s, {len(out)} signals)")
    # flush per-session signals before cross-session pass (it queries the table)
    con.executemany(
        "INSERT OR REPLACE INTO signals VALUES (:session_key,:line_no,:ts,:detector,:score,:evidence)", out)
    con.commit()
    extra: list[dict] = []
    detect_subagent_failures(con, extra)
    detect_cross_session_escalation(con, extra)
    con.executemany(
        "INSERT OR REPLACE INTO signals VALUES (:session_key,:line_no,:ts,:detector,:score,:evidence)", extra)
    con.commit()
    for det, cnt in con.execute(
            "SELECT detector, COUNT(*) FROM signals GROUP BY detector ORDER BY 2 DESC"):
        print(f"  {det:22s} {cnt}")
    print(f"done: {len(out) + len(extra)} signals over {len(keys)} sessions "
          f"in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
