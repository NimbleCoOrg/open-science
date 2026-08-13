#!/usr/bin/env python3
"""§5 — score B1-B5 for prereg rev 3.1.

Reuses rev 2's corrected machinery (`llm_agreement_score.py`): the substrate
audit with content-duplication detection and a per-cell marginal model, the
cluster bootstrap that drops rather than coerces undefined replicates, and the
`verdict` rule where a CI spanning its falsifier is AMBIGUOUS and never resolves
toward the interesting direction.

Three things this script refuses to do, each because rev 2 or its audit was
burned by the opposite:

  * score a coder that §4 did not admit;
  * score at all when §4.2 made the roster the headline;
  * report B3 or B4 from data that does not exist — an absent per-cell arm is
    UNAVAILABLE, not a quietly dropped hypothesis.

B4 is computed on the clean-key frame only (§1). The contamination contrast set
is reported beside it as a demonstration, never as a verdict.

  .venv/bin/python pipeline/rev3_score.py
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "pipeline"))
from llm_agreement_score import (  # noqa: E402
    alpha_over,
    build_units,
    cluster_bootstrap,
    substrate_audit,
    verdict,
)
from rev3_coders import CELLS, FAMILY, parse_freeform, parse_percell  # noqa: E402

FRAME = BASE / "data/llm-agreement/frame-rev3.json"
ADMISSION = BASE / "data/llm-agreement/admission-rev3.json"
RAW_DIR = BASE / "data/llm-agreement/raw"
OUT = BASE / "data/llm-agreement/results-rev3.json"

SEED = 20260810
BOOTSTRAP_N = 2000

B1_BAR = 0.40
B2_BAR, B2_FALSIFY = 0.15, 0.05
B2_PER_FAMILY = 0.15
B3_MAX_GAP = 0.15
B4_BAR, B4_FALSIFY = 0.15, 0.05
B4_MARGINAL_LO, B4_MARGINAL_HI = 0.05, 0.60
B5_BAR = 0.30


def load_frame_labels(coders: list, phase: str = "frame") -> dict:
    """(coder, row) -> {cell: 0/1}, from raw. Unparseable output is absent, not zero."""
    labels, missing = {}, {}
    for coder in coders:
        p = RAW_DIR / f"frame-rev3-{coder}.jsonl"
        miss = 0
        if not p.exists():
            missing[coder] = None
            continue
        for line in p.read_text().splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("phase") != phase:
                continue
            v, _ = parse_freeform(r.get("response"))
            if v is None:
                miss += 1
            else:
                labels[(coder, r["row_index"])] = v
        missing[coder] = miss
    return labels, missing


def load_percell_labels(coders: list) -> dict:
    labels = {}
    for coder in coders:
        p = RAW_DIR / f"percell-rev3-{coder}.jsonl"
        if not p.exists():
            continue
        acc = {}
        for line in p.read_text().splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            v, _ = parse_percell(r.get("response"))
            if v is not None:
                acc.setdefault(r["row_index"], {})[r["cell"]] = v
        for row, cells in acc.items():
            if len(cells) == len(CELLS):  # partial vectors are not a coding
                labels[(coder, row)] = cells
    return labels


def per_cell_alphas(by_trace: dict, rows: list) -> dict:
    from llm_agreement_score import alpha_nominal

    out = {}
    for cell in CELLS:
        units = [by_trace[r][cell] for r in rows
                 if cell in by_trace[r] and len(by_trace[r][cell]) >= 2]
        out[cell] = alpha_nominal(units) if units else None
    return out


def marked_proportion(labels: dict, coder: str, rows: list) -> float | None:
    vals = [sum(labels[(coder, r)].values()) / len(CELLS)
            for r in rows if (coder, r) in labels]
    return sum(vals) / len(vals) if vals else None


def main() -> None:
    if not ADMISSION.exists():
        raise SystemExit("no admission-rev3.json — §4 must fix the roster first")
    adm = json.load(open(ADMISSION))
    if not adm.get("roster_complete"):
        raise SystemExit("§4 roster incomplete — every candidate must run before scoring")
    if adm.get("roster_is_the_headline"):
        raise SystemExit(
            "§4.2: fewer than four coders admitted, so the roster IS the result. "
            "No agreement statistic is to be computed."
        )
    coders = adm["admitted"]
    frame = json.load(open(FRAME))
    rows = [x["row_index"] for x in frame["frame"]]
    published = {x["row_index"]: dict(zip(CELLS, x["published"])) for x in frame["frame"]}
    stratum = {x["row_index"]: x["stratum"] for x in frame["frame"]}

    labels, missing = load_frame_labels(coders)
    print(f"admitted coders: {', '.join(coders)}")
    for c in coders:
        got = sum(1 for r in rows if (c, r) in labels)
        print(f"  {c:<3} {got}/{len(rows)} frame traces parsed, {missing.get(c)} missing")

    # §6 — a coder missing more than 20% makes the study underpowered rather
    # than making the coder droppable.
    underpowered = [c for c in coders
                    if sum(1 for r in rows if (c, r) in labels) < 0.8 * len(rows)]

    by_trace = build_units(labels, coders, rows)

    # The audit's first check compares INPUTS, not labels — the independence
    # violation the old rule could not see. It needs the trajectories, so they
    # are re-read and re-redacted here rather than passed as row indices.
    from rev3_admission import trace_text

    records = json.load(open(BASE / "data/external/MAST-Data/MAD_full_dataset.json"))
    units_by_row = {x["row_index"]: x for x in frame["frame"]}
    trajectories = {r: trace_text(records, units_by_row[r]) for r in rows}

    audit = substrate_audit(by_trace, coders, trajectories, seed=SEED)
    print(f"\nsubstrate audit: {'PASS' if audit['valid'] else 'FAIL'}")
    for f in audit["failures"]:
        print(f"  FAILURE: {f}")
    for w in audit["warnings"]:
        print(f"  warning: {w}")
    if not audit["valid"]:
        raise SystemExit("§6: substrate audit failed — no hypothesis is scored")

    res = {"coders": coders, "n_traces": len(rows), "underpowered_coders": underpowered,
           "audit": audit, "hypotheses": {}}

    # ---- B1
    b1 = alpha_over(by_trace, rows, coders)
    lo, hi, n = cluster_bootstrap(rows, lambda rr: alpha_over(by_trace, rr, coders),
                                  seed=SEED, iterations=BOOTSTRAP_N)
    res["hypotheses"]["B1"] = {"statistic": b1, "ci": [lo, hi],
                               "verdict": verdict(lo, hi, B1_BAR, B1_BAR)}

    # ---- B2
    def fam_diff(rr):
        pairs = {}
        for i, a in enumerate(coders):
            for b in coders[i + 1:]:
                pairs[(a, b)] = alpha_over(by_trace, rr, [a, b])
        within = [v for (a, b), v in pairs.items() if FAMILY[a] == FAMILY[b] and v is not None]
        between = [v for (a, b), v in pairs.items() if FAMILY[a] != FAMILY[b] and v is not None]
        if not within or not between:
            return None
        return sum(within) / len(within) - sum(between) / len(between)

    b2 = fam_diff(rows)
    lo2, hi2, _ = cluster_bootstrap(rows, fam_diff, seed=SEED, iterations=BOOTSTRAP_N)

    # The Alibaba check: rev 2's A2 was confirmed and under-determined because
    # only one family had two members. B2 requires at least two families to
    # clear the bar individually.
    pairs = {}
    for i, a in enumerate(coders):
        for b in coders[i + 1:]:
            pairs[(a, b)] = alpha_over(by_trace, rows, [a, b])
    between_all = [v for (a, b), v in pairs.items() if FAMILY[a] != FAMILY[b] and v is not None]
    between_mean = sum(between_all) / len(between_all) if between_all else None
    per_family = {}
    for fam in sorted(set(FAMILY[c] for c in coders)):
        vals = [v for (a, b), v in pairs.items()
                if FAMILY[a] == fam and FAMILY[b] == fam and v is not None]
        per_family[fam] = {
            "n_pairs": len(vals),
            "mean_alpha": sum(vals) / len(vals) if vals else None,
            "clears_bar": (bool(vals) and between_mean is not None
                           and sum(vals) / len(vals) >= between_mean + B2_PER_FAMILY),
        }
    n_clearing = sum(1 for v in per_family.values() if v["clears_bar"])
    v2 = verdict(lo2, hi2, B2_BAR, B2_FALSIFY)
    if v2 == "CONFIRMED" and n_clearing < 2:
        v2 = "CONFIRMED POOLED, SINGLE-FAMILY — re-scored per §5 falsifier"
    res["hypotheses"]["B2"] = {"statistic": b2, "ci": [lo2, hi2],
                               "between_family_mean": between_mean,
                               "per_family": per_family, "families_clearing": n_clearing,
                               "verdict": v2}

    # ---- B3
    pc = load_percell_labels(coders)
    subset_ids = set(frame["percell_subset"])
    subset_rows = [x["row_index"] for x in frame["frame"] if x["unit_id"] in subset_ids]
    pc_coders = sorted({c for (c, _) in pc})
    if len(pc_coders) < 3:
        res["hypotheses"]["B3"] = {
            "verdict": "UNAVAILABLE — per-cell arm not collected",
            "coders_with_percell": pc_coders,
            "note": "§4.2 requires >=3 coders admitted under BOTH instruments; "
                    "reported as underpowered rather than scored.",
        }
    else:
        ff = alpha_over(by_trace, subset_rows, pc_coders)
        pc_by = build_units(pc, pc_coders, subset_rows)
        pcA = alpha_over(pc_by, subset_rows, pc_coders)
        gap = None if ff is None or pcA is None else abs(ff - pcA)
        res["hypotheses"]["B3"] = {
            "alpha_freeform": ff, "alpha_percell": pcA, "gap": gap,
            "coders": pc_coders,
            "verdict": ("UNRESOLVED" if gap is None
                        else "CONFIRMED" if gap <= B3_MAX_GAP else "REFUTED"),
        }

    # ---- B4
    def concordance(coder, rr):
        units = []
        for r in rr:
            if (coder, r) not in labels:
                continue
            for cell in CELLS:
                units.append({coder: labels[(coder, r)][cell], "published": published[r][cell]})
        from llm_agreement_score import alpha_nominal
        return alpha_nominal(units)

    marginals = {c: marked_proportion(labels, c, rows) for c in coders}
    b4_coders = [c for c in coders
                 if marginals[c] is not None and B4_MARGINAL_LO <= marginals[c] <= B4_MARGINAL_HI]
    excluded_b4 = {c: marginals[c] for c in coders if c not in b4_coders}

    if not b4_coders:
        res["hypotheses"]["B4"] = {
            "verdict": "UNAVAILABLE — every coder's marking rate is outside "
                       f"[{B4_MARGINAL_LO}, {B4_MARGINAL_HI}]",
            "marginals": marginals,
        }
    else:
        def b4_stat(rr):
            pooled = alpha_over(by_trace, rr, coders)
            cs = [concordance(c, rr) for c in b4_coders]
            cs = [x for x in cs if x is not None]
            if pooled is None or not cs:
                return None
            return pooled - sum(cs) / len(cs)

        b4 = b4_stat(rows)
        lo4, hi4, _ = cluster_bootstrap(rows, b4_stat, seed=SEED, iterations=BOOTSTRAP_N)
        res["hypotheses"]["B4"] = {
            "statistic": b4, "ci": [lo4, hi4],
            "coders_included": b4_coders, "excluded_by_marginal": excluded_b4,
            "marginals": marginals,
            "verdict": verdict(lo4, hi4, B4_BAR, B4_FALSIFY),
            "bound": "concordance with a published label set, never accuracy; that "
                     "label set scores alpha=0.047 against itself on the file's repeats",
        }

    # ---- B5
    cell_a = per_cell_alphas(by_trace, rows)
    vals = sorted(v for v in cell_a.values() if v is not None)
    iqr = (statistics.quantiles(vals, n=4)[2] - statistics.quantiles(vals, n=4)[0]
           if len(vals) >= 4 else None)

    def iqr_stat(rr):
        ca = per_cell_alphas(build_units(labels, coders, rr), rr)
        vs = sorted(v for v in ca.values() if v is not None)
        if len(vs) < 4:
            return None
        q = statistics.quantiles(vs, n=4)
        return q[2] - q[0]

    lo5, hi5, _ = cluster_bootstrap(rows, iqr_stat, seed=SEED, iterations=BOOTSTRAP_N)
    res["hypotheses"]["B5"] = {"statistic": iqr, "ci": [lo5, hi5],
                               "per_cell": cell_a,
                               "verdict": verdict(lo5, hi5, B5_BAR, B5_BAR, strict=True)}

    # ---- secondary, no thresholds and no verdicts
    def rows_in(s):
        return [r for r in rows if stratum[r] == s]

    res["secondary"] = {
        "length_system_matched_S1_vs_S2": {
            "S1_short_AG2": alpha_over(by_trace, rows_in("S1"), coders),
            "S2_long_AG2": alpha_over(by_trace, rows_in("S2"), coders)},
        "system_length_matched_S2_vs_S3": {
            "S2_AG2_long": alpha_over(by_trace, rows_in("S2"), coders),
            "S3_Magentic_long": alpha_over(by_trace, rows_in("S3"), coders)},
    }

    # §3.3 — B4 recomputed with the contamination contrast set folded in. This is
    # a DEMONSTRATION of what copied labels do to a concordance figure, never a
    # verdict: 41% of the published annotation is a copied slot, and the whole
    # reason the frame is clean-key-only is that B4 must not rest on it.
    contrast_labels, _ = load_frame_labels(coders, phase="contrast")
    if contrast_labels and "statistic" in res["hypotheses"].get("B4", {}):
        c_rows = [x["row_index"] for x in frame["contrast"]]
        c_published = {x["row_index"]: dict(zip(CELLS, x["published"]))
                       for x in frame["contrast"]}
        merged = dict(labels)
        merged.update(contrast_labels)
        merged_published = dict(published)
        merged_published.update(c_published)
        all_rows = rows + c_rows
        merged_by_trace = build_units(merged, coders, all_rows)

        from llm_agreement_score import alpha_nominal

        def conc_all(coder, rr):
            units = []
            for r in rr:
                if (coder, r) not in merged:
                    continue
                for cell in CELLS:
                    units.append({coder: merged[(coder, r)][cell],
                                  "published": merged_published[r][cell]})
            return alpha_nominal(units)

        pooled_all = alpha_over(merged_by_trace, all_rows, coders)
        cs = [conc_all(c, all_rows) for c in b4_coders]
        cs = [x for x in cs if x is not None]
        res["secondary"]["B4_with_contaminated_contrast_set"] = {
            "n_traces": len(all_rows),
            "statistic": (pooled_all - sum(cs) / len(cs)) if pooled_all is not None and cs else None,
            "clean_only_statistic": res["hypotheses"]["B4"]["statistic"],
            "note": "demonstration only — no verdict attaches to this number",
        }

    print("\n" + "=" * 74)
    for name, h in res["hypotheses"].items():
        stat = h.get("statistic", h.get("gap"))
        ci = h.get("ci")
        s = "—" if stat is None else f"{stat:.3f}"
        c = "" if not ci or ci[0] is None else f"  [{ci[0]:.3f}, {ci[1]:.3f}]"
        print(f"{name}  {s:>7}{c:<22}  {h['verdict']}")
    print("=" * 74)
    if underpowered:
        print(f"UNDERPOWERED — coders missing >20% of traces: {underpowered}")

    json.dump(res, open(OUT, "w"), indent=1, default=float)
    print("wrote", OUT.relative_to(BASE))


if __name__ == "__main__":
    main()
