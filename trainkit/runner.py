"""Model execution runner for TrainKit.

Supports two modes:
- Script mode: ``trainkit run --script path/to/eval.py``
- Command mode: ``trainkit run --cmd "python eval.py --config cfg.yaml"``
"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trainkit.metrics import MissingFieldError, ParseError, parse_result_line, validate_metric_range

# Exit codes
EXIT_OK = 0
EXIT_THRESHOLD = 1
EXIT_ERROR = 2


def hash_script(script_path: Path) -> str:
    """Compute the SHA-256 digest of a script file.

    Parameters
    ----------
    script_path:
        Path to the evaluation script.

    Returns
    -------
    str
        Hex digest string prefixed with ``sha256:``.
    """
    digest = hashlib.sha256(script_path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def run_evaluation(
    *,
    script: str | None = None,
    command: str | None = None,
    args: str | None = None,
    strict: bool = False,
    thresholds: dict[str, float] | None = None,
) -> tuple[int, list[dict[str, Any]], str, str, list[str], datetime, float, str | None]:
    """Execute an evaluation script or command and capture its output.

    Parameters
    ----------
    script:
        Path to a Python evaluation script (script mode).
    command:
        Shell command string (command mode).
    args:
        Additional arguments appended to the script command (script mode only).
    strict:
        If ``True``, any parse warning causes the run to fail with exit code 2.
    thresholds:
        Mapping of metric name to minimum acceptable mean value. If any
        metric mean falls below its threshold, the run exits with code 1.

    Returns
    -------
    tuple
        ``(exit_code, results, stdout_text, stderr_text, warnings,
        start_time, duration_seconds, model_hash)``

    Raises
    ------
    ValueError
        If neither ``script`` nor ``command`` is provided, or if both are.
    """
    if script is None and command is None:
        raise ValueError("Either --script or --cmd must be provided")
    if script is not None and command is not None:
        raise ValueError("--script and --cmd are mutually exclusive")

    model_hash: str | None = None

    if script is not None:
        script_path = Path(script)
        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")
        model_hash = hash_script(script_path)
        cmd: list[str] = [sys.executable, str(script_path)]
        if args:
            import shlex
            cmd.extend(shlex.split(args))
    else:
        cmd = ["sh", "-c", command]  # type: ignore[list-item]

    start_time = datetime.now(tz=timezone.utc)
    t0 = time.monotonic()

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    duration = time.monotonic() - t0
    stdout_text = proc.stdout
    stderr_text = proc.stderr

    warnings: list[str] = []
    results: list[dict[str, Any]] = []

    if proc.returncode != 0:
        return (
            EXIT_ERROR,
            results,
            stdout_text,
            stderr_text,
            warnings,
            start_time,
            duration,
            model_hash,
        )

    # Parse stdout lines
    for lineno, line in enumerate(stdout_text.splitlines(), start=1):
        line = line.strip()
        if not line:
            # Treat empty lines as parse errors to enforce "one JSON object per line"
            exc = ParseError("Empty line")
            msg = f"Line {lineno}: {exc}"
            if strict:
                warnings.append(msg)
                return (
                    EXIT_ERROR,
                    results,
                    stdout_text,
                    stderr_text,
                    warnings,
                    start_time,
                    duration,
                    model_hash,
                )
            warnings.append(f"WARNING — {msg} (line skipped)")
            continue
        try:
            row = parse_result_line(line)
        except (ParseError, MissingFieldError) as exc:
            msg = f"Line {lineno}: {exc}"
            if strict:
                warnings.append(msg)
                return (
                    EXIT_ERROR,
                    results,
                    stdout_text,
                    stderr_text,
                    warnings,
                    start_time,
                    duration,
                    model_hash,
                )
            warnings.append(f"WARNING — {msg} (line skipped)")
            continue

        # Range check for built-in metrics
        range_warning = validate_metric_range(row["metric"], float(row["value"]))
        if range_warning:
            warnings.append(f"WARNING — Line {lineno}: {range_warning}")

        results.append(row)

    # Threshold enforcement
    exit_code = EXIT_OK
    if thresholds and results:
        metric_values: dict[str, list[float]] = {}
        for row in results:
            metric_values.setdefault(row["metric"], []).append(float(row["value"]))

        for metric, minimum in thresholds.items():
            vals = metric_values.get(metric)
            if vals is None:
                warnings.append(
                    f"WARNING — Threshold set for {metric!r} but no values found"
                )
                continue
            mean_val = sum(vals) / len(vals)
            if mean_val < minimum:
                warnings.append(
                    f"Threshold breach: {metric!r} mean {mean_val:.4f} < {minimum}"
                )
                exit_code = EXIT_THRESHOLD

    return (
        exit_code,
        results,
        stdout_text,
        stderr_text,
        warnings,
        start_time,
        duration,
        model_hash,
    )
