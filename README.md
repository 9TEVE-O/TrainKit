# TrainKit

TrainKit is a CLI tool for preparing and evaluating machine-learning evaluation sets.

## Installation

```bash
pip install -e ".[dev]"   # install with dev dependencies (pytest)
```

## Commands

### `trainkit validate <file>`

Validates a JSONL evaluation-set file against the TrainKit schema.

Every line is checked against the schema. All errors are collected before
reporting — the validator never halts on the first error.

**Exit codes**

| Code | Meaning |
|------|---------|
| 0 | No errors found. Warnings may be present. |
| 1 | One or more schema errors found. |
| 2 | Execution error: file not found, unreadable, or permission denied. |

**Schema rules**

Each non-blank line must be a JSON object with the following fields:

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `id` | Yes | Non-empty string | Must be unique across the file |
| `input` | Yes | JSON object | |
| `expected` | Yes | JSON object | |
| `description` | No | Any | Ignored |
| `tags` | No | Any | Ignored |
| `metadata` | No | Any | Contents not validated |

Fields outside this set generate warnings (exit code 0 is still returned if no errors are present).

**Error limit**

After collecting 50 errors the validator stops processing, appends a truncation
notice showing how many additional errors were not reported, and exits with
code 1.

*Product decision (March 2026):* 50 is the starting default. This value may be
changed before v1.0 without a schema amendment. If a different limit is needed,
update `MAX_ERRORS` in `src/trainkit/validate.py` and record the change here.

**Performance**

Measured on a Linux machine with a modern dual-core processor:

| File size | Time |
|-----------|------|
| 10,000 lines | ~78 ms |

Well within the 2-second directional target.

## Development

Run the test suite:

```bash
python -m pytest tests/
```