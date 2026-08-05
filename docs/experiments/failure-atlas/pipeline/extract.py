#!/usr/bin/env python3
"""Stage 1: extract Claude Code transcripts into a normalized SQLite event store.

Walks one or more Claude config roots (default: ~/.claude and any ~/.claude-*),
parses every session JSONL under <root>/projects/, and writes:

  sessions(session_key, root, project, file, is_sidechain, agent_id, slug,
           entrypoint, start_ts, end_ts, n_events, models, cc_versions,
           git_branches, cwd)
  events(session_key, line_no, uuid, parent_uuid, ts, type, role, model,
         agent_id, is_sidechain, tool_name, tool_use_id, is_error,
         api_error, stop_reason, permission_mode, text, tool_input,
         text_len, thinking_len, cwd, git_branch)

Text policy: user text, assistant text, and tool inputs are stored truncated;
tool RESULTS are stored only when they are errors (else just length). Full
content is always recoverable via (file, line_no) pointers — the store carries
enough to detect failures, the source remains the archive. This keeps the DB a
fraction of corpus size and means the shareable layer never needs raw text.

Idempotent: re-running skips files whose (path, size, mtime) are unchanged.
"""
from __future__ import annotations

import argparse
import glob as globmod
import json
import sqlite3
import sys
import time
from pathlib import Path

TRUNC_TEXT = 4000
TRUNC_INPUT = 1500
TRUNC_ERROR = 4000

SCHEMA = """
CREATE TABLE IF NOT EXISTS files(
  path TEXT PRIMARY KEY, size INTEGER, mtime REAL, parsed_at REAL,
  n_lines INTEGER, n_bad_lines INTEGER
);
CREATE TABLE IF NOT EXISTS sessions(
  session_key TEXT PRIMARY KEY,      -- root_alias:relpath (unique per file)
  session_id TEXT, root TEXT, project TEXT, file TEXT,
  is_sidechain INTEGER, agent_id TEXT, slug TEXT, entrypoint TEXT,
  start_ts REAL, end_ts REAL, n_events INTEGER,
  models TEXT, cc_versions TEXT, git_branches TEXT, cwd TEXT
);
CREATE TABLE IF NOT EXISTS events(
  session_key TEXT, line_no INTEGER, uuid TEXT, parent_uuid TEXT,
  ts REAL, type TEXT, role TEXT, model TEXT, agent_id TEXT,
  is_sidechain INTEGER, tool_name TEXT, tool_use_id TEXT,
  is_error INTEGER DEFAULT 0, api_error TEXT, stop_reason TEXT,
  permission_mode TEXT, text TEXT, tool_input TEXT,
  text_len INTEGER DEFAULT 0, thinking_len INTEGER DEFAULT 0,
  cwd TEXT, git_branch TEXT,
  PRIMARY KEY(session_key, line_no)
);
CREATE INDEX IF NOT EXISTS ix_events_session_ts ON events(session_key, ts);
CREATE INDEX IF NOT EXISTS ix_events_tool ON events(tool_name);
CREATE INDEX IF NOT EXISTS ix_events_err ON events(is_error);
CREATE INDEX IF NOT EXISTS ix_events_type ON events(type);
"""


def parse_ts(v) -> float | None:
    if not v:
        return None
    if isinstance(v, (int, float)):
        return float(v) / (1000.0 if v > 1e12 else 1.0)
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def block_text(content) -> tuple[str, int, int]:
    """Return (joined visible text, text_len, thinking_len) from a message content field."""
    if isinstance(content, str):
        return content, len(content), 0
    texts, tlen, thlen = [], 0, 0
    if isinstance(content, list):
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text" and isinstance(b.get("text"), str):
                texts.append(b["text"])
                tlen += len(b["text"])
            elif b.get("type") == "thinking" and isinstance(b.get("thinking"), str):
                thlen += len(b["thinking"])
    return "\n".join(texts), tlen, thlen


def result_text(block) -> str:
    c = block.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        parts = []
        for e in c:
            if isinstance(e, dict) and isinstance(e.get("text"), str):
                parts.append(e["text"])
        return "\n".join(parts)
    return "" if c is None else json.dumps(c)[:TRUNC_ERROR]


