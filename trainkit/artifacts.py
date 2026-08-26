"""Artefact directory management for TrainKit.

Layout::

    .trainkit/
    └── runs/
        └── <run_id>/
            ├── results.jsonl
            ├── summary.json
            ├── stdout.log
            └── stderr.log

Run IDs are ``<ISO8601_UTC_compact>_<sha256_prefix_8chars>``, e.g.
``20260304T142300Z_e3b0c442``.
"""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import trainkit

DEFAULT_ARTEFACT_DIR = Path(".trainkit") / "runs"


def make_run_id(timestamp: datetime, seed: str) -> str:
    """Create a run directory name from a UTC timestamp and a seed string.

    Parameters
    ----------
    timestamp:
        UTC datetime for the run start.
    seed:
        A string used to derive the 8-character hex suffix (e.g. script path
        or command string).

    Returns
    -------
    str
        Run ID of the form ``YYYYMMDDTHHMMSSZ_xxxxxxxx``.
    """
    ts = timestamp.strftime("%Y%m%dT%H%M%SZ")
    suffix = hashlib.sha256(seed.encode()).hexdigest()[:8]
    return f"{ts}_{suffix}"


def run_dir(run_id: str, base: Path = DEFAULT_ARTEFACT_DIR) -> Path:
    """Return the directory path for a given run ID."""
    return base / run_id


def reserve_run_id(
    timestamp: datetime, seed: str, base: Path = DEFAULT_ARTEFACT_DIR
) -> str:
    """Atomically claim an unused run directory and return its ID.

    ``make_run_id`` is deterministic: the same seed evaluated twice within the
    same second produces the same ID. Without disambiguation the second run
    would reuse the first run's directory and overwrite its artefacts. When the
    base ID is already taken, a discriminator is appended (``<run_id>-002``,
    ``<run_id>-003``, ...) so each run keeps its own artefacts.

    The claim is the ``mkdir`` itself rather than an existence check followed by
    a later write. Evaluation can take minutes, so a check-then-act would let
    two concurrent runs pass the same check and only collide at write time,
    by which point the loser has already spent its work. Here the filesystem
    picks the winner and the loser immediately tries the next discriminator.

    The directory is created empty; ``write_run`` fills it. A caller that
    aborts before writing should remove it (see ``discard_run_id``).

    The timestamp portion is left untouched, so run selection by timestamp
    prefix continues to match every run started in that second.
    """
    run_id = make_run_id(timestamp, seed)
    counter = 1
    while True:
        candidate = run_id if counter == 1 else f"{run_id}-{counter:03d}"
        try:
            run_dir(candidate, base).mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            counter += 1


def discard_run_id(run_id: str, base: Path = DEFAULT_ARTEFACT_DIR) -> None:
    """Release a reservation made by ``reserve_run_id`` that was never written.

    Removes the directory only while it is still empty, so a directory that
    already holds artefacts is never destroyed by a cleanup path.
    """
    directory = run_dir(run_id, base)
    try:
        directory.rmdir()
    except OSError:
        # Non-empty (it holds artefacts) or already gone. Either way, leave it.
        pass


def write_run(
    *,
    run_id: str,
    results: list[dict[str, Any]],
    summary: dict[str, Any],
    stdout_text: str,
    stderr_text: str,
    base: Path = DEFAULT_ARTEFACT_DIR,
) -> Path:
    """Write all artefacts for a completed run to disk.

    Parameters
    ----------
    run_id:
        The run identifier (used as directory name).
    results:
        List of parsed result dicts to write as JSONL.
    summary:
        Run summary dict to write as JSON.
    stdout_text:
        Full stdout captured from the evaluation script.
    stderr_text:
        Full stderr captured from the evaluation script.
    base:
        Base artefact directory; defaults to ``.trainkit/runs``.

    Returns
    -------
    Path
        The run directory that was created.
    """
    directory = run_dir(run_id, base)
    # The directory may already exist because reserve_run_id created it, so the
    # guard is emptiness rather than absence: an ID whose directory already
    # holds artefacts belongs to another run, and writing would destroy it.
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.iterdir()):
        raise FileExistsError(
            f"Run directory {directory} already contains artefacts"
        )

    results_path = directory / "results.jsonl"
    with results_path.open("w", encoding="utf-8") as fh:
        for row in results:
            fh.write(json.dumps(row) + "\n")

    summary_path = directory / "summary.json"
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")

    (directory / "stdout.log").write_text(stdout_text, encoding="utf-8")
    (directory / "stderr.log").write_text(stderr_text, encoding="utf-8")

    return directory


