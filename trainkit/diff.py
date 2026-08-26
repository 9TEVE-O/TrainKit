"""Diff semantics for TrainKit.

Compares two runs and reports metric deltas. Run selection uses
integer indices (0-based from oldest, negative from newest) or
run ID prefixes (e.g. ``20260304T142300Z``). Natural-language
aliases (``latest``, ``previous``) are explicitly unsupported.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from trainkit.artifacts import DEFAULT_ARTEFACT_DIR, load_summary, resolve_run_id


def diff_runs(
    selector_a: str,
    selector_b: str,
    base: Path = DEFAULT_ARTEFACT_DIR,
) -> dict[str, Any]:
    """Compare two runs and return a diff dict.

    Parameters
    ----------
    selector_a:
        Index or timestamp prefix identifying the *base* run.
    selector_b:
        Index or timestamp prefix identifying the *compare* run.
    base:
        Base artefact directory.

    Returns
    -------
    dict
        A diff result with ``base_run``, ``compare_run``, and ``deltas``.

    Raises
    ------
    ValueError
        If either selector does not resolve to a run.
    """
    run_id_a = resolve_run_id(selector_a, base)
    run_id_b = resolve_run_id(selector_b, base)

    summary_a = load_summary(run_id_a, base)
    summary_b = load_summary(run_id_b, base)

    metrics_a: dict[str, dict[str, float]] = summary_a.get("metrics", {})
    metrics_b: dict[str, dict[str, float]] = summary_b.get("metrics", {})

    all_metrics = sorted(set(metrics_a) | set(metrics_b))
    deltas: dict[str, Any] = {}
    for metric in all_metrics:
        base_mean = metrics_a[metric]["mean"] if metric in metrics_a else None
        compare_mean = metrics_b[metric]["mean"] if metric in metrics_b else None
        delta = (
            round(compare_mean - base_mean, 6)
            if base_mean is not None and compare_mean is not None
            else None
        )
        deltas[metric] = {
            "base": base_mean,
            "compare": compare_mean,
            "delta": delta,
        }

    return {
        "base_run": run_id_a,
        "compare_run": run_id_b,
        "deltas": deltas,
    }
