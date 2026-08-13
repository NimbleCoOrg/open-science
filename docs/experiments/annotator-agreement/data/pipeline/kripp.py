#!/usr/bin/env python3
"""Krippendorff's alpha (nominal) with cluster bootstrap CIs.

Written for the disagreement-structure study
(experiments/prereg-2026-08-07-disagreement-structure.md), which needs an
agreement statistic that handles more than two coders and missing cells.

Deliberately dependency-free and self-testing: `python3 pipeline/kripp.py`
validates against Krippendorff's canonical worked example (nominal alpha
0.691) before any study code is allowed to trust it. The lab has been bitten
by generators that validated their own fabrications, so the instrument is
checked against a value that was published outside this repo.

Reliability data are passed as a list of units, each a mapping
{coder_id: value}; absent coders are missing, not a category.
"""
from __future__ import annotations

import random
from collections import Counter
from typing import Hashable, Iterable, Mapping, Sequence

Unit = Mapping[Hashable, Hashable]


def alpha_nominal(units: Sequence[Unit]) -> float | None:
    """Nominal Krippendorff's alpha.

    Returns None when alpha is undefined: fewer than two pairable values, or
    every value identical (expected disagreement zero, so the ratio is 0/0).
    Callers must treat None as "not estimable", never as 0.0 or 1.0.
    """
    # Coincidence matrix. Only units with >= 2 codings are pairable.
    coincidence: Counter[tuple[Hashable, Hashable]] = Counter()
    for unit in units:
        values = list(unit.values())
        m = len(values)
        if m < 2:
            continue
        for i, c in enumerate(values):
            for j, k in enumerate(values):
                if i != j:
                    coincidence[(c, k)] += 1.0 / (m - 1)

    if not coincidence:
        return None

    marginals: Counter[Hashable] = Counter()
    for (c, k), v in coincidence.items():
        marginals[c] += v
    n = sum(marginals.values())
    if n < 2:
        return None

    observed = sum(v for (c, k), v in coincidence.items() if c != k)
    expected = sum(
        nc * nk for c, nc in marginals.items() for k, nk in marginals.items() if c != k
    )
    if expected == 0:
        return None  # single category: alpha undefined, not perfect
    return 1.0 - (n - 1) * observed / expected


def bootstrap_ci(
    clusters: Sequence[Sequence[Unit]],
    seed: int,
    iterations: int = 2000,
    level: float = 0.95,
) -> tuple[float | None, float | None, int]:
    """Percentile CI, resampling whole clusters (traces) with replacement.

    Units inside a trace are not independent — the same annotator judges every
    cell of it — so the trace is the resampling unit, not the cell. Returns
    (low, high, n_estimable); replicates where alpha is undefined are dropped
    and counted rather than coerced to a number.
    """
    rng = random.Random(seed)
    n = len(clusters)
    if n == 0:
        return None, None, 0

    estimates: list[float] = []
    for _ in range(iterations):
        drawn = [clusters[rng.randrange(n)] for _ in range(n)]
        units = [u for cluster in drawn for u in cluster]
        a = alpha_nominal(units)
        if a is not None:
            estimates.append(a)

    if len(estimates) < iterations * 0.5:
        # Too unstable to quote an interval honestly.
        return None, None, len(estimates)

    estimates.sort()
    tail = (1.0 - level) / 2.0
    lo = estimates[int(tail * (len(estimates) - 1))]
    hi = estimates[int((1.0 - tail) * (len(estimates) - 1))]
    return lo, hi, len(estimates)


def percent_agreement(units: Sequence[Unit]) -> float | None:
    """Mean pairwise percent agreement, reported alongside alpha.

    Alpha is chance-corrected and collapses toward 0 on skewed marginals; raw
    agreement is reported next to it so a low alpha on a near-constant cell is
    legible rather than alarming.
    """
    agree = total = 0
    for unit in units:
        values = list(unit.values())
        for i in range(len(values)):
            for j in range(i + 1, len(values)):
                total += 1
                agree += values[i] == values[j]
    return agree / total if total else None


def _self_test() -> None:
    """Validate against Krippendorff's canonical nominal example."""
    na = None
    # 15 units x 3 observers, the reliability matrix distributed with
    # Krippendorff's own worked example; published nominal alpha 0.691.
    observers = {
        "A": [na, na, na, na, na, 3, 4, 1, 2, 1, 1, 3, 3, na, 3],
        "B": [1, na, 2, 1, 3, 3, 4, 3, na, na, na, na, na, na, na],
        "C": [na, na, 2, 1, 3, 4, 4, na, 2, 1, 1, 3, 3, na, 4],
    }
    units: list[dict[str, Hashable]] = []
    for idx in range(15):
        unit = {o: vals[idx] for o, vals in observers.items() if vals[idx] is not na}
        units.append(unit)

    got = alpha_nominal(units)
    expected = 0.691
    assert got is not None, "alpha came back undefined on the canonical example"
    assert abs(got - expected) < 0.001, f"expected ~{expected}, got {got!r}"

    # Degenerate cases must return None, not a flattering number.
    assert alpha_nominal([{"a": 1, "b": 1}, {"a": 1, "b": 1}]) is None, (
        "single-category data must be undefined, not alpha=1"
    )
    assert alpha_nominal([{"a": 1}]) is None, "unpairable data must be undefined"

    # Perfect agreement across two categories is alpha = 1.
    perfect = [{"a": 0, "b": 0}] * 5 + [{"a": 1, "b": 1}] * 5
    assert abs(alpha_nominal(perfect) - 1.0) < 1e-9

    print(f"kripp self-test OK: canonical alpha = {got:.4f} (expected {expected})")


if __name__ == "__main__":
    _self_test()
