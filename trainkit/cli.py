"""CLI entry point for TrainKit."""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import click

from trainkit import __version__
from trainkit.artifacts import (
    DEFAULT_ARTEFACT_DIR,
    build_summary,
    list_runs,
    load_summary,
    make_run_id,
    resolve_run_id,
    run_dir,
    write_run,
)
from trainkit.diff import diff_runs
from trainkit.runner import EXIT_ERROR, run_evaluation
from trainkit.validate import ERROR_LIMIT_DEFAULT, validate_jsonl_content
from trainkit.runtime_bridge import (
    emit_precommit,
    emit_run_completed,
    emit_run_failed,
    emit_run_started,
)


@click.group()
@click.version_option(__version__, prog_name="trainkit")
def main() -> None:
    """TrainKit — reproducible ML model evaluation."""


# ---------------------------------------------------------------------------
# trainkit run
# ---------------------------------------------------------------------------

@main.command("run")
@click.option("--script", default=None, help="Path to evaluation script (script mode).")
@click.option("--cmd", "command", default=None, help="Shell command to run (command mode).")
@click.option("--args", default=None, help="Additional arguments for the script (script mode).")
@click.option(
    "--threshold",
    "thresholds",
    multiple=True,
    metavar="METRIC:VALUE",
    help="Minimum acceptable mean for a metric, e.g. accuracy:0.90.",
)
@click.option("--strict", is_flag=True, default=False, help="Fail on any parse warning.")
@click.option(
    "--output-dir",
    default=str(DEFAULT_ARTEFACT_DIR),
    show_default=True,
    help="Base artefact directory.",
)
def run_cmd(
    script: Optional[str],
    command: Optional[str],
    args: Optional[str],
    thresholds: tuple[str, ...],
    strict: bool,
    output_dir: str,
) -> None:
    """Execute an evaluation script and store results."""
    if script is None and command is None:
        raise click.UsageError("Either --script or --cmd must be provided.")
    if script is not None and command is not None:
        raise click.UsageError("--script and --cmd are mutually exclusive.")

    parsed_thresholds: dict[str, float] = {}
    for spec in thresholds:
        try:
            metric, val = spec.split(":", 1)
            parsed_thresholds[metric.strip()] = float(val.strip())
        except (ValueError, TypeError):
            raise click.BadParameter(
                f"Expected METRIC:VALUE, got {spec!r}", param_hint="--threshold"
            )

    seed = script or command or ""
    pre_start = datetime.now(tz=timezone.utc)
    run_id = make_run_id(pre_start, seed)
    base = Path(output_dir)

    emit_run_started(run_id, script=script, command=command)

    try:
        (
            exit_code,
            results,
            stdout_text,
            stderr_text,
            warnings,
            start_time,
            duration,
            model_hash,
        ) = run_evaluation(
            script=script,
            command=command,
            args=args,
            strict=strict,
            thresholds=parsed_thresholds,
        )
    except FileNotFoundError as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_ERROR)

    if exit_code == EXIT_ERROR and not results:
        emit_run_failed(run_id, reason="Evaluation script exited with non-zero status")
    else:
        emit_run_completed(run_id, exit_code=exit_code, duration_seconds=duration)

    summary = build_summary(
        run_id=run_id,
        timestamp=start_time,
        script=script,
        command=command,
        model_hash=model_hash,
        exit_code=exit_code,
        duration_seconds=duration,
        results=results,
        warnings=warnings,
    )

    emit_precommit(run_id, description="write run artefacts to disk")

    directory = write_run(
        run_id=run_id,
        results=results,
        summary=summary,
        stdout_text=stdout_text,
        stderr_text=stderr_text,
        base=base,
    )

    for warning in warnings:
        click.echo(warning, err=True)

    click.echo(json.dumps(summary, indent=2))
    click.echo(f"\nArtefacts written to: {directory}", err=True)
    sys.exit(exit_code)


# ---------------------------------------------------------------------------
# trainkit list
# ---------------------------------------------------------------------------

@main.command("list")
@click.option(
    "--output-dir",
    default=str(DEFAULT_ARTEFACT_DIR),
    show_default=True,
    help="Base artefact directory.",
)
def list_cmd(output_dir: str) -> None:
    """List all stored evaluation runs."""
    base = Path(output_dir)
    runs = list_runs(base)
    if not runs:
        click.echo("No runs found.")
        return
    for i, run_id in enumerate(runs):
        click.echo(f"[{i}] {run_id}")


# ---------------------------------------------------------------------------
# trainkit show
# ---------------------------------------------------------------------------

@main.command("show")
@click.argument("selector", default="-1")
@click.option(
    "--output-dir",
    default=str(DEFAULT_ARTEFACT_DIR),
    show_default=True,
    help="Base artefact directory.",
)
def show_cmd(selector: str, output_dir: str) -> None:
    """Display the summary for a run.

    SELECTOR is a run index (e.g. 0, -1) or a full timestamp prefix.
    Defaults to the latest run (-1).
    """
    base = Path(output_dir)
    try:
        run_id = resolve_run_id(selector, base)
        summary = load_summary(run_id, base)
    except (ValueError, FileNotFoundError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_ERROR)

    click.echo(json.dumps(summary, indent=2))


