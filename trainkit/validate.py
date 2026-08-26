from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

ERROR_LIMIT_DEFAULT = 50

KNOWN_FIELDS = {"id", "input", "expected", "description", "tags", "metadata"}


def json_type_name(value: Any) -> str:
    """Return JSON type name, not Python type name."""
    if value is None:
        return "null"
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


@dataclass
class Issue:
    line: Optional[int]
    is_warning: bool
    message: str


@dataclass
class ValidationResult:
    case_count: int
    warnings: List[Issue]
    errors: List[Issue]
    truncated: bool
    suppressed_error_count: int


class _DuplicateTracker:
    """
    Tracks duplicate IDs. Post-processes messages after the main loop
    rather than mutating Issue objects in place.
    """

    def __init__(self) -> None:
        self.lines_by_id: Dict[str, List[int]] = {}

    def note(self, case_id: str, line_no: int) -> None:
        self.lines_by_id.setdefault(case_id, []).append(line_no)

    def duplicate_issues(self) -> List[Issue]:
        """
        Called once after the main loop. Returns one Issue per duplicated ID,
        with all line numbers. No in-place mutation of shared objects.
        """
        issues = []
        for case_id, lines in self.lines_by_id.items():
            if len(lines) > 1:
                joined = ", ".join(str(n) for n in lines)
                issues.append(Issue(
                    line=None,
                    is_warning=False,
                    message=f'✗ Duplicate id "{case_id}" found at lines {joined}',
                ))
        return issues


def _valid_case_id(value: Any) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Returns (is_valid, valid_id, invalid_detail).
    Whitespace-only strings are reported accurately, not as empty string.
    """
    if isinstance(value, str):
        if not value.strip():
            if value == "":
                return (False, None, 'empty string ""')
            return (False, None, f'whitespace-only string "{value}"')
        return (True, value, None)
    return (False, None, json_type_name(value))


def _line_prefix(line_no: int, case_id: Optional[str]) -> str:
    if case_id:
        return f'✗ Line {line_no} (case "{case_id}"): '
    return f"✗ Line {line_no}: "


def _warning_prefix(line_no: int, case_id: Optional[str]) -> str:
    if case_id:
        return f'⚠ Line {line_no} (case "{case_id}"): '
    return f"⚠ Line {line_no}: "


def validate_jsonl_content(
    content: str,
    error_limit: int = ERROR_LIMIT_DEFAULT,
) -> ValidationResult:
    """
    Pure validation logic. Accepts content as a string.
    File reading is handled entirely by the caller.
    """
    warnings: List[Issue] = []
    errors: List[Issue] = []
    case_count = 0
    truncated = False
    suppressed = 0
    dup = _DuplicateTracker()

    def add_error(issue: Issue) -> None:
        nonlocal truncated, suppressed
        if len(errors) < error_limit:
            errors.append(issue)
        else:
            truncated = True
            suppressed += 1

    def add_line_error(line_no: int, case_id: Optional[str], description: str) -> None:
        add_error(Issue(
            line=line_no,
            is_warning=False,
            message=_line_prefix(line_no, case_id) + description,
        ))

    def add_line_warning(line_no: int, case_id: Optional[str], description: str) -> None:
        warnings.append(Issue(
            line=line_no,
            is_warning=True,
            message=_warning_prefix(line_no, case_id) + description,
        ))

    any_non_blank = False

    for idx, raw in enumerate(content.splitlines(), start=1):
        if not raw.strip():
            continue

        any_non_blank = True

        # Criterion 3: valid JSON
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as exc:
            add_line_error(idx, None, f"invalid JSON: {exc.msg}")
            continue

        # Criterion 4: top-level must be object
        if not isinstance(obj, dict):
            got = json_type_name(obj)
            add_line_error(idx, None, f"Top-level JSON must be an object, got {got}")
            continue

        case_count += 1

        # Resolve ID validity once; result is reused below.
        raw_id_present = "id" in obj
        id_is_valid = False
        valid_id: Optional[str] = None
        id_detail: Optional[str] = None

        if raw_id_present:
            id_is_valid, valid_id, id_detail = _valid_case_id(obj["id"])

        # Label to use in error messages (valid string ID only)
        label = valid_id if id_is_valid else None

        # Criterion 8: unrecognised fields -> warnings
        for key in obj:
            if key not in KNOWN_FIELDS:
                add_line_warning(idx, label, f'unrecognised field "{key}"')

        # Criterion 5: required fields
        missing = [k for k in ("id", "input", "expected") if k not in obj]
        if missing:
            add_line_error(idx, label, f"missing required field(s): {', '.join(missing)}")

        # Criterion 6: ID type and uniqueness
        if raw_id_present:
            if not id_is_valid:
                add_line_error(idx, None, f'"id" must be a non-empty string, got {id_detail}')
            else:
                # Duplicate detection only for valid ID strings
                dup.note(valid_id, idx)

        # Criterion 7: input and expected must be objects
        for field_name in ("input", "expected"):
            if field_name in obj and not isinstance(obj[field_name], dict):
                got = json_type_name(obj[field_name])
                add_line_error(idx, label, f'"{field_name}" must be an object, got {got}')

    # Criterion 2: file not empty
    if not any_non_blank:
        add_error(Issue(
            line=None,
            is_warning=False,
            message="✗ File contains no cases (empty or blank lines only)",
        ))

    # Post-loop duplicate resolution, no in-place mutation
    for dup_issue in dup.duplicate_issues():
        add_error(dup_issue)

    return ValidationResult(
        case_count=case_count,
        warnings=warnings,
        errors=errors,
        truncated=truncated,
        suppressed_error_count=suppressed,
    )
