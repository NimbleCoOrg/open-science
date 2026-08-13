#!/usr/bin/env python3
"""§5 — score D1-D5 for prereg rev 4.

Reuses rev 3.1's machinery unchanged: the corrected substrate audit, the cluster
bootstrap that drops rather than coerces undefined replicates, and the verdict
rule where a CI spanning its falsifier is AMBIGUOUS.

D2 compares this study's frontier alpha against rev 3.1's **0.173 on the
identical frame**. That is only meaningful because the frame, the prompt and the
parser are literally the same objects — a re-drawn frame or a re-typed prompt
would confound tier with sample.

  .venv/bin/python pipeline/rev4_score.py
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "pipeline"))
from llm_agreement_score import (  # noqa: E402
    alpha_nominal,
    alpha_over,
    build_units,
    cluster_bootstrap,
    substrate_audit,
    verdict,
)
from rev3_admission import trace_text  # noqa: E402
from rev4_coders import CELLS, CODERS, FAMILY, TIER, parse_freeform  # noqa: E402

FRAME = BASE / "data/llm-agreement/frame-rev3.json"
SRC = BASE / "data/external/MAST-Data/MAD_full_dataset.json"
ADMISSION = BASE / "data/llm-agreement/admission-rev4.json"
RAW_DIR = BASE / "data/llm-agreement/raw"
REV3 = BASE / "data/llm-agreement/results-rev3.json"
OUT = BASE / "data/llm-agreement/results-rev4.json"

SEED = 20260812
BOOTSTRAP_N = 2000

D1_BAR = 0.40
D2_BAR, D2_FALSIFY = 0.15, 0.05
D4_BAR, D4_FALSIFY = 0.15, 0.05
D4_MARGINAL_LO, D4_MARGINAL_HI = 0.05, 0.60
MIN_PER_TIER = 2


def load_labels(coders: list) -> tuple:
    labels, missing = {}, {}
    for c in coders:
        p = RAW_DIR / f"rev4-frame-{c}.jsonl"
        miss = 0
        if not p.exists():
            missing[c] = None
            continue
        for line in p.read_text().splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not r.get("ok"):
                miss += 1
                continue
            v, _ = parse_freeform(r.get("response"))
            if v is None:
                miss += 1
            else:
                labels[(c, r["row_index"])] = v
        missing[c] = miss
    return labels, missing


def marked_proportion(labels, coder, rows):
    vals = [sum(labels[(coder, r)].values()) / len(CELLS)
            for r in rows if (coder, r) in labels]
    return sum(vals) / len(vals) if vals else None


def main() -> None:
    adm = json.load(open(ADMISSION))
    coders = adm["admitted"]
    frame = json.load(open(FRAME))
    rows = [x["row_index"] for x in frame["frame"]]
    published = {x["row_index"]: dict(zip(CELLS, x["published"])) for x in frame["frame"]}

    labels, missing = load_labels(coders)
    print("admitted:", ", ".join(f"{c}({TIER[c]})" for c in coders))
    for c in coders:
        got = sum(1 for r in rows if (c, r) in labels)
        print(f"  {c:<3} {CODERS[c]:<36} {got}/{len(rows)} parsed, {missing.get(c)} missing")

    by_tier = collections.defaultdict(list)
    for c in coders:
        by_tier[TIER[c]].append(c)

    by_trace = build_units(labels, coders, rows)
    units_by_row = {x["row_index"]: x for x in frame["frame"]}
    records = json.load(open(SRC))
    trajectories = {r: trace_text(records, units_by_row[r]) for r in rows}
    audit = substrate_audit(by_trace, coders, trajectories, seed=SEED)
    print(f"\nsubstrate audit: {'PASS' if audit['valid'] else 'FAIL'}")
    for f in audit["failures"]:
        print("  FAILURE:", f)
    for w in audit["warnings"]:
        print("  warning:", w)
    if not audit["valid"]:
        raise SystemExit("§6: substrate audit failed — no hypothesis is scored")

    res = {"coders": coders, "by_tier": dict(by_tier), "audit": audit,
           "n_traces": len(rows), "hypotheses": {}, "secondary": {}}

    # ---- D1: do frontier coders agree with each other?
    t3 = by_tier["T3"]
    if len(t3) < MIN_PER_TIER:
        res["hypotheses"]["D1"] = {"verdict": "UNAVAILABLE — T3 under-populated"}
    else:
        t3_by = build_units(labels, t3, rows)
        d1 = alpha_over(t3_by, rows, t3)
        lo, hi, _ = cluster_bootstrap(rows, lambda rr: alpha_over(t3_by, rr, t3),
                                      seed=SEED, iterations=BOOTSTRAP_N)
        res["hypotheses"]["D1"] = {"statistic": d1, "ci": [lo, hi],
                                   "coders": t3,
                                   "verdict": verdict(lo, hi, D1_BAR, D1_BAR)}

    # ---- D2: THE decisive one. Does agreement improve with tier?
    rev3 = json.load(open(REV3))
    t1_alpha = rev3["hypotheses"]["B1"]["statistic"]
    if len(t3) < MIN_PER_TIER:
        res["hypotheses"]["D2"] = {"verdict": "UNAVAILABLE — T3 under-populated"}
    else:
        t3_by = build_units(labels, t3, rows)

        def gap(rr):
            a = alpha_over(t3_by, rr, t3)
            return None if a is None else a - t1_alpha

        d2 = gap(rows)
        lo2, hi2, _ = cluster_bootstrap(rows, gap, seed=SEED, iterations=BOOTSTRAP_N)
        res["hypotheses"]["D2"] = {
            "statistic": d2, "ci": [lo2, hi2],
            "alpha_T3": alpha_over(t3_by, rows, t3), "alpha_T1_rev3": t1_alpha,
            "verdict": verdict(lo2, hi2, D2_BAR, D2_FALSIFY),
            "reading": ("CONFIRMED means the rev 3.1 null is about SCALE; "
                        "REFUTED means it is about the TAXONOMY"),
        }

    # ---- D3: is the gradient monotone? descriptive, no threshold.
    tiers = {"T1 (rev 3.1, open-weight small)": t1_alpha}
    for t in ("T2", "T3"):
        cs = by_tier.get(t, [])
        if len(cs) >= 2:
            tb = build_units(labels, cs, rows)
            tiers[f"{t} ({len(cs)} coders)"] = alpha_over(tb, rows, cs)
        else:
            tiers[f"{t} ({len(cs)} coders)"] = None
    res["hypotheses"]["D3"] = {"tier_alphas": tiers,
                               "verdict": "DESCRIPTIVE — no threshold"}

    # ---- D4: concordance with the published labels
    def concordance(coder, rr):
        units = []
        for r in rr:
            if (coder, r) not in labels:
                continue
            for cell in CELLS:
                units.append({coder: labels[(coder, r)][cell],
                              "published": published[r][cell]})
        return alpha_nominal(units)

    marginals = {c: marked_proportion(labels, c, rows) for c in coders}
    d4_coders = [c for c in t3
                 if marginals[c] is not None
                 and D4_MARGINAL_LO <= marginals[c] <= D4_MARGINAL_HI]
    if len(t3) < MIN_PER_TIER or not d4_coders:
        res["hypotheses"]["D4"] = {"verdict": "UNAVAILABLE", "marginals": marginals}
    else:
        t3_by = build_units(labels, t3, rows)

        def d4_stat(rr):
            pooled = alpha_over(t3_by, rr, t3)
            cs = [concordance(c, rr) for c in d4_coders]
            cs = [x for x in cs if x is not None]
            if pooled is None or not cs:
                return None
            return pooled - sum(cs) / len(cs)

        d4 = d4_stat(rows)
        lo4, hi4, _ = cluster_bootstrap(rows, d4_stat, seed=SEED, iterations=BOOTSTRAP_N)
        res["hypotheses"]["D4"] = {
            "statistic": d4, "ci": [lo4, hi4], "coders_included": d4_coders,
            "excluded_by_marginal": {c: marginals[c] for c in t3 if c not in d4_coders},
            "marginals": marginals,
            "verdict": verdict(lo4, hi4, D4_BAR, D4_FALSIFY),
            "bound": "concordance with a label set scoring alpha=0.047 against "
                     "itself; never accuracy",
        }

    # ---- D5 + family, secondary, no thresholds
    pairs = {}
    for i, a in enumerate(coders):
        for b in coders[i + 1:]:
            pairs[(a, b)] = alpha_over(by_trace, rows, [a, b])
    cross = [v for (a, b), v in pairs.items() if TIER[a] != TIER[b] and v is not None]
    res["secondary"]["D5_cross_tier_T2_T3"] = (
        sum(cross) / len(cross) if cross else None)

    fam = collections.defaultdict(list)
    for (a, b), v in pairs.items():
        if v is None:
            continue
        fam["within" if FAMILY[a] == FAMILY[b] else "between"].append(v)
    res["secondary"]["family_within"] = (
        sum(fam["within"]) / len(fam["within"]) if fam["within"] else None)
    res["secondary"]["family_between"] = (
        sum(fam["between"]) / len(fam["between"]) if fam["between"] else None)
    res["secondary"]["family_n_within_pairs"] = len(fam["within"])
    res["secondary"]["pairwise"] = {f"{a}-{b}": v for (a, b), v in pairs.items()}

    print("\n" + "=" * 76)
    for name, h in res["hypotheses"].items():
        stat = h.get("statistic")
        ci = h.get("ci")
        s = "—" if stat is None else f"{stat:.3f}"
        c = "" if not ci or ci[0] is None else f"  [{ci[0]:.3f}, {ci[1]:.3f}]"
        print(f"{name}  {s:>7}{c:<22}  {h['verdict']}")
    print("=" * 76)
    print("tier alphas:")
    for k, v in res["hypotheses"]["D3"]["tier_alphas"].items():
        print(f"   {k:<34} {'—' if v is None else f'{v:.4f}'}")
    print(f"cross-tier T2-T3: {res['secondary']['D5_cross_tier_T2_T3']}")

    json.dump(res, open(OUT, "w"), indent=1, default=float)
    print("wrote", OUT.relative_to(BASE))


if __name__ == "__main__":
    main()
