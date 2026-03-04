import json

import click


KNOWN_FIELDS = {"id", "input", "expected", "description", "tags", "metadata"}
MAX_ERRORS = 50


def _python_type_to_json_name(value) -> str:
    """Convert a Python value to its JSON type name."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "number"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def validate_jsonl(file_path: str) -> int:
    """Validate a JSONL evaluation set file.

    Returns:
        0: No errors (warnings may be present).
        1: One or more schema errors found.
        2: Execution error (file not found, unreadable, or permission denied).
    """
    # Criterion 1: File exists and is readable
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw_lines = f.readlines()
    except FileNotFoundError:
        click.echo(f"✗ File not found: {file_path}")
        return 2
    except PermissionError:
        click.echo(f"✗ Permission denied: {file_path}")
        return 2
    except OSError as e:
        click.echo(f"✗ Cannot read file {file_path}: {e}")
        return 2

    # Criterion 2: File is not empty (after stripping blank lines)
    if not any(line.strip() for line in raw_lines):
        click.echo("✗ File is empty: no cases found.")
        return 1

    errors = []
    warnings = []
    seen_ids: dict = {}
    case_count = 0
    additional_errors = 0

    def add_error(msg: str) -> None:
        nonlocal additional_errors
        if len(errors) >= MAX_ERRORS:
            additional_errors += 1
        else:
            errors.append(msg)

    for line_num, line in enumerate(raw_lines, start=1):
        # Blank line policy: skip silently
        if not line.strip():
            continue

        # Criterion 3: Every non-blank line is valid JSON
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            add_error(f"✗ Line {line_num}: invalid JSON")
            continue  # Skip criteria 4-8 for this line

        # Criterion 4: Top-level structure is a JSON object
        if not isinstance(data, dict):
            json_type = _python_type_to_json_name(data)
            add_error(f"✗ Line {line_num}: expected a JSON object, got {json_type}")
            continue  # Skip criteria 5-8 for this line

        case_count += 1

        # Determine if id is present and valid for labelling purposes
        id_present = "id" in data
        raw_id = data.get("id")
        # id_valid: present, a string (not bool), and non-empty
        id_valid = (
            id_present
            and not isinstance(raw_id, bool)
            and isinstance(raw_id, str)
            and raw_id != ""
        )

        def case_label() -> str:
            if id_valid:
                return f'Line {line_num} (case "{raw_id}")'
            return f"Line {line_num}"

        # Criterion 5: Required fields are present
        missing = [f for f in ("id", "input", "expected") if f not in data]
        if missing:
            add_error(
                f"✗ {case_label()}: missing required field(s): {', '.join(missing)}"
            )

        # Criterion 6: ID is a non-empty string and unique
        if id_present:
            if isinstance(raw_id, bool):
                add_error(
                    f'✗ Line {line_num}: "id" must be a non-empty string, got boolean'
                )
            elif not isinstance(raw_id, str):
                json_type = _python_type_to_json_name(raw_id)
                add_error(
                    f'✗ Line {line_num}: "id" must be a non-empty string, got {json_type}'
                )
            elif raw_id == "":
                add_error(
                    f'✗ Line {line_num}: "id" must be a non-empty string, got empty string'
                )
            else:
                # Valid string ID: track for duplicate detection
                seen_ids.setdefault(raw_id, []).append(line_num)

        # Criterion 7: input and expected are JSON objects
        for field in ("input", "expected"):
            if field in data:
                value = data[field]
                if not isinstance(value, dict):
                    json_type = _python_type_to_json_name(value)
                    add_error(
                        f'✗ {case_label()}: "{field}" must be an object, got {json_type}'
                    )

        # Criterion 8: Unrecognised fields generate warnings
        for field in data:
            if field not in KNOWN_FIELDS:
                warnings.append(
                    f'⚠ {case_label()}: unrecognised field "{field}"'
                )

    # Criterion 6 continued: Duplicate ID detection (after processing all lines)
    for dup_id, line_nums in sorted(seen_ids.items(), key=lambda x: x[1][0]):
        if len(line_nums) > 1:
            lines_str = ", ".join(str(n) for n in line_nums)
            add_error(f'✗ Duplicate id "{dup_id}" found at lines {lines_str}')

    # Output: warnings before errors (criterion 8 ordering)
    for warning in warnings:
        click.echo(warning)
    for error in errors:
        click.echo(error)

    # Truncation notice (criterion 10)
    if additional_errors > 0:
        click.echo(
            f"✗ 50 errors reported. {additional_errors} additional errors not shown."
            " Fix the listed errors first then re-run."
        )

    # Success messages
    has_errors = errors or additional_errors > 0
    if not has_errors:
        if warnings:
            click.echo(f"⚠ {len(warnings)} warning(s). See above.")
        click.echo(f"✓ {case_count} cases validated. No errors.")
        return 0

    return 1
