# TrainKit

**A lightweight CLI tool for reproducible ML model evaluation.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/)

---

## Overview

TrainKit is a local-first, script-based CLI tool that runs ML model evaluation pipelines, records structured metrics, and compares results across runs. It is designed for ML engineers who need a lightweight, reproducible evaluation harness without adopting a full experiment-tracking platform.

**Problem:** Running model evaluations manually is error-prone and non-reproducible. Existing tools are heavy, require cloud infrastructure, or are too general-purpose.

**Solution:** TrainKit wraps a user-supplied evaluation script, captures its outputs, stores them with metadata in a structured artefact directory, and provides diff and threshold commands for result comparison.

---

## Philosophy

- **v0.x:** Local only. No cloud, no UI, no multi-user state. Deterministic by default.
- Scripts are the source of truth — TrainKit never modifies them.
- Metrics flow out; TrainKit does not inject state back into evaluation scripts.
- One output format (JSONL). One artefact layout. No configuration dialects.

---

## Target Users

ML engineers working on local model evaluation pipelines who want reproducible, structured result capture without a full MLOps platform.

> **Note:** Windows support is explicitly out of scope for v0.1. Windows compatibility will be reassessed at v0.2.

---

## Core Workflow

1. **Author** an evaluation script that writes metric rows to stdout as JSON lines.
2. **Run** `trainkit run` — TrainKit executes the script and captures output.
3. **Store** — results and metadata are written to the artefact directory.
4. **Inspect** — `trainkit show` displays the latest or a named run.
5. **Compare** — `trainkit diff` compares two runs and reports metric deltas.

---

## Installation

```bash
pip install trainkit
```

Requires Python 3.9 or later. Linux and macOS are supported for v0.1.

---

## Evaluation Data Format

Evaluation scripts must write one JSON object per line to stdout. Each line represents one evaluation sample.

### Required fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Unique identifier for the sample |
| `metric` | `string` | Metric name (e.g. `"accuracy"`, `"f1"`) |
| `value` | `number` | Numeric metric value |

### Optional fields

| Field | Type | Description |
|-------|------|-------------|
| `split` | `string` | Dataset split (e.g. `"test"`, `"val"`) |
| `label` | `string` | Ground-truth label |
| `prediction` | `string` | Model prediction |
| `metadata` | `object` | Arbitrary extra key/value pairs |

### Example output line

```json
{"id": "sample_001", "metric": "accuracy", "value": 0.923, "split": "test"}
```

---

## Model Execution Contract

TrainKit supports two execution modes:

### Mode 1 — Script mode (recommended)

The user provides a Python script path. TrainKit runs it as a subprocess:

```
trainkit run --script path/to/eval.py [--args "arg1 arg2"]
```

- The script must exit with code `0` on success.
- The script writes JSON lines to stdout; stderr is captured separately.
- `model_hash` is computed as the SHA-256 digest of the script file. **Limitation:** this identifies the script, not the model weights. Weight hashing is deferred to a future version.

### Mode 2 — Command mode

The user provides an arbitrary shell command:

```
trainkit run --cmd "python eval.py --config cfg.yaml"
```

- Same stdout/stderr contract as script mode.
- `model_hash` is `null` in command mode (no single file to hash).

---

## Metric System

### Built-in metrics

TrainKit recognises and validates the following metric names out of the box:

| Metric | Expected range | Notes |
|--------|---------------|-------|
| `accuracy` | [0.0, 1.0] | Boundary values 0.0 and 1.0 are valid |
| `f1` | [0.0, 1.0] | Macro, micro, or weighted — caller's choice |
| `precision` | [0.0, 1.0] | |
| `recall` | [0.0, 1.0] | |
| `loss` | ≥ 0.0 | No upper bound enforced |
| `bleu` | [0.0, 1.0] | |
| `rouge` | [0.0, 1.0] | |

**Boundary conditions:**
- Empty string for a required field → parse error; run fails with exit code `2`.
- Type mismatch for `value` (e.g. string instead of number) → parse error; run fails with exit code `2`.

### Custom metrics

Any metric name not in the built-in list is treated as a custom metric. Custom metrics are stored as-is, with no range validation.

**Custom metric failure modes:**

1. **Parse failure** — the output line is not valid JSON → the line is skipped; a warning is emitted to stderr; the run continues.
2. **Missing required field** — a required field (`id`, `metric`, or `value`) is absent → the line is skipped; a warning is emitted; the run continues.
3. **Fatal schema error** — if `--strict` is passed, any parse or missing-field error causes the run to fail immediately with exit code `2`.

---

## Result Format

Results are stored in two forms:

### Per-sample JSONL file (`results.jsonl`)

