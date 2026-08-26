"""Tests for trainkit.metrics — parse_result_line and validate_metric_range."""
import pytest

from trainkit.metrics import (
    MissingFieldError,
    ParseError,
    parse_result_line,
    validate_metric_range,
)


class TestParseResultLine:
    def test_valid_minimal(self):
        row = parse_result_line('{"id": "s1", "metric": "accuracy", "value": 0.9}')
        assert row["id"] == "s1"
        assert row["metric"] == "accuracy"
        assert row["value"] == 0.9

    def test_valid_with_optional_fields(self):
        row = parse_result_line(
            '{"id": "s2", "metric": "f1", "value": 0.85, "split": "test", "label": "cat"}'
        )
        assert row["split"] == "test"
        assert row["label"] == "cat"

    def test_invalid_json(self):
        with pytest.raises(ParseError, match="Invalid JSON"):
            parse_result_line("not json {")

    def test_empty_line(self):
        with pytest.raises(ParseError, match="Empty line"):
            parse_result_line("")

    def test_json_array_rejected(self):
        with pytest.raises(ParseError, match="JSON object"):
            parse_result_line("[1, 2, 3]")

    @pytest.mark.parametrize(
        "literal, json_name",
        [
            ('"0.9"', "string"),
            ("true", "boolean"),
            ("null", "null"),
            ("{}", "object"),
            ("[]", "array"),
        ],
    )
    def test_value_type_error_names_the_json_type(self, literal, json_name):
        # Errors must name JSON types, not Python ones ('string' not 'str',
        # 'boolean' not 'bool', 'object' not 'dict').
        with pytest.raises(ParseError, match=f"got {json_name}$"):
            parse_result_line(
                '{"id": "s1", "metric": "accuracy", "value": %s}' % literal
            )

    @pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
    def test_non_finite_value_rejected(self, literal):
        # json.loads accepts these as floats; they must not reach results,
        # where they would defeat range checks and threshold comparisons.
        with pytest.raises(ParseError, match="finite number"):
            parse_result_line(
                '{"id": "s1", "metric": "accuracy", "value": %s}' % literal
            )

    def test_missing_id(self):
        with pytest.raises(MissingFieldError, match="'id'"):
            parse_result_line('{"metric": "accuracy", "value": 0.9}')

    def test_missing_metric(self):
        with pytest.raises(MissingFieldError, match="'metric'"):
            parse_result_line('{"id": "s1", "value": 0.9}')

    def test_missing_value(self):
        with pytest.raises(MissingFieldError, match="'value'"):
            parse_result_line('{"id": "s1", "metric": "accuracy"}')

    def test_empty_string_id(self):
        with pytest.raises(ParseError, match="'id'"):
            parse_result_line('{"id": "", "metric": "accuracy", "value": 0.9}')

    def test_empty_string_metric(self):
        with pytest.raises(ParseError, match="'metric'"):
            parse_result_line('{"id": "s1", "metric": "", "value": 0.9}')

    def test_type_mismatch_value_string(self):
        with pytest.raises(ParseError, match="'value' must be a number"):
            parse_result_line('{"id": "s1", "metric": "accuracy", "value": "high"}')

    def test_type_mismatch_value_bool(self):
        with pytest.raises(ParseError, match="'value' must be a number"):
            parse_result_line('{"id": "s1", "metric": "accuracy", "value": true}')

    def test_boundary_value_zero(self):
        row = parse_result_line('{"id": "s1", "metric": "accuracy", "value": 0.0}')
        assert row["value"] == 0.0

    def test_boundary_value_one(self):
        row = parse_result_line('{"id": "s1", "metric": "accuracy", "value": 1.0}')
        assert row["value"] == 1.0

    def test_integer_value_accepted(self):
        row = parse_result_line('{"id": "s1", "metric": "loss", "value": 1}')
        assert row["value"] == 1

    def test_whitespace_only_line(self):
        with pytest.raises(ParseError, match="Empty line"):
            parse_result_line("   ")


class TestValidateMetricRange:
    def test_accuracy_in_range(self):
        assert validate_metric_range("accuracy", 0.9) is None

    def test_accuracy_at_lower_bound(self):
        assert validate_metric_range("accuracy", 0.0) is None

    def test_accuracy_at_upper_bound(self):
        assert validate_metric_range("accuracy", 1.0) is None

    def test_accuracy_below_range(self):
        warning = validate_metric_range("accuracy", -0.1)
        assert warning is not None
        assert "below" in warning

    def test_accuracy_above_range(self):
        warning = validate_metric_range("accuracy", 1.1)
        assert warning is not None
        assert "above" in warning

    def test_loss_zero(self):
        assert validate_metric_range("loss", 0.0) is None

    def test_loss_large(self):
        assert validate_metric_range("loss", 999.0) is None

    def test_loss_negative(self):
        warning = validate_metric_range("loss", -0.5)
        assert warning is not None

    def test_custom_metric_no_warning(self):
        assert validate_metric_range("my_custom_metric", -9999) is None

    def test_all_builtin_metrics_in_range(self):
        for metric in ("accuracy", "f1", "precision", "recall", "bleu", "rouge"):
            assert validate_metric_range(metric, 0.5) is None

    def test_bleu_out_of_range(self):
        warning = validate_metric_range("bleu", 1.5)
        assert warning is not None
