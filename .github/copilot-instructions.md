# Copilot Instructions — TrainKit

## Project overview

TrainKit is a local-first CLI tool for reproducible ML model evaluation.
It wraps user-supplied evaluation scripts, captures structured JSONL output,
stores results with metadata, and provides diff/threshold commands.

## Language and runtime

- Python 3.9+
- Linux and macOS only (Windows is out of scope for v0.x)

## Package layout

```
src/trainkit/       # all library and CLI code lives here
tests/              # pytest test suite
tests/fixtures/     # JSONL fixture files for validation tests
docs/               # PRD and task documents
```

Packages are discovered via `[tool.setuptools.packages.find] where = ["src"]`
in `pyproject.toml`.

## CLI framework

- Use **Click** (`click>=8.0`) for all CLI commands.
- The entry point is `trainkit.cli:cli` (a `click.Group`).
- Every subcommand is a function decorated with `@cli.command()`.

## Coding conventions

- Use type hints on all public function signatures.
- Prefer stdlib modules (`json`, `hashlib`, `pathlib`, `datetime`) over
  third-party libraries unless there is a clear need.
- Keep `click` as the only non-stdlib runtime dependency.
- Use `pathlib.Path` for filesystem operations.
- Strings: double quotes for user-facing messages, single or double for
  internal code (stay consistent within a file).

## Output format

- All structured data is JSONL (one JSON object per line).
- Use JSON type names in error messages (`number`, `boolean`, `array`,
  `null`, `object`, `string`), not Python type names.

## Exit codes

| Code | Meaning |
|------|---------|
| 0    | Success (warnings are OK) |
| 1    | Schema/threshold errors detected |
| 2    | Fatal error (file I/O, parse failure in strict mode) |

## Error handling

- Collect all errors before reporting; never halt on the first error.
- Hard cap of 50 errors per validation run — additional violations are
  counted in a truncation notice.
- Warnings (e.g. unrecognised fields) never cause a non-zero exit.

## Testing

- Use **pytest** (`pytest>=7.0`).
- Install dev dependencies: `pip install -e ".[dev]"`
- Run tests: `python -m pytest tests/`
- One test file per module (e.g. `test_validate.py` for `validate.py`).
- Use fixtures in `tests/fixtures/` for JSONL test data.

## Dependencies

- Runtime: `click>=8.0` (only non-stdlib dependency)
- Dev: `pytest>=7.0`, `pytest-cov`

## What NOT to do

- Do not add cloud, UI, or multi-user features (out of scope for v0.x).
- Do not add new runtime dependencies without explicit justification.
- Do not use `print()` for CLI output — use `click.echo()`.
- Do not use natural-language aliases (e.g. `latest`, `previous`) for
  run selection — use integer indices or full ISO 8601 timestamps.
