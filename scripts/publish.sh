#!/usr/bin/env bash
#
# publish.sh — copy a built experiment into docs/, regenerate the indexes, push.
#
# Intended to run on the Mac Mini inside (or next to) the hermes-matilde container,
# where experiments are generated. Safe to re-run: an unchanged experiment produces
# no commit and no push.
#
# Usage:
#   scripts/publish.sh <slug>
#   scripts/publish.sh <slug> --src /path/to/built/output
#
# Assumptions:
#   - Run from anywhere; paths resolve relative to this script's repo.
#   - Built output lives at ${MATILDE_HOME:-$HOME}/experiments/<slug>/dist/ unless --src.
#   - The checkout has a writable origin and is on the branch you want to push
#     (normally main — pushing straight to main is how this repo already works).
#   - git, rsync and node >= 18 are available; gh is optional (used only to poke
#     the cyborg-garden-site rebuild).
#   - GitHub rejects files > 100 MB, so this script refuses anything > 95 MB.
#     Keep large assets on the expansion volume and point meta.json's "source" there.
#
set -euo pipefail

MAX_BYTES=$((95 * 1024 * 1024))
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DISPATCH_REPO="cyborg-garden/cyborg-garden-site"

die() { printf 'publish: %s\n' "$*" >&2; exit 1; }
info() { printf '→ %s\n' "$*"; }
warn() { printf '! %s\n' "$*" >&2; }

SLUG=""
SRC=""
while [ $# -gt 0 ]; do
  case "$1" in
    --src) [ $# -ge 2 ] || die "--src needs a directory"; SRC="$2"; shift 2 ;;
    -h|--help) sed -n '2,25p' "${BASH_SOURCE[0]}"; exit 0 ;;
    -*) die "unknown option: $1" ;;
    *) [ -z "$SLUG" ] || die "unexpected argument: $1"; SLUG="$1"; shift ;;
  esac
done

[ -n "$SLUG" ] || die "usage: publish.sh <slug> [--src <dir>]"
case "$SLUG" in */*|.*) die "slug must be a plain directory name, got: $SLUG" ;; esac

: "${MATILDE_HOME:=$HOME}"
[ -n "$SRC" ] || SRC="$MATILDE_HOME/experiments/$SLUG/dist"
[ -d "$SRC" ] || die "source directory not found: $SRC (pass --src <dir>)"

DEST="$REPO_ROOT/docs/experiments/$SLUG"
META="$DEST/meta.json"

# --- refuse oversized files before anything is copied ---------------------------
OVERSIZED="$(find "$SRC" -type f -size +${MAX_BYTES}c -print 2>/dev/null || true)"
if [ -n "$OVERSIZED" ]; then
  warn "these files exceed 95 MB and cannot go in the repo:"
  printf '%s\n' "$OVERSIZED" | while IFS= read -r f; do printf '    %s\n' "$f" >&2; done
  die "store them on the expansion volume and record the path in $META (\"source\"), then re-run"
fi

# --- copy ------------------------------------------------------------------------
mkdir -p "$DEST"
info "rsync $SRC/ → docs/experiments/$SLUG/"
rsync -a --delete --exclude 'meta.json' --exclude '.DS_Store' "$SRC/" "$DEST/"

# --- manifest --------------------------------------------------------------------
if [ ! -f "$META" ]; then
  cat > "$META" <<EOF
{
  "slug": "$SLUG",
  "title": "TODO: short display title",
  "blurb": "TODO: one sentence shown on the card and in the README table",
  "emoji": "",
  "status": "draft",
  "updated": "$(date +%F)",
  "source": "generated in hermes-matilde container on the Mini; source not yet in repo"
}
EOF
  warn "no manifest existed — wrote a skeleton at $META"
  warn "fill in title/blurb/emoji, set \"status\": \"published\", then re-run: scripts/publish.sh $SLUG"
  exit 1
fi

# refresh the updated date without pulling in a JSON dependency
TODAY="$(date +%F)"
node - "$META" "$TODAY" <<'NODE'
const fs = require('node:fs');
const [file, today] = process.argv.slice(2);
const meta = JSON.parse(fs.readFileSync(file, 'utf8'));
if (meta.updated !== today) {
  meta.updated = today;
  fs.writeFileSync(file, JSON.stringify(meta, null, 2) + '\n');
}
NODE

# --- regenerate indexes ----------------------------------------------------------
info "regenerating indexes"
node "$REPO_ROOT/scripts/build-index.mjs"

# --- commit / push ---------------------------------------------------------------
git -C "$REPO_ROOT" add -A
if git -C "$REPO_ROOT" diff --cached --quiet; then
  info "nothing changed — no commit, no push"
  exit 0
fi
git -C "$REPO_ROOT" commit -m "publish($SLUG): $TODAY"
info "pulling --rebase"
git -C "$REPO_ROOT" pull --rebase
info "pushing"
git -C "$REPO_ROOT" push

# --- poke the site rebuild (best effort) ------------------------------------------
if command -v gh >/dev/null 2>&1; then
  if gh api "repos/$DISPATCH_REPO/dispatches" -f event_type=open-science-updated >/dev/null 2>&1; then
    info "dispatched open-science-updated to $DISPATCH_REPO"
  else
    warn "could not dispatch open-science-updated to $DISPATCH_REPO (token may lack repo scope) — the site will pick it up on its next build"
  fi
else
  warn "gh not installed — skipped the $DISPATCH_REPO rebuild dispatch"
fi

info "published $SLUG"