One JSON object per line, one line per sample. Each object is exactly one record emitted by the evaluation script and matches the evaluation data format described above (TrainKit does not inject additional fields into these records).


### Run summary file (`summary.json`)

One JSON object containing aggregate statistics and metadata for the run:

```json
{
  "run_id": "20260304T142300Z_abc12345",
  "timestamp": "2026-03-04T14:23:00Z",
  "script": "eval.py",
  "model_hash": "sha256:e3b0c44298fc...",
  "metrics": {
    "accuracy": {"mean": 0.923, "min": 0.88, "max": 0.96, "count": 50},
    "loss":     {"mean": 0.241, "min": 0.11, "max": 0.39, "count": 50}
  },
  "exit_code": 0,
  "duration_seconds": 12.4,
  "warnings": []
}
```

---

## Diff Semantics

`trainkit diff` compares two runs and reports metric deltas.

### Run selection

Runs are selected by **index** (integer, 0-based from oldest) or by **run ID prefix** (the compact timestamp prefix of the run directory name, for example `20260301T100000Z`).

```bash
# Compare run at index 0 (oldest) with run at index 1
trainkit diff 0 1

# Compare two runs by compact timestamp / run ID prefix
trainkit diff 20260301T100000Z 20260304T142300Z

# Compare second-to-last with last run
trainkit diff -2 -1
```

> **Rejected syntax:** Natural-language aliases such as `latest` or `previous` are not supported. Use negative indices (`-1` for last, `-2` for second-to-last).

### Diff output

```json
{
  "base_run": "20260301T100000Z_xyz99999",
  "compare_run": "20260304T142300Z_abc12345",
  "deltas": {
    "accuracy": {"base": 0.901, "compare": 0.923, "delta": +0.022},
    "loss":     {"base": 0.289, "compare": 0.241, "delta": -0.048}
  }
}
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All metrics within threshold (or no threshold set); run succeeded |
| `1` | One or more metrics breached the configured threshold, or a thresholded metric produced no values in this run |
| `2` | Fatal error (script error, parse failure in strict mode, missing required field) |

### Threshold option

```bash
trainkit run --script eval.py --threshold accuracy:0.90
```

If the mean `accuracy` across the run is below `0.90`, TrainKit exits with code `1`.

---

## Artefact Directory

By default, artefacts are stored under `.trainkit/runs/` in the current working directory.

```
.trainkit/
└── runs/
    └── 20260304T142300Z_abc12345/
        ├── results.jsonl
        ├── summary.json
        ├── stdout.log
        └── stderr.log
```

### Run directory naming

`<ISO8601_UTC_compact>_<sha256_prefix_8chars>`

Example: `20260304T142300Z_e3b0c442`

The suffix is derived from the script path or command string, so the same
target evaluated twice in the same second would otherwise produce the same
directory name. When that happens a numeric discriminator is appended
(`20260304T142300Z_e3b0c442-2`, `-3`, ...) so no run overwrites another. The
timestamp portion is unchanged, so selection by timestamp prefix still matches
every run started in that second.

### Metadata fields (`summary.json`)

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `string` | Full run directory name |
| `timestamp` | `string` | ISO 8601 UTC start time |
| `script` | `string` | Path to the evaluation script (or `null` in command mode) |
| `command` | `string` | Full shell command (or `null` in script mode) |
| `model_hash` | `string\|null` | SHA-256 of the script file in script mode; `null` in command mode |
| `exit_code` | `integer` | Script exit code |
| `duration_seconds` | `number` | Wall-clock duration of the script execution |
| `warnings` | `array` | List of warning messages emitted during the run |
| `trainkit_version` | `string` | TrainKit version that produced this run |
| `python_version` | `string` | Python interpreter version |
| `platform` | `string` | OS and architecture string |

> **model_hash limitation:** In script mode, `model_hash` is the SHA-256 of the evaluation script file, not the model weights. Two runs using the same script but different model checkpoints will have the same `model_hash`. Weight hashing is deferred to a future version.

---

## CLI Interface

```
trainkit <command> [options]
```

### Commands

| Command | Description |
|---------|-------------|
| `trainkit run` | Execute an evaluation script and store results |
| `trainkit show` | Display the summary for a run |
| `trainkit diff` | Compare two runs |
| `trainkit list` | List all stored runs |
| `trainkit clean` | Remove one or more stored runs |

### Examples

```bash
# Run an evaluation script
trainkit run --script eval.py

# Run with threshold enforcement
trainkit run --script eval.py --threshold accuracy:0.90 --threshold loss:0.30

# Run with strict mode (fail on any parse warning)
trainkit run --script eval.py --strict

# Show the latest run summary
trainkit show

# Show a specific run
trainkit show 20260304T142300Z_abc12345

