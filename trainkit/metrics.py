"""Metric validation for TrainKit.

Built-in metrics have defined expected ranges. Values outside those ranges
emit a warning. Type mismatches and empty required fields are fatal parse
errors (exit code 2, or skipped with a warning in non-strict mode).
"""
from __future__ import annotations

import json
import math
from typing import Any

from trainkit._jsontypes import json_type_name

# Metric name → (min_value, max_value) or None for unbounded
_BUILTIN_METRICS: dict[str, tuple[float | None, float | None]] = {
    "accuracy":  (0.0, 1.0),
    "f1":        (0.0, 1.0),
    "precision": (0.0, 1.0),
    "recall":    (0.0, 1.0),
    "loss":      (0.0, None),
    "bleu":      (0.0, 1.0),
    "rouge":     (0.0, 1.0),
}

REQUIRED_FIELDS = ("id", "metric", "value")


class ParseError(Exception):
    """Raised when a result line cannot be parsed."""


class MissingFieldError(Exception):
    """Raised when a required field is absent from a result line."""


def parse_result_line(line: str) -> dict[str, Any]:
    """Parse one JSON line of evaluation output.

    Parameters
    ----------
    line:
        A single JSON object string from evaluation script stdout.

    Returns
    -------
    dict
        Parsed and validated result object.

    Raises
    ------
    ParseError
        If the line is not valid JSON, or if a required field has a type
        mismatch (e.g. ``value`` is a string instead of a number), or if
        a required field is an empty string.
    MissingFieldError
        If a required field (``id``, ``metric``, or ``value``) is absent.
    """
    line = line.strip()
    if not line:
        raise ParseError("Empty line")

    try:
        obj = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ParseError(f"Invalid JSON: {exc}") from exc

    if not isinstance(obj, dict):
        raise ParseError("Expected a JSON object, got a scalar or array")

    # Check for missing required fields
    for field in REQUIRED_FIELDS:
        if field not in obj:
            raise MissingFieldError(f"Missing required field: {field!r}")

    # Validate types and empty-string guard
    if not isinstance(obj["id"], str) or obj["id"] == "":
        raise ParseError("Field 'id' must be a non-empty string")
    if not isinstance(obj["metric"], str) or obj["metric"] == "":
        raise ParseError("Field 'metric' must be a non-empty string")
    if not isinstance(obj["value"], (int, float)) or isinstance(obj["value"], bool):
        raise ParseError(
            f"Field 'value' must be a number, got {json_type_name(obj['value'])}"
        )
    # json.loads accepts NaN/Infinity as floats. They compare false against
    # every bound, so they would slip past range checks and threshold gates,
    # and json.dump would then write non-standard JSON into summary.json.
    if not math.isfinite(obj["value"]):
        raise ParseError(
            f"Field 'value' must be a finite number, got {obj['value']}"
        )

    return obj


def validate_metric_range(metric: str, value: float) -> str | None:
    """Check whether a value is within the expected range for a built-in metric.

    Parameters
    ----------
    metric:
        Metric name string.
    value:
        Numeric metric value.

    Returns
    -------
    str or None
        A warning message if the value is out of range, ``None`` otherwise.
        Custom (non-built-in) metrics always return ``None``.
    """
    if metric not in _BUILTIN_METRICS:
        return None
    lo, hi = _BUILTIN_METRICS[metric]
    if lo is not None and value < lo:
        return f"Metric {metric!r} value {value} is below minimum {lo}"
    if hi is not None and value > hi:
        return f"Metric {metric!r} value {value} is above maximum {hi}"
    return None