def extract_file(path: Path, root_alias: str, root: Path, con: sqlite3.Connection) -> None:
    rel = str(path.relative_to(root))
    session_key = f"{root_alias}:{rel}"
    rows, bad = [], 0
    meta = {
        "session_id": None, "slug": None, "entrypoint": None, "agent_id": None,
        "models": set(), "versions": set(), "branches": set(), "cwd": None,
        "sidechain": 0,
    }
    perm_mode = None
    with open(path, errors="replace") as fh:
        for line_no, line in enumerate(fh, 1):
            try:
                o = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            if not isinstance(o, dict):
                bad += 1
                continue
            etype = o.get("type")
            if etype == "permission-mode":
                perm_mode = o.get("mode") or perm_mode
            meta["session_id"] = meta["session_id"] or o.get("sessionId")
            meta["slug"] = meta["slug"] or o.get("slug")
            meta["entrypoint"] = meta["entrypoint"] or o.get("entrypoint")
            meta["agent_id"] = meta["agent_id"] or o.get("agentId")
            meta["cwd"] = meta["cwd"] or o.get("cwd")
            if o.get("version"):
                meta["versions"].add(o["version"])
            if o.get("gitBranch"):
                meta["branches"].add(o["gitBranch"])
            if o.get("isSidechain"):
                meta["sidechain"] = 1

            ts = parse_ts(o.get("timestamp"))
            msg = o.get("message") if isinstance(o.get("message"), dict) else {}
            role = msg.get("role")
            model = msg.get("model")
            if model:
                meta["models"].add(model)
            stop_reason = msg.get("stop_reason")
            api_error = None
            if o.get("isApiErrorMessage"):
                api_error = str(o.get("apiErrorStatus") or o.get("error") or "api_error")[:200]

            text, tlen, thlen = block_text(msg.get("content"))

            base = dict(
                session_key=session_key, line_no=line_no, uuid=o.get("uuid"),
                parent_uuid=o.get("parentUuid"), ts=ts, type=etype, role=role,
                model=model, agent_id=o.get("agentId"),
                is_sidechain=1 if o.get("isSidechain") else 0,
                stop_reason=stop_reason, permission_mode=perm_mode,
                api_error=api_error, cwd=o.get("cwd"), git_branch=o.get("gitBranch"),
            )

            content = msg.get("content")
            emitted_tool_row = False
            if isinstance(content, list):
                for b in content:
                    if not isinstance(b, dict):
                        continue
                    if b.get("type") == "tool_use":
                        rows.append({**base,
                            "tool_name": b.get("name"), "tool_use_id": b.get("id"),
                            "is_error": 0,
                            "tool_input": json.dumps(b.get("input"), default=str)[:TRUNC_INPUT],
                            "text": text[:TRUNC_TEXT] if text else None,
                            "text_len": tlen, "thinking_len": thlen})
                        emitted_tool_row = True
                        # one row per tool_use; text carried once
                        text, tlen, thlen = "", 0, 0
                    elif b.get("type") == "tool_result":
                        err = 1 if b.get("is_error") else 0
                        rtxt = result_text(b)
                        rows.append({**base,
                            "tool_name": None, "tool_use_id": b.get("tool_use_id"),
                            "is_error": err, "tool_input": None,
                            "text": rtxt[:TRUNC_ERROR] if err else None,
                            "text_len": len(rtxt), "thinking_len": 0})
                        emitted_tool_row = True
            if not emitted_tool_row:
                store_text = text[:TRUNC_TEXT] if (role == "user" or role == "assistant" or api_error) and text else None
                rows.append({**base, "tool_name": None, "tool_use_id": o.get("toolUseID"),
                             "is_error": 0, "tool_input": None, "text": store_text,
                             "text_len": tlen, "thinking_len": thlen})

    tss = [r["ts"] for r in rows if r["ts"]]
    con.execute(
        "INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (session_key, meta["session_id"], root_alias,
         rel.split("/")[0] if "/" in rel else "", rel,
         meta["sidechain"], meta["agent_id"], meta["slug"], meta["entrypoint"],
         min(tss) if tss else None, max(tss) if tss else None, len(rows),
         ",".join(sorted(meta["models"])), ",".join(sorted(meta["versions"])),
         ",".join(sorted(meta["branches"])), meta["cwd"]))
    con.execute("DELETE FROM events WHERE session_key=?", (session_key,))
    con.executemany(
        """INSERT OR REPLACE INTO events(session_key,line_no,uuid,parent_uuid,ts,type,role,model,
           agent_id,is_sidechain,tool_name,tool_use_id,is_error,api_error,stop_reason,
           permission_mode,text,tool_input,text_len,thinking_len,cwd,git_branch)
           VALUES(:session_key,:line_no,:uuid,:parent_uuid,:ts,:type,:role,:model,
           :agent_id,:is_sidechain,:tool_name,:tool_use_id,:is_error,:api_error,:stop_reason,
           :permission_mode,:text,:tool_input,:text_len,:thinking_len,:cwd,:git_branch)""",
        rows)
    st = path.stat()
    con.execute("INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?)",
                (str(path), st.st_size, st.st_mtime, time.time(), len(rows), bad))


def discover_roots(patterns: list[str]) -> list[Path]:
    roots = []
    for pat in patterns:
        for p in sorted(globmod.glob(str(Path(pat).expanduser()))):
            pp = Path(p)
            if (pp / "projects").is_dir():
                roots.append(pp)
    return roots


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--roots", nargs="*", default=["~/.claude", "~/.claude-*"],
                    help="Claude config roots or globs (need a projects/ subdir)")
    ap.add_argument("--db", default="labs/failure-atlas/data/atlas.db")
    ap.add_argument("--exclude-session", action="append", default=[],
                    help="session_id values to skip (e.g. the currently running session)")
    args = ap.parse_args()

    db = Path(args.db)
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.executescript(SCHEMA)
    con.execute("PRAGMA journal_mode=WAL")

    roots = discover_roots(args.roots)
    if not roots:
        print("no roots found", file=sys.stderr)
        return 1
    total, skipped, failed = 0, 0, 0
    t0 = time.time()
    for root in roots:
        alias = root.name
        files = sorted((root / "projects").rglob("*.jsonl"))
        print(f"[{alias}] {len(files)} jsonl files")
        for i, f in enumerate(files):
            try:
                # workflow journals are event skeletons, not transcripts
                if f.name == "journal.jsonl":
                    continue
                st = f.stat()
                if st.st_size == 0:
                    continue
                row = con.execute("SELECT size, mtime FROM files WHERE path=?", (str(f),)).fetchone()
                if row and row[0] == st.st_size and abs(row[1] - st.st_mtime) < 1:
                    skipped += 1
                    continue
                extract_file(f, alias, root, con)
                total += 1
                if total % 200 == 0:
                    con.commit()
                    print(f"  ...{total} parsed ({time.time()-t0:.0f}s)")
            except Exception as e:  # keep going; one bad file must not sink the run
                failed += 1
                print(f"  FAIL {f}: {type(e).__name__}: {e}", file=sys.stderr)
        con.commit()
    n_ev = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    n_se = con.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
    print(f"done: {total} parsed, {skipped} unchanged, {failed} failed; "
          f"{n_se} sessions, {n_ev} events; {time.time()-t0:.0f}s; db={db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
