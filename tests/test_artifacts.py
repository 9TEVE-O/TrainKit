"""Tests for trainkit.artifacts — run management functions."""
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from trainkit.artifacts import (
    discard_run_id,
    build_summary,
    reserve_run_id,
    list_runs,
    load_summary,
    make_run_id,
    resolve_run_id,
    write_run,
)


SAMPLE_RESULTS = [
    {"id": "s1", "metric": "accuracy", "value": 0.9},
    {"id": "s2", "metric": "accuracy", "value": 0.8},
    {"id": "s3", "metric": "loss", "value": 0.3},
]


class TestMakeRunId:
    def test_format(self):
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        run_id = make_run_id(ts, "eval.py")
        assert run_id.startswith("20260304T142300Z_")
        assert len(run_id) == 17 + 8  # "20260304T142300Z_" + 8 hex chars

    def test_deterministic(self):
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        assert make_run_id(ts, "eval.py") == make_run_id(ts, "eval.py")

    def test_different_seeds(self):
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        assert make_run_id(ts, "eval_a.py") != make_run_id(ts, "eval_b.py")


class TestReserveRunId:
    def test_returns_base_id_when_free(self, tmp_path):
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        assert reserve_run_id(ts, "eval.py", tmp_path) == make_run_id(ts, "eval.py")

    def test_reservation_is_atomic(self, tmp_path):
        # The whole point: reserving must claim the directory immediately, so a
        # second reservation taken before the first has written anything still
        # gets a distinct ID. A check-then-act allocator returns the same ID here.
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        first = reserve_run_id(ts, "eval.py", tmp_path)
        second = reserve_run_id(ts, "eval.py", tmp_path)
        assert first != second
        assert (tmp_path / first).is_dir()
        assert (tmp_path / second).is_dir()

    def test_disambiguates_same_second_same_seed(self, tmp_path):
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        first = reserve_run_id(ts, "eval.py", tmp_path)
        second = reserve_run_id(ts, "eval.py", tmp_path)
        assert second == f"{first}-002"
        assert reserve_run_id(ts, "eval.py", tmp_path) == f"{first}-003"

    def test_disambiguated_id_keeps_timestamp_prefix(self, tmp_path):
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        reserve_run_id(ts, "eval.py", tmp_path)
        second = reserve_run_id(ts, "eval.py", tmp_path)
        # Selection by timestamp prefix must still find both runs.
        assert second.startswith("20260304T142300Z_")


class TestRunOrdering:
    def _write(self, tmp_path, run_id, ts):
        summary = build_summary(
            run_id=run_id, timestamp=ts, script="eval.py", command=None,
            model_hash=None, exit_code=0, duration_seconds=1.0,
            results=SAMPLE_RESULTS, warnings=[],
        )
        write_run(
            run_id=run_id, results=SAMPLE_RESULTS, summary=summary,
            stdout_text="", stderr_text="", base=tmp_path,
        )

    def test_many_runs_in_one_second_stay_chronological(self, tmp_path):
        # End-to-end: twelve runs of one target inside a single second must
        # list in creation order and resolve correctly by index.
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        created = []
        for _ in range(12):
            run_id = reserve_run_id(ts, "eval.py", tmp_path)
            self._write(tmp_path, run_id, ts)
            created.append(run_id)

        assert list_runs(tmp_path) == created
        assert resolve_run_id("-1", tmp_path) == created[-1]
        assert resolve_run_id("0", tmp_path) == created[0]

    def test_ordering_survives_discriminator_width_change(self, tmp_path):
        # Zero-padding keeps IDs lexicographically sortable only while the
        # discriminator stays three digits. Past 999 the width grows and plain
        # string sorting puts "-1000" before "-999"; ordering must not depend
        # on that. Directories are created directly to reach the boundary
        # without a thousand reservations.
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        stem = make_run_id(ts, "eval.py")
        expected = [stem, f"{stem}-002", f"{stem}-999", f"{stem}-1000"]

        for run_id in reversed(expected):  # create out of order on purpose
            self._write(tmp_path, run_id, ts)

        assert list_runs(tmp_path) == expected
        assert resolve_run_id("-1", tmp_path) == f"{stem}-1000"