# ---------------------------------------------------------------------------
# trainkit diff
# ---------------------------------------------------------------------------

@main.command("diff")
@click.argument("selector_a")
@click.argument("selector_b")
@click.option(
    "--output-dir",
    default=str(DEFAULT_ARTEFACT_DIR),
    show_default=True,
    help="Base artefact directory.",
)
def diff_cmd(selector_a: str, selector_b: str, output_dir: str) -> None:
    """Compare two runs and report metric deltas.

    SELECTOR_A and SELECTOR_B are run indices or full timestamp prefixes.
    """
    base = Path(output_dir)
    try:
        result = diff_runs(selector_a, selector_b, base)
    except (ValueError, FileNotFoundError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_ERROR)

    click.echo(json.dumps(result, indent=2))


# ---------------------------------------------------------------------------
# trainkit clean
# ---------------------------------------------------------------------------

@main.command("clean")
@click.argument("selector", required=False)
@click.option(
    "--older-than",
    default=None,
    metavar="DURATION",
    help="Remove runs older than this duration (e.g. 7d, 24h).",
)
@click.option(
    "--output-dir",
    default=str(DEFAULT_ARTEFACT_DIR),
    show_default=True,
    help="Base artefact directory.",
)
def clean_cmd(
    selector: Optional[str], older_than: Optional[str], output_dir: str
) -> None:
    """Remove one or more stored runs.

    SELECTOR is a run index or timestamp prefix. If --older-than is given,
    all runs older than the specified duration are removed.
    """
    base = Path(output_dir)

    if older_than is not None:
        cutoff = _parse_duration(older_than)
        runs = list_runs(base)
        now = datetime.now(tz=timezone.utc)
        removed = 0
        for run_id in runs:
            ts_str = run_id[:16]  # YYYYMMDDTHHMMSSz
            try:
                ts = datetime.strptime(ts_str, "%Y%m%dT%H%M%SZ").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue
            if (now - ts) > cutoff:
                shutil.rmtree(run_dir(run_id, base))
                click.echo(f"Removed: {run_id}")
                removed += 1
        if removed == 0:
            click.echo("No runs matched.")
        return

    if selector is None:
        raise click.UsageError("Provide a SELECTOR or --older-than.")

    try:
        run_id = resolve_run_id(selector, base)
    except (ValueError, FileNotFoundError) as exc:
        click.echo(f"Error: {exc}", err=True)
        sys.exit(EXIT_ERROR)

    shutil.rmtree(run_dir(run_id, base))
    click.echo(f"Removed: {run_id}")


# ---------------------------------------------------------------------------
# trainkit validate
# ---------------------------------------------------------------------------

@main.command("validate")
@click.argument("path", type=click.Path(path_type=Path, readable=False))
@click.option(
    "--error-limit",
    type=int,
    default=ERROR_LIMIT_DEFAULT,
    show_default=True,
    help="Maximum number of individual errors to report.",
)
def validate_cmd(path: Path, error_limit: int) -> None:
    """Validate an evaluation set JSONL file against TrainKit schema rules."""
    # readable=False above keeps Click from rejecting the path itself, so
    # permission errors surface here with our own message and exit code.
    # Single read attempt; all file errors surface here with exit code 2.
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        click.echo(f"✗ File not found: {path}")
        raise SystemExit(EXIT_ERROR)
    except PermissionError:
        click.echo(f"✗ Cannot read file: {path} (permission denied)")
        raise SystemExit(EXIT_ERROR)
    except UnicodeDecodeError:
        click.echo(f"✗ Cannot read file: {path} (not valid UTF-8)")
        raise SystemExit(EXIT_ERROR)
    except OSError as exc:
        click.echo(f"✗ Cannot read file: {path} ({exc})")
        raise SystemExit(EXIT_ERROR)

    result = validate_jsonl_content(content, error_limit=error_limit)

    # Output order: warnings before errors.
    for warning in result.warnings:
        click.echo(warning.message)
    for error in result.errors:
        click.echo(error.message)

    if result.truncated:
        click.echo(
            f"✗ {error_limit} errors reported. "
            f"{result.suppressed_error_count} additional errors not shown. "
            f"Fix the listed errors first then re-run."
        )
        raise SystemExit(1)

    if result.errors:
        raise SystemExit(1)

    if result.warnings:
        click.echo(f"⚠ {len(result.warnings)} warning(s). See above.")

    click.echo(f"✓ {result.case_count} cases validated. No errors.")
    raise SystemExit(0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_duration(spec: str) -> timedelta:
    """Parse a duration string like ``7d`` or ``24h`` into a timedelta.

    Parameters
    ----------
    spec:
        Duration string ending in ``d`` (days) or ``h`` (hours).

    Returns
    -------
    timedelta

    Raises
    ------
    click.BadParameter
        If the spec is not recognised.
    """
    spec = spec.strip().lower()
    try:
        if spec.endswith("d"):
            return timedelta(days=int(spec[:-1]))
        if spec.endswith("h"):
            return timedelta(hours=int(spec[:-1]))
    except ValueError:
        pass
    raise click.BadParameter(
        f"Unrecognised duration {spec!r}. Use e.g. 7d or 24h.",
        param_hint="--older-than",
    )
