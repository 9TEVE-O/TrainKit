"""Tests for trainkit.cli — CLI commands."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from click.testing import CliRunner

from trainkit.cli import main


@pytest.fixture()
def runner():
    # Click >= 8.2 always keeps stderr separate and removed the constructor
    # argument; older releases need it passed explicitly. Tests read
    # result.stdout, which is the stdout-only stream on both.
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()


@pytest.fixture()
def eval_script(tmp_path):
    script = tmp_path / "eval.py"
    script.write_text(
        'import json\n'
        'rows = [\n'
        '    {"id": "s1", "metric": "accuracy", "value": 0.9},\n'
        '    {"id": "s2", "metric": "accuracy", "value": 0.85},\n'
        '    {"id": "s3", "metric": "loss", "value": 0.2},\n'
        ']\n'
        'for row in rows:\n'
        '    print(json.dumps(row))\n'
    )
    return script


@pytest.fixture()
def failing_script(tmp_path):
    script = tmp_path / "fail.py"
    script.write_text("import sys\nsys.exit(1)\n")
    return script


@pytest.fixture()
def bad_output_script(tmp_path):
    script = tmp_path / "bad.py"
    script.write_text('print("not json")\nprint("also not json")\n')
    return script


class TestRunCommand:
    def test_run_script_mode(self, runner, eval_script, tmp_path):
        result = runner.invoke(
            main,
            ["run", "--script", str(eval_script), "--output-dir", str(tmp_path)],
        )
        assert result.exit_code == 0, result.output
        summary = json.loads(result.stdout)
        assert summary["exit_code"] == 0
        assert "accuracy" in summary["metrics"]

    def test_run_requires_script_or_cmd(self, runner, tmp_path):
        result = runner.invoke(main, ["run", "--output-dir", str(tmp_path)])
        assert result.exit_code != 0

    def test_run_script_and_cmd_mutually_exclusive(self, runner, eval_script, tmp_path):
        result = runner.invoke(
            main,
            ["run", "--script", str(eval_script), "--cmd", "echo hi",
             "--output-dir", str(tmp_path)],
        )
        assert result.exit_code != 0

    def test_run_threshold_pass(self, runner, eval_script, tmp_path):
        result = runner.invoke(
            main,
            ["run", "--script", str(eval_script),
             "--threshold", "accuracy:0.80", "--output-dir", str(tmp_path)],
        )
        assert result.exit_code == 0

    def test_run_threshold_fail(self, runner, eval_script, tmp_path):
        result = runner.invoke(
            main,
            ["run", "--script", str(eval_script),
             "--threshold", "accuracy:0.99", "--output-dir", str(tmp_path)],
        )
        assert result.exit_code == 1

    def test_run_threshold_on_absent_metric_fails(self, runner, eval_script, tmp_path):
        # The script emits accuracy and loss but never precision. A gate on a
        # metric that never appeared must fail, not pass with a warning.
        result = runner.invoke(
            main,
            ["run", "--script", str(eval_script),
             "--threshold", "precision:0.5", "--output-dir", str(tmp_path)],
        )
        assert result.exit_code == 1
        assert "precision" in result.stderr

    def test_run_threshold_enforced_when_no_results(
        self, runner, bad_output_script, tmp_path
    ):
        # No parseable metric rows at all: the gate must still fail rather than
        # pass because nothing was measured.
        result = runner.invoke(
            main,
            ["run", "--script", str(bad_output_script),
             "--threshold", "accuracy:0.5", "--output-dir", str(tmp_path)],
        )
        assert result.exit_code == 1

    def test_repeated_runs_do_not_overwrite_artefacts(
        self, runner, eval_script, tmp_path, monkeypatch
    ):
        # Two runs of the same script in the same second previously collided on
        # the run ID and the second silently overwrote the first. Freeze the
        # clock so the collision is guaranteed rather than timing-dependent.
        frozen = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)

        class FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return frozen

        monkeypatch.setattr("trainkit.cli.datetime", FrozenDatetime)

        first = runner.invoke(
            main, ["run", "--script", str(eval_script), "--output-dir", str(tmp_path)]
        )
        second = runner.invoke(
            main, ["run", "--script", str(eval_script), "--output-dir", str(tmp_path)]
        )
        assert first.exit_code == 0, first.output
        assert second.exit_code == 0, second.output

        id_a = json.loads(first.stdout)["run_id"]
        id_b = json.loads(second.stdout)["run_id"]
        assert id_a != id_b
        assert (tmp_path / id_a / "summary.json").exists()
        assert (tmp_path / id_b / "summary.json").exists()

    def test_run_failing_script_exit_code_2(self, runner, failing_script, tmp_path):
        result = runner.invoke(
            main,
            ["run", "--script", str(failing_script), "--output-dir", str(tmp_path)],
        )
        assert result.exit_code == 2

    def test_failed_run_leaves_no_orphan_reservation(
        self, runner, tmp_path, monkeypatch
    ):
        # reserve_run_id claims the directory before the script runs, so a run
        # that aborts before writing must release it rather than leaving an
        # empty directory to consume the ID.
        frozen = datetime(2026, 3, 4, 14, 23, 0, tzinfo=timezone.utc)

        class FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return frozen

        monkeypatch.setattr("trainkit.cli.datetime", FrozenDatetime)

        result = runner.invoke(
            main,
            ["run", "--script", str(tmp_path / "nope.py"), "--output-dir", str(tmp_path)],
        )
        assert result.exit_code == 2
        assert [p.name for p in tmp_path.iterdir() if p.is_dir()] == []

    def test_run_args_with_quoted_spaces(self, runner, tmp_path):
        # args.split() would break a quoted argument containing a space into
        # multiple argv entries. shlex.split must keep it as one.
        script = tmp_path / "argv_echo.py"
        script.write_text(
            'import sys, json\n'
            'print(json.dumps({"id": "a", "metric": "accuracy", "value": 0.5, '
            '"split": repr(sys.argv[1:])}))\n'
        )
        result = runner.invoke(
            main,
            [
                "run", "--script", str(script),
                "--args", '--data "/data/my eval set.csv"',
                "--output-dir", str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.stdout
        run_dirs = [p for p in tmp_path.iterdir() if p.is_dir()]
        row = json.loads((run_dirs[0] / "results.jsonl").read_text().splitlines()[0])
        assert row["split"] == "['--data', '/data/my eval set.csv']"

    def test_run_args_unbalanced_quote_exits_2(self, runner, eval_script, tmp_path):
        # A malformed --args string must be a clean CLI error, not an
        # uncaught ValueError from shlex.split.
        result = runner.invoke(
            main,
            [
                "run", "--script", str(eval_script),
                "--args", '--data "unterminated',
                "--output-dir", str(tmp_path),
            ],
        )
        assert result.exit_code == 2
        assert "Could not parse --args" in result.stderr

    def test_run_non_utf8_output_does_not_crash(self, runner, tmp_path):
        # A script writing an invalid UTF-8 byte to stdout previously raised
        # an uncaught UnicodeDecodeError, surfacing as exit 1 -- the same
        # code as a threshold breach, making a tool crash indistinguishable
        # from a failed gate.
        script = tmp_path / "bad_encoding.py"
        payload = (
            b'{"id": "a", "metric": "accuracy", "value": 0.9, "note": "caf\xe9"}\n'
        )
        script.write_text(
            "import sys\n"
            f"sys.stdout.buffer.write({payload!r})\n"
        )
        result = runner.invoke(
            main,
            ["run", "--script", str(script), "--output-dir", str(tmp_path)],
        )
        assert result.exit_code == 0, result.stdout

    def test_run_timeout_kills_hung_script(self, runner, tmp_path):
        script = tmp_path / "hang.py"
        script.write_text(
            'import time\n'
            'print(\'{"id": "a", "metric": "accuracy", "value": 0.5}\')\n'
            'time.sleep(30)\n'
        )
        result = runner.invoke(
            main,
            [
                "run", "--script", str(script),
                "--timeout", "1",
                "--output-dir", str(tmp_path),
            ],
        )
        assert result.exit_code == 2
        assert "timed out" in result.stderr

    def test_run_bad_output_non_strict(self, runner, bad_output_script, tmp_path):
        result = runner.invoke(
            main,
            ["run", "--script", str(bad_output_script), "--output-dir", str(tmp_path)],
        )
        # Non-strict: warnings emitted, exit code 0, zero results
        assert result.exit_code == 0

    def test_run_bad_output_strict(self, runner, bad_output_script, tmp_path):
        result = runner.invoke(
            main,
            ["run", "--script", str(bad_output_script), "--strict",
             "--output-dir", str(tmp_path)],
        )
        assert result.exit_code == 2

    def test_run_nonexistent_script(self, runner, tmp_path):
        result = runner.invoke(
            main,
            ["run", "--script", str(tmp_path / "missing.py"),
             "--output-dir", str(tmp_path)],
        )
        assert result.exit_code == 2

    def test_run_stores_artefacts(self, runner, eval_script, tmp_path):
        out_dir = tmp_path / "artefacts"
        runner.invoke(
            main,
            ["run", "--script", str(eval_script), "--output-dir", str(out_dir)],
        )
        runs = list(out_dir.iterdir())
        assert len(runs) == 1
        run_dir = runs[0]
        assert (run_dir / "results.jsonl").exists()
        assert (run_dir / "summary.json").exists()

    def test_run_model_hash_present_script_mode(self, runner, eval_script, tmp_path):
        result = runner.invoke(
            main,
            ["run", "--script", str(eval_script), "--output-dir", str(tmp_path)],
        )
        summary = json.loads(result.stdout)
        assert summary["model_hash"] is not None
        assert summary["model_hash"].startswith("sha256:")

    def test_run_model_hash_null_command_mode(self, runner, tmp_path):
        result = runner.invoke(
            main,
            ["run", "--cmd",
             f'{sys.executable} -c "import json; print(json.dumps({{\'id\':\'s1\',\'metric\':\'accuracy\',\'value\':0.9}}))"',
             "--output-dir", str(tmp_path)],
        )
        assert result.exit_code == 0, result.output
        summary = json.loads(result.stdout)
        assert summary["model_hash"] is None


class TestListCommand:
    def test_list_empty(self, runner, tmp_path):
        result = runner.invoke(main, ["list", "--output-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "No runs found" in result.stdout

    def test_list_shows_runs(self, runner, eval_script, tmp_path):
        runner.invoke(
            main, ["run", "--script", str(eval_script), "--output-dir", str(tmp_path)]
        )
        result = runner.invoke(main, ["list", "--output-dir", str(tmp_path)])
        assert result.exit_code == 0
        assert "[0]" in result.stdout


class TestShowCommand:
    def test_show_latest(self, runner, eval_script, tmp_path):
        runner.invoke(
            main, ["run", "--script", str(eval_script), "--output-dir", str(tmp_path)]
        )
        result = runner.invoke(main, ["show", "--output-dir", str(tmp_path)])
        assert result.exit_code == 0
        summary = json.loads(result.stdout)
        assert "run_id" in summary

    def test_show_no_runs(self, runner, tmp_path):
        result = runner.invoke(main, ["show", "--output-dir", str(tmp_path)])
        assert result.exit_code == 2


class TestDiffCommand:
    def test_diff_two_runs(self, runner, eval_script, tmp_path):
        # Create two runs using two different scripts
        script2 = tmp_path / "eval2.py"
        script2.write_text(
            'import json\n'
            'print(json.dumps({"id": "s1", "metric": "accuracy", "value": 0.95}))\n'
        )
        runner.invoke(
            main, ["run", "--script", str(eval_script), "--output-dir", str(tmp_path)]
        )
        runner.invoke(
            main, ["run", "--script", str(script2), "--output-dir", str(tmp_path)]
        )
        result = runner.invoke(
            main, ["diff", "0", "1", "--output-dir", str(tmp_path)]
        )
        assert result.exit_code == 0
        diff = json.loads(result.stdout)
        assert "deltas" in diff

    def test_diff_invalid_selector(self, runner, tmp_path):
        result = runner.invoke(
            main, ["diff", "0", "1", "--output-dir", str(tmp_path)]
        )
        assert result.exit_code == 2


class TestCleanCommand:
    def test_clean_by_selector(self, runner, eval_script, tmp_path):
        runner.invoke(
            main, ["run", "--script", str(eval_script), "--output-dir", str(tmp_path)]
        )
        runner.invoke(main, ["clean", "0", "--output-dir", str(tmp_path)])
        result = runner.invoke(main, ["list", "--output-dir", str(tmp_path)])
        assert "No runs found" in result.stdout

    def test_clean_older_than(self, runner, eval_script, tmp_path):
        runner.invoke(
            main, ["run", "--script", str(eval_script), "--output-dir", str(tmp_path)]
        )
        # Clean with 0d should remove everything (runs are just created = within 0 days is borderline)
        # Use a very small duration that definitely includes the just-created run would need 0s.
        # Instead, assert clean --older-than 9999d removes nothing.
        result = runner.invoke(
            main, ["clean", "--older-than", "9999d", "--output-dir", str(tmp_path)]
        )
        assert result.exit_code == 0
        assert "No runs matched" in result.stdout

    def test_clean_bad_duration(self, runner, tmp_path):
        result = runner.invoke(
            main, ["clean", "--older-than", "bad", "--output-dir", str(tmp_path)]
        )
        assert result.exit_code != 0

    def test_clean_no_args(self, runner, tmp_path):
        result = runner.invoke(main, ["clean", "--output-dir", str(tmp_path)])
        assert result.exit_code != 0
