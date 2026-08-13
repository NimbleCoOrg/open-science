#!/usr/bin/env node
/**
 * build-index.mjs — regenerate the two experiment indexes from meta.json manifests.
 *
 * Source of truth: docs/experiments/<slug>/meta.json
 *   { slug, title, blurb, emoji, status, updated, source, order? }
 *
 * Regenerates, between <!-- experiments:begin --> / <!-- experiments:end --> markers:
 *   - the card grid in docs/index.html
 *   - the experiments table in README.md
 *
 * Only status: "published" entries are listed. Sort: updated desc, then the
 * optional numeric `order` asc (default 100), then slug asc — the order field
 * exists purely to keep a stable, curated sequence when several experiments
 * share an updated date (a repo-wide fix re-dates everything at once).
 *
 * `title` and `blurb` are inserted verbatim (they may contain & and unicode);
 * keep them HTML-safe in meta.json. No dependencies, Node >= 18.
 *
 * Usage:
 *   node scripts/build-index.mjs           # write
 *   node scripts/build-index.mjs --check   # exit 1 if output would change
 */

import { readdirSync, readFileSync, writeFileSync, statSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const EXPERIMENTS_DIR = join(ROOT, 'docs', 'experiments');
const INDEX_HTML = join(ROOT, 'docs', 'index.html');
const README = join(ROOT, 'README.md');
const BEGIN = '<!-- experiments:begin -->';
const END = '<!-- experiments:end -->';
const PAGES_BASE = 'https://nimblecoorg.github.io/open-science/experiments';

function loadManifests() {
  const entries = [];
  for (const name of readdirSync(EXPERIMENTS_DIR).sort()) {
    const dir = join(EXPERIMENTS_DIR, name);
    if (!statSync(dir).isDirectory()) continue;
    let raw;
    try {
      raw = readFileSync(join(dir, 'meta.json'), 'utf8');
    } catch {
      console.warn(`warn: ${name}/ has no meta.json — not listed`);
      continue;
    }
    const meta = JSON.parse(raw);
    for (const field of ['slug', 'title', 'blurb', 'status', 'updated']) {
      if (!meta[field]) throw new Error(`${name}/meta.json: missing "${field}"`);
    }
    if (meta.slug !== name) throw new Error(`${name}/meta.json: slug "${meta.slug}" != directory name`);
    if (meta.status !== 'published') continue;
    entries.push(meta);
  }
  entries.sort((a, b) =>
    b.updated.localeCompare(a.updated) ||
    (a.order ?? 100) - (b.order ?? 100) ||
    a.slug.localeCompare(b.slug));
  return entries;
}

const heading = (m) => (m.emoji ? `${m.emoji} ${m.title}` : m.title);

function renderCards(entries) {
  return entries.map((m) => [
    `    <a class="card" href="experiments/${m.slug}/">`,
    `      <h2>${heading(m)}</h2>`,
    `      <p>${m.blurb}</p>`,
    `    </a>`,
  ].join('\n')).join('\n');
}

function renderTable(entries) {
  const rows = entries.map((m) =>
    `| [${m.slug}](docs/experiments/${m.slug}/) | ${m.title}: ${m.blurb} | [View](${PAGES_BASE}/${m.slug}/) |`);
  return [
    '| Experiment | Description | Live |',
    '|-----------|-------------|------|',
    ...rows,
  ].join('\n');
}

function replaceBlock(file, body) {
  const text = readFileSync(file, 'utf8');
  const start = text.indexOf(BEGIN);
  const end = text.indexOf(END);
  if (start === -1 || end === -1 || end < start) {
    throw new Error(`${file}: missing ${BEGIN} / ${END} markers`);
  }
  const indent = text.slice(text.lastIndexOf('\n', start) + 1, start);
  const head = text.slice(0, start + BEGIN.length);
  const tail = text.slice(end);
  return `${head}\n${body}\n${indent}${tail}`;
}

const check = process.argv.includes('--check');
const entries = loadManifests();
const outputs = [
  [INDEX_HTML, replaceBlock(INDEX_HTML, renderCards(entries))],
  [README, replaceBlock(README, renderTable(entries))],
];

let drift = false;
for (const [file, next] of outputs) {
  if (readFileSync(file, 'utf8') === next) continue;
  drift = true;
  if (check) console.error(`drift: ${file} is out of date`);
  else {
    writeFileSync(file, next);
    console.log(`updated: ${file}`);
  }
}

if (check) {
  if (drift) {
    console.error('run `node scripts/build-index.mjs` and commit the result');
    process.exit(1);
  }
  console.log(`ok: indexes match ${entries.length} manifests`);
} else if (!drift) {
  console.log(`ok: indexes already match ${entries.length} manifests`);
}
