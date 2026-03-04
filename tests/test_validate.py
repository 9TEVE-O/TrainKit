"""Tests for trainkit validate command.

One test per acceptance criterion (as required), plus tests for each fixture.
"""
import os
import tempfile

import pytest
from click.testing import CliRunner

from trainkit.cli import cli

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def run_validate(path: str):
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", path])
    return result


# ---------------------------------------------------------------------------
# Criterion 1 — File exists and is readable
# ---------------------------------------------------------------------------


def test_criterion1_file_not_found():
    """Non-existent path exits with code 2."""
    result = run_validate(os.path.join(FIXTURES, "file_not_found"))
    assert result.exit_code == 2
    assert "File not found" in result.output


def test_criterion1_unreadable_file():
    """Unreadable file (no permissions) exits with code 2."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
        f.write(b'{"id": "x", "input": {}, "expected": {}}\n')
        path = f.name
    try:
        os.chmod(path, 0o000)
        result = run_validate(path)
        assert result.exit_code == 2
    finally:
        os.chmod(path, 0o644)
        os.unlink(path)


# ---------------------------------------------------------------------------
# Criterion 2 — File is not empty
# ---------------------------------------------------------------------------


def test_criterion2_empty_file():
    """Empty file exits with code 1."""
    result = run_validate(os.path.join(FIXTURES, "empty_file.jsonl"))
    assert result.exit_code == 1
    assert "empty" in result.output.lower()


def test_criterion2_blank_lines_only():
    """File with only blank lines exits with code 1."""
    result = run_validate(os.path.join(FIXTURES, "blank_lines_only.jsonl"))
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Criterion 3 — Every non-blank line is valid JSON
# ---------------------------------------------------------------------------


def test_criterion3_invalid_json():
    """Invalid JSON lines are reported with line number; valid lines still processed."""
    result = run_validate(os.path.join(FIXTURES, "invalid_json.jsonl"))
    assert result.exit_code == 1
    assert "Line 2" in result.output
    assert "invalid JSON" in result.output


# ---------------------------------------------------------------------------
# Criterion 4 — Top-level structure is a JSON object
# ---------------------------------------------------------------------------


def test_criterion4_top_level_array():
    """Top-level JSON array is reported with correct type."""
    result = run_validate(os.path.join(FIXTURES, "top_level_array.jsonl"))
    assert result.exit_code == 1
    assert "array" in result.output


def test_criterion4_top_level_string():
    """Top-level JSON string is reported with correct type."""
    result = run_validate(os.path.join(FIXTURES, "top_level_string.jsonl"))
    assert result.exit_code == 1
    assert "string" in result.output


def test_criterion4_top_level_number():
    """Top-level JSON number is reported with correct type."""
    result = run_validate(os.path.join(FIXTURES, "top_level_number.jsonl"))
    assert result.exit_code == 1
    assert "number" in result.output


# ---------------------------------------------------------------------------
# Criterion 5 — Required fields are present
# ---------------------------------------------------------------------------


def test_criterion5_missing_id():
    """Missing id field is reported by line number (no id to label by)."""
    result = run_validate(os.path.join(FIXTURES, "missing_id.jsonl"))
    assert result.exit_code == 1
    assert "missing required field(s)" in result.output
    assert "id" in result.output


def test_criterion5_missing_input():
    """Missing input field is reported."""
    result = run_validate(os.path.join(FIXTURES, "missing_input.jsonl"))
    assert result.exit_code == 1
    assert "missing required field(s)" in result.output
    assert "input" in result.output


def test_criterion5_missing_expected():
    """Missing expected field is reported."""
    result = run_validate(os.path.join(FIXTURES, "missing_expected.jsonl"))
    assert result.exit_code == 1
    assert "missing required field(s)" in result.output
    assert "expected" in result.output


# ---------------------------------------------------------------------------
# Criterion 6 — ID is a non-empty string and unique
# ---------------------------------------------------------------------------


def test_criterion6_empty_string_id():
    """Empty string id is reported as invalid."""
    result = run_validate(os.path.join(FIXTURES, "empty_string_id.jsonl"))
    assert result.exit_code == 1
    assert "empty string" in result.output


def test_criterion6_integer_id():
    """Integer id is reported as invalid with type 'number'."""
    result = run_validate(os.path.join(FIXTURES, "integer_id.jsonl"))
    assert result.exit_code == 1
    assert "number" in result.output


def test_criterion6_boolean_id():
    """Boolean id is reported as invalid with type 'boolean'."""
    result = run_validate(os.path.join(FIXTURES, "boolean_id.jsonl"))
    assert result.exit_code == 1
    assert "boolean" in result.output


def test_criterion6_duplicate_id_pair():
    """Duplicate id appearing twice is reported with both line numbers."""
    result = run_validate(os.path.join(FIXTURES, "duplicate_id_pair.jsonl"))
    assert result.exit_code == 1
    assert "Duplicate id" in result.output
    assert "1" in result.output
    assert "2" in result.output


def test_criterion6_duplicate_id_triple():
    """Duplicate id appearing three times is reported with all three line numbers."""
    result = run_validate(os.path.join(FIXTURES, "duplicate_id_triple.jsonl"))
    assert result.exit_code == 1
    assert "Duplicate id" in result.output
    # All three lines must be mentioned
    assert "1" in result.output
    assert "2" in result.output
    assert "3" in result.output


def test_criterion6_two_invalid_ids():
    """Two empty string ids are each reported individually (no duplicate detection)."""
    result = run_validate(os.path.join(FIXTURES, "two_invalid_ids.jsonl"))
    assert result.exit_code == 1
    # Two separate invalid-id errors, not a duplicate error
    error_lines = [ln for ln in result.output.splitlines() if "empty string" in ln]
    assert len(error_lines) == 2
    assert "Duplicate" not in result.output


# ---------------------------------------------------------------------------
# Criterion 7 — input and expected are JSON objects
# ---------------------------------------------------------------------------


def test_criterion7_expected_is_string():
    result = run_validate(os.path.join(FIXTURES, "expected_is_string.jsonl"))
    assert result.exit_code == 1
    assert '"expected" must be an object, got string' in result.output


def test_criterion7_expected_is_boolean():
    result = run_validate(os.path.join(FIXTURES, "expected_is_boolean.jsonl"))
    assert result.exit_code == 1
    assert '"expected" must be an object, got boolean' in result.output


def test_criterion7_expected_is_integer():
    result = run_validate(os.path.join(FIXTURES, "expected_is_integer.jsonl"))
    assert result.exit_code == 1
    assert '"expected" must be an object, got number' in result.output


def test_criterion7_expected_is_array():
    result = run_validate(os.path.join(FIXTURES, "expected_is_array.jsonl"))
    assert result.exit_code == 1
    assert '"expected" must be an object, got array' in result.output


def test_criterion7_expected_is_null():
    result = run_validate(os.path.join(FIXTURES, "expected_is_null.jsonl"))
    assert result.exit_code == 1
    assert '"expected" must be an object, got null' in result.output


def test_criterion7_input_is_string():
    result = run_validate(os.path.join(FIXTURES, "input_is_string.jsonl"))
    assert result.exit_code == 1
    assert '"input" must be an object, got string' in result.output


# ---------------------------------------------------------------------------
# Criterion 8 — Unrecognised fields generate warnings, not errors
# ---------------------------------------------------------------------------


def test_criterion8_unrecognised_field():
    """Unrecognised field generates a warning but no error; exits 0."""
    result = run_validate(os.path.join(FIXTURES, "unrecognised_field.jsonl"))
    assert result.exit_code == 0
    assert "unrecognised field" in result.output


def test_criterion8_warnings_only_exit_code():
    """File with only warnings exits with code 0."""
    result = run_validate(os.path.join(FIXTURES, "warnings_only.jsonl"))
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# Criterion 9 — All errors collected before reporting
# ---------------------------------------------------------------------------


def test_criterion9_multiple_errors():
    """All errors across multiple non-adjacent lines are reported in one run."""
    result = run_validate(os.path.join(FIXTURES, "multiple_errors.jsonl"))
    assert result.exit_code == 1
    # Must have at least 3 distinct errors
    error_lines = [ln for ln in result.output.splitlines() if ln.startswith("✗")]
    assert len(error_lines) >= 3


# ---------------------------------------------------------------------------
# Criterion 10 — Error limit
# ---------------------------------------------------------------------------


def test_criterion10_truncation():
    """After 50 errors, truncation notice is shown with additional error count."""
    result = run_validate(os.path.join(FIXTURES, "fifty_plus_errors.jsonl"))
    assert result.exit_code == 1
    assert "50 errors reported" in result.output
    assert "additional errors not shown" in result.output


# ---------------------------------------------------------------------------
# Valid file (criteria 3-8 all pass)
# ---------------------------------------------------------------------------


def test_valid_cases():
    """A fully valid JSONL file exits with code 0 and shows success message."""
    result = run_validate(os.path.join(FIXTURES, "valid_cases.jsonl"))
    assert result.exit_code == 0
    assert "✓" in result.output
    assert "No errors" in result.output


# ---------------------------------------------------------------------------
# Blank line policy
# ---------------------------------------------------------------------------


def test_blank_lines_between_cases():
    """Blank lines between valid cases are skipped silently."""
    result = run_validate(os.path.join(FIXTURES, "blank_lines_between_cases.jsonl"))
    assert result.exit_code == 0
    assert "3 cases validated" in result.output


# ---------------------------------------------------------------------------
# Mixed errors and warnings
# ---------------------------------------------------------------------------


def test_mixed_errors_and_warnings():
    """File with both warnings and errors: warnings appear before errors."""
    result = run_validate(os.path.join(FIXTURES, "mixed_errors_and_warnings.jsonl"))
    assert result.exit_code == 1
    lines = result.output.splitlines()
    first_warning_idx = next(
        (i for i, ln in enumerate(lines) if ln.startswith("⚠")), None
    )
    first_error_idx = next(
        (i for i, ln in enumerate(lines) if ln.startswith("✗")), None
    )
    assert first_warning_idx is not None
    assert first_error_idx is not None
    assert first_warning_idx < first_error_idx


# ---------------------------------------------------------------------------
# Success message format tests
# ---------------------------------------------------------------------------


def test_success_message_no_warnings():
    """Success message format: N cases validated. No errors."""
    result = run_validate(os.path.join(FIXTURES, "valid_cases.jsonl"))
    assert "✓ 3 cases validated. No errors." in result.output


def test_success_message_with_warnings():
    """Success message when warnings present shows warning count."""
    result = run_validate(os.path.join(FIXTURES, "warnings_only.jsonl"))
    assert "warning(s). See above." in result.output
    assert "✓" in result.output
    assert "No errors" in result.output