class TestDiscardRunId:
    def test_removes_empty_reservation(self, tmp_path):
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        run_id = reserve_run_id(ts, "eval.py", tmp_path)
        discard_run_id(run_id, tmp_path)
        assert not (tmp_path / run_id).exists()
        # The freed slot is reusable.
        assert reserve_run_id(ts, "eval.py", tmp_path) == run_id

    def test_never_removes_a_directory_holding_artefacts(self, tmp_path):
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        run_id = reserve_run_id(ts, "eval.py", tmp_path)
        (tmp_path / run_id / "summary.json").write_text("{}")
        discard_run_id(run_id, tmp_path)
        assert (tmp_path / run_id / "summary.json").exists()


class TestWriteAndLoadRun:
    def test_write_creates_files(self, tmp_path):
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        run_id = make_run_id(ts, "eval.py")
        summary = build_summary(
            run_id=run_id,
            timestamp=ts,
            script="eval.py",
            command=None,
            model_hash="sha256:abc123",
            exit_code=0,
            duration_seconds=1.5,
            results=SAMPLE_RESULTS,
            warnings=[],
        )
        directory = write_run(
            run_id=run_id,
            results=SAMPLE_RESULTS,
            summary=summary,
            stdout_text="some stdout",
            stderr_text="",
            base=tmp_path,
        )
        assert (directory / "results.jsonl").exists()
        assert (directory / "summary.json").exists()
        assert (directory / "stdout.log").exists()
        assert (directory / "stderr.log").exists()

    def test_write_refuses_to_overwrite_existing_run(self, tmp_path):
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        run_id = make_run_id(ts, "eval.py")
        summary = build_summary(
            run_id=run_id, timestamp=ts, script="eval.py", command=None,
            model_hash=None, exit_code=0, duration_seconds=1.0,
            results=SAMPLE_RESULTS, warnings=[],
        )
        kwargs = dict(
            run_id=run_id, summary=summary,
            stdout_text="", stderr_text="", base=tmp_path,
        )
        write_run(results=SAMPLE_RESULTS, **kwargs)

        # Reusing an ID must not silently clobber the first run's artefacts.
        with pytest.raises(FileExistsError):
            write_run(results=[], **kwargs)

        lines = (tmp_path / run_id / "results.jsonl").read_text().strip().splitlines()
        assert len(lines) == 3

    def test_results_jsonl_content(self, tmp_path):
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        run_id = make_run_id(ts, "eval.py")
        summary = build_summary(
            run_id=run_id, timestamp=ts, script="eval.py", command=None,
            model_hash=None, exit_code=0, duration_seconds=1.0,
            results=SAMPLE_RESULTS, warnings=[],
        )
        directory = write_run(
            run_id=run_id, results=SAMPLE_RESULTS, summary=summary,
            stdout_text="", stderr_text="", base=tmp_path,
        )
        lines = (directory / "results.jsonl").read_text().strip().splitlines()
        assert len(lines) == 3
        for line in lines:
            obj = json.loads(line)
            assert "id" in obj

    def test_load_summary(self, tmp_path):
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        run_id = make_run_id(ts, "eval.py")
        summary = build_summary(
            run_id=run_id, timestamp=ts, script="eval.py", command=None,
            model_hash="sha256:abc", exit_code=0, duration_seconds=2.0,
            results=SAMPLE_RESULTS, warnings=["w1"],
        )
        write_run(
            run_id=run_id, results=SAMPLE_RESULTS, summary=summary,
            stdout_text="", stderr_text="", base=tmp_path,
        )
        loaded = load_summary(run_id, tmp_path)
        assert loaded["run_id"] == run_id
        assert loaded["exit_code"] == 0
        assert loaded["warnings"] == ["w1"]

    def test_load_nonexistent(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_summary("does_not_exist", tmp_path)


class TestBuildSummary:
    def test_metrics_aggregation(self):
        ts = datetime(2026, 3, 4, tzinfo=timezone.utc)
        summary = build_summary(
            run_id="test_id", timestamp=ts, script="eval.py", command=None,
            model_hash=None, exit_code=0, duration_seconds=1.0,
            results=SAMPLE_RESULTS, warnings=[],
        )
        assert "accuracy" in summary["metrics"]
        assert "loss" in summary["metrics"]
        acc = summary["metrics"]["accuracy"]
        assert acc["count"] == 2
        assert abs(acc["mean"] - 0.85) < 1e-9
        assert acc["min"] == 0.8
        assert acc["max"] == 0.9

    def test_model_hash_none_command_mode(self):
        ts = datetime(2026, 3, 4, tzinfo=timezone.utc)
        summary = build_summary(
            run_id="test_id", timestamp=ts, script=None, command="python eval.py",
            model_hash=None, exit_code=0, duration_seconds=1.0,
            results=[], warnings=[],
        )
        assert summary["model_hash"] is None
        assert summary["command"] == "python eval.py"
        assert summary["script"] is None

    def test_required_metadata_fields(self):
        ts = datetime(2026, 3, 4, tzinfo=timezone.utc)
        summary = build_summary(
            run_id="r1", timestamp=ts, script="e.py", command=None,
            model_hash="sha256:x", exit_code=0, duration_seconds=0.5,
            results=[], warnings=[],
        )
        for field in ("trainkit_version", "python_version", "platform"):
            assert field in summary


class TestListAndResolveRuns:
    def _make_run(self, tmp_path, ts, seed="eval.py"):
        run_id = make_run_id(ts, seed)
        summary = build_summary(
            run_id=run_id, timestamp=ts, script="eval.py", command=None,
            model_hash=None, exit_code=0, duration_seconds=1.0,
            results=[], warnings=[],
        )
        write_run(
            run_id=run_id, results=[], summary=summary,
            stdout_text="", stderr_text="", base=tmp_path,
        )
        return run_id

    def test_list_empty(self, tmp_path):
        assert list_runs(tmp_path) == []

    def test_list_sorted(self, tmp_path):
        ts1 = datetime(2026, 3, 1, tzinfo=timezone.utc)
        ts2 = datetime(2026, 3, 4, tzinfo=timezone.utc)
        id2 = self._make_run(tmp_path, ts2, "b.py")
        id1 = self._make_run(tmp_path, ts1, "a.py")
        runs = list_runs(tmp_path)
        assert runs.index(id1) < runs.index(id2)

    def test_resolve_by_positive_index(self, tmp_path):
        ts1 = datetime(2026, 3, 1, tzinfo=timezone.utc)
        ts2 = datetime(2026, 3, 4, tzinfo=timezone.utc)
        id1 = self._make_run(tmp_path, ts1, "a.py")
        self._make_run(tmp_path, ts2, "b.py")
        assert resolve_run_id("0", tmp_path) == id1

    def test_resolve_by_negative_index(self, tmp_path):
        ts1 = datetime(2026, 3, 1, tzinfo=timezone.utc)
        ts2 = datetime(2026, 3, 4, tzinfo=timezone.utc)
        self._make_run(tmp_path, ts1, "a.py")
        id2 = self._make_run(tmp_path, ts2, "b.py")
        assert resolve_run_id("-1", tmp_path) == id2

    def test_resolve_by_timestamp_prefix(self, tmp_path):
        ts = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)
        run_id = self._make_run(tmp_path, ts)
        resolved = resolve_run_id("20260304T142300Z", tmp_path)
        assert resolved == run_id

    def test_resolve_no_runs(self, tmp_path):
        with pytest.raises(ValueError, match="No runs found"):
            resolve_run_id("0", tmp_path)

    def test_resolve_out_of_range(self, tmp_path):
        ts = datetime(2026, 3, 4, tzinfo=timezone.utc)
        self._make_run(tmp_path, ts)
        with pytest.raises((ValueError, IndexError)):
            resolve_run_id("99", tmp_path)
