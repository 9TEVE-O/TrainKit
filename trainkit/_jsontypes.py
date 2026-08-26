"""JSON type naming, shared by the metric parser and the schema validator.

Both surfaces report the type of an offending value in user-facing errors, and
both must name it as JSON does. Python's own names leak the implementation:
``str`` for a string, ``dict`` for an object, and — worst of the set — ``bool``
and ``float`` for values JSON calls booleans and numbers.
"""
from __future__ import annotations

from typing import Any


def json_type_name(value: Any) -> str:
    """Return the JSON name for a value's type, not the Python one."""
    if value is None:
        return "null"
    # Must precede the numeric check: bool is a subclass of int.
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__