def build_summary(
    *,
    run_id: str,
    timestamp: datetime,
    script: str | None,
    command: str | None,
    model_hash: str | None,
    exit_code: int,
    duration_seconds: float,
    results: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any]:
    """Construct the run summary dict.

    Parameters
    ----------
    run_id:
        The run identifier.
    timestamp:
        UTC start time of the run.
    script:
        Path to the evaluation script, or ``None`` in command mode.
    command:
        Full shell command, or ``None`` in script mode.
    model_hash:
        SHA-256 hex digest of the script file (script mode only), or ``None``.
    exit_code:
        Exit code returned by the evaluation script.
    duration_seconds:
        Wall-clock duration of the script execution.
    results:
        Parsed result dicts for aggregate metric calculation.
    warnings:
        Warning messages emitted during the run.

    Returns
    -------
    dict
        Fully populated summary dict matching the spec.
    """
    metrics_agg: dict[str, dict[str, Any]] = {}
    for row in results:
        name = row["metric"]
        val = float(row["value"])
        if name not in metrics_agg:
            metrics_agg[name] = {"values": []}
        metrics_agg[name]["values"].append(val)

    metrics_out: dict[str, Any] = {}
    for name, agg in metrics_agg.items():
        vals = agg["values"]
        metrics_out[name] = {
            "mean": sum(vals) / len(vals),
            "min": min(vals),
            "max": max(vals),
            "count": len(vals),
        }

    return {
        "run_id": run_id,
        "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
        "script": script,
        "command": command,
        "model_hash": model_hash,
        "exit_code": exit_code,
        "duration_seconds": round(duration_seconds, 3),
        "metrics": metrics_out,
        "warnings": warnings,
        "trainkit_version": trainkit.__version__,
        "python_version": sys.version,
        "platform": platform.platform(),
    }


def _run_sort_key(run_id: str) -> tuple[str, int]:
    """Sort key placing a run's discriminated siblings in creation order.

    Run IDs sort chronologically as plain strings because the timestamp leads
    and is fixed-width, but the collision discriminator must be compared as a
    number: as text ``-010`` precedes ``-002``, which would make ``list_runs``
    non-chronological and let a selector like ``-1`` resolve to the wrong run.
    """
    stem, sep, suffix = run_id.rpartition("-")
    if sep and suffix.isdigit():
        return (stem, int(suffix))
    return (run_id, 1)


def list_runs(base: Path = DEFAULT_ARTEFACT_DIR) -> list[str]:
    """Return sorted list of run IDs in the artefact directory (oldest first).

    Parameters
    ----------
    base:
        Base artefact directory.

    Returns
    -------
    list[str]
        Run IDs in ascending chronological order.
    """
    if not base.exists():
        return []
    return sorted(
        (d.name for d in base.iterdir() if d.is_dir() and (d / "summary.json").exists()),
        key=_run_sort_key,
    )


def load_summary(run_id: str, base: Path = DEFAULT_ARTEFACT_DIR) -> dict[str, Any]:
    """Load a run summary from disk.

    Parameters
    ----------
    run_id:
        The run identifier.
    base:
        Base artefact directory.

    Returns
    -------
    dict
        Parsed summary JSON.

    Raises
    ------
    FileNotFoundError
        If the run does not exist.
    """
    path = run_dir(run_id, base) / "summary.json"
    if not path.exists():
        raise FileNotFoundError(f"No run found with ID {run_id!r}")
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def resolve_run_id(selector: str, base: Path = DEFAULT_ARTEFACT_DIR) -> str:
    """Resolve a run selector (index or run ID prefix) to a run ID.

    Parameters
    ----------
    selector:
        An integer index (e.g. ``"0"``, ``"-1"``) or a prefix of a run ID
        (e.g. the compact timestamp ``"20260304T142300Z"``).
    base:
        Base artefact directory.

    Returns
    -------
    str
        The resolved run ID.

    Raises
    ------
    ValueError
        If the selector does not resolve to a run.
    """
    runs = list_runs(base)
    if not runs:
        raise ValueError("No runs found in the artefact directory")

    # Try integer index
    try:
        idx = int(selector)
        return runs[idx]
    except (ValueError, IndexError):
        pass

    # Try timestamp prefix match
    matches = [r for r in runs if r.startswith(selector)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            f"Selector {selector!r} is ambiguous: matches {matches}"
        )
    raise ValueError(f"No run found matching selector {selector!r}")
