"""Tests for trainkit.diff — diff_runs."""
from datetime import datetime, timezone

import pytest

from trainkit.artifacts import build_summary, make_run_id, write_run
from trainkit.diff import diff_runs


def _make_run(tmp_path, ts, seed, results):
    run_id = make_run_id(ts, seed)
    summary = build_summary(
        run_id=run_id, timestamp=ts, script=seed, command=None,
        model_hash=None, exit_code=0, duration_seconds=1.0,
        results=results, warnings=[],
    )
    write_run(
        run_id=run_id, results=results, summary=summary,
        stdout_text="", stderr_text="", base=tmp_path,
    )
    return run_id


class TestDiffRuns:
    def test_basic_delta(self, tmp_path):
        ts1 = datetime(2026, 3, 1, tzinfo=timezone.utc)
        ts2 = datetime(2026, 3, 4, tzinfo=timezone.utc)
        results1 = [{"id": "s1", "metric": "accuracy", "value": 0.9}]
        results2 = [{"id": "s1", "metric": "accuracy", "value": 0.95}]
        id1 = _make_run(tmp_path, ts1, "a.py", results1)
        id2 = _make_run(tmp_path, ts2, "b.py", results2)

        result = diff_runs("0", "1", tmp_path)
        assert result["base_run"] == id1
        assert result["compare_run"] == id2
        delta = result["deltas"]["accuracy"]["delta"]
        assert abs(delta - 0.05) < 1e-6

    def test_negative_delta(self, tmp_path):
        ts1 = datetime(2026, 3, 1, tzinfo=timezone.utc)
        ts2 = datetime(2026, 3, 4, tzinfo=timezone.utc)
        results1 = [{"id": "s1", "metric": "accuracy", "value": 0.95}]
        results2 = [{"id": "s1", "metric": "accuracy", "value": 0.90}]
        _make_run(tmp_path, ts1, "a.py", results1)
        _make_run(tmp_path, ts2, "b.py", results2)

        result = diff_runs("0", "1", tmp_path)
        assert result["deltas"]["accuracy"]["delta"] < 0

    def test_metric_only_in_base(self, tmp_path):
        ts1 = datetime(2026, 3, 1, tzinfo=timezone.utc)
        ts2 = datetime(2026, 3, 4, tzinfo=timezone.utc)
        results1 = [{"id": "s1", "metric": "accuracy", "value": 0.9}]
        results2 = [{"id": "s1", "metric": "f1", "value": 0.85}]
        _make_run(tmp_path, ts1, "a.py", results1)
        _make_run(tmp_path, ts2, "b.py", results2)

        result = diff_runs("0", "1", tmp_path)
        assert result["deltas"]["accuracy"]["compare"] is None
        assert result["deltas"]["accuracy"]["delta"] is None
        assert result["deltas"]["f1"]["base"] is None

    def test_invalid_selector(self, tmp_path):
        with pytest.raises(ValueError):
            diff_runs("0", "1", tmp_path)