# List all runs
trainkit list

# Compare last two runs
trainkit diff -2 -1

# Compare by index
trainkit diff 0 3

# Remove a run
trainkit clean 20260301T100000Z_xyz99999

# Remove all runs older than 7 days
trainkit clean --older-than 7d
```

---

## Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python 3.9+ | Ubiquitous in ML; matches user environment |
| CLI framework | `click` | Mature; composable; good error messages |
| Output format | JSONL | Streamable; grep-friendly; no schema lock-in |
| Packaging | `pyproject.toml` + `hatch` | Modern Python packaging standard |
| Testing | `pytest` | Standard Python test runner |
| Hashing | `hashlib` (stdlib) | No extra dependencies for SHA-256 |

---

## Development Roadmap

### v0.1 — Core loop
- `trainkit run` (script mode and command mode)
- JSONL capture and summary generation
- Artefact directory with metadata
- Exit codes 0/1/2
- `trainkit list` and `trainkit show`

### v0.2 — Diff and thresholds
- `trainkit diff` with index and timestamp selection
- `--threshold` option
- `trainkit clean`
- Windows support assessment

### v0.3 — Custom metrics and strict mode
- Custom metric pass-through
- `--strict` flag
- Built-in metric range validation
- Boundary condition error messages

### v1.0 — Stabilisation
- API stability guarantee
- Comprehensive documentation
- CI integration examples
- Performance benchmarks

---

## Competitive Landscape

| Tool | Scope | Why TrainKit is different |
|------|-------|--------------------------|
| MLflow | Full MLOps platform | Too heavy; requires a tracking server |
| Weights & Biases | Cloud-first experiment tracking | Cloud dependency; not local-first |
| DVC | Data/model versioning | Different problem; storage-focused |
| pytest-benchmark | Code benchmarking | Not ML-metric-aware |
| **TrainKit** | Local script evaluation | Zero infrastructure; script-native |

TrainKit occupies the niche of **zero-infrastructure, local-first, script-native evaluation capture** — no server, no account, no configuration dialect.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Feature creep | Public will-not-do list (below); new features require a filed issue with use-case justification |
| Script diversity | No assumptions about script internals; only stdout/stderr contract |
| Format lock-in | JSONL is grep-friendly and importable into any downstream tool |
| model_hash confusion | Limitation is documented explicitly in spec and in CLI help text |

### Will-not-do list (v0.x)

- No cloud sync or remote storage
- No web UI or dashboard
- No multi-user or team features
- No model registry
- No automatic hyperparameter logging
- No dataset versioning

---

## Success Metrics

> *All baselines marked (Inference) — not yet empirically measured.*

| Metric | Target | Baseline |
|--------|--------|----------|
| `trainkit run` latency overhead | < 500 ms vs raw script | (Inference) ~200 ms expected |
| Time to first evaluation run | < 5 minutes from `pip install` | (Inference) based on DeepEval onboarding data |
| Artefact directory size per run | < 1 MB for 10k samples | (Inference) ~50 bytes/sample in JSONL |

---

## Future Directions (post-v1.0)

> *The following are explicitly scoped to post-v1.0. They are not commitments.*

- Model weight hashing (replace script-hash with checkpoint-hash)
- Remote artefact storage backends (S3, GCS)
- Parallel evaluation across multiple scripts
- HTML report generation
- IDE plugin for inline metric display

---

## Contributing

TrainKit is in pre-release. Contributions are welcome after v0.1 is tagged.

If you want to propose a new feature, please file an issue with a concrete use-case description before submitting a PR. Feature requests without a filed issue will not be merged.

---

## Repository

**GitHub:** https://github.com/9TEVE-O/TrainKit

---

## Corrections Log (v0.2 → v0.3)

| Issue | Resolution |
|-------|-----------|
| `model_hash` undefined | Defined as SHA-256 of script file only; limitation documented |
| Metric boundary conditions | Empty string → parse error; type mismatch → parse error; both fail with exit code 2 |
| Custom metric error handling | Three failure modes specified (parse failure, missing field, fatal/strict) |
| Diff run selection ambiguous | Index or run ID prefix only; `latest`/`previous` rejected; negative indices supported |
| Success metrics unanchored | DeepEval baseline added; all labelled (Inference) |
| Feature creep mitigation weak | Public will-not-do list added; filed issue requirement stated |
| Windows support unaddressed | Explicitly out of scope for v0.1; reassess at v0.2 |
| Philosophy/future directions conflict | Philosophy scoped to v0.x; future directions explicitly post-v1.0 |

---

## License

MIT — see [LICENSE](LICENSE).

---

*Document Version: 0.3 (Verified) · Prepared by Subzteveø · March 2026*