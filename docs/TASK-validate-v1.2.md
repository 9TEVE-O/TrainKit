# Task: `trainkit validate` — JSONL Evaluation Schema Validator

**Version:** 1.2
**Status:** Ready for implementation
**Phase:** 1
**Depends on:** CLI scaffolding (Click entrypoint)

---

## Objective

Implement `trainkit validate <file>`, a CLI command that reads a JSONL
evaluation-set file, checks every line against the TrainKit schema, collects all
errors before reporting, and exits with a CI-actionable exit code.

---

## Exit Codes

| Code | Meaning                                              |
|------|------------------------------------------------------|
| 0    | No errors found (warnings may be present)            |
| 1    | One or more schema errors found                      |
| 2    | Execution error: file not found, unreadable, or permission denied |

---

## Acceptance Criteria

### File-level checks

| #  | Criterion                                                       |
|----|-----------------------------------------------------------------|
| 1  | File not found or unreadable → exit code 2 with message `✗ Cannot read file: <path>` |
| 2  | Empty file (0 bytes) → exit code 1 with message `✗ File is empty` |
| 3  | Each line must be valid JSON; invalid lines are reported as errors |
| 4  | Each parsed JSON value must be a top-level object (not array, string, number, etc.) |

### Field-level checks

| #  | Criterion                                                       |
|----|-----------------------------------------------------------------|
| 5  | Required fields: `id`, `input`, `expected`                      |
| 6  | `id` must be a non-empty string; type mismatches report the JSON type name (`number`, `boolean`, etc.) |
| 7  | `id` must be unique across the file; duplicates report all occurrence line numbers |
| 8  | `input` and `expected` must be JSON objects                     |
| 9  | Unknown fields emit warnings (prefixed with `⚠`), never errors; a warnings-only file exits 0 |

### Error reporting

| #  | Criterion                                                       |
|----|-----------------------------------------------------------------|
| 10 | Hard cap of 50 errors — further violations are counted and reported in a truncation notice |
| 11 | Errors are prefixed with `✗`; warnings are prefixed with `⚠`   |
| 12 | Success message: `✓ <N> cases validated. No errors.`            |
| 13 | Error messages include line numbers; field errors include case ID when available |

---

## Error Message Format

```
✗ Line 4: invalid JSON
✗ Line 7 (case "case_007"): "expected" must be an object, got boolean
✗ Duplicate id "case_001" found at lines 3, 12, 47
⚠ Line 2 (case "case_002"): unrecognised field "source"
✓ 120 cases validated. No errors.
```

- When `id` is invalid or missing, error messages use line number only (no case label).
- When `id` is valid, error messages include `(case "<id>")`.
- JSON type names are used in messages: `number`, `boolean`, `array`, `null`,
  `object`, `string` — not Python type names.

---

## Architecture

### File layout

```
src/trainkit/cli.py        — Click group + validate subcommand
src/trainkit/validate.py   — Core validator (pure function)
tests/test_validate.py     — One test per acceptance criterion + fixture coverage
tests/fixtures/            — JSONL fixture files (one per failure mode)
```

### Design decisions

1. **Pure function validator** — `validate_jsonl_content(content: str, error_limit: int) -> ValidationResult`
   accepts content as a string. File I/O is the caller's responsibility. This
   eliminates TOCTOU race conditions and simplifies testing.

2. **Click path handling** — Use `click.Path(readable=False)` so Click does not
   intercept permission errors before our handler. Our code surfaces them with
   the expected `✗ Cannot read file:` prefix.

3. **Single file read** — One call to `path.read_text(encoding="utf-8")` with
   `FileNotFoundError` / `PermissionError` / `OSError` handlers.

4. **Duplicate tracking** — `_DuplicateTracker` collects all occurrences
   post-loop to avoid mutable shared-state bugs.

---

## Error Limit

After collecting 50 errors the validator stops processing further lines, appends
a truncation notice showing how many additional errors were not reported, and
exits with code 1.

*Product decision (March 2026):* 50 is the starting default. This value may be
changed before v1.0 without a schema amendment. If a different limit is needed,
update `MAX_ERRORS` in `src/trainkit/validate.py` and record the change in the
README.

---

## Performance Target

| File size     | Target  |
|---------------|---------|
| 10,000 lines  | < 2 s   |

Baseline measurement: ~78 ms on a Linux machine with a modern dual-core
processor (well within the 2-second target).

---

## Test Plan

One test per acceptance criterion, plus per-fixture coverage. Tests use the
Click test runner (`CliRunner`) for end-to-end validation.

| Test                                   | Validates criterion |
|----------------------------------------|---------------------|
| File not found → exit 2                | 1                   |
| Unreadable file → exit 2               | 1                   |
| Empty file → exit 1                    | 2                   |
| Invalid JSON line → error reported     | 3                   |
| Top-level array → error reported       | 4                   |
| Missing required fields → errors       | 5                   |
| Invalid ID types → error with type name| 6                   |
| Duplicate IDs → all lines reported     | 7                   |
| input/expected not objects → error     | 8                   |
| Unknown fields → warning only, exit 0  | 9                   |
| 50+ errors → truncation notice         | 10                  |

### Fixture files

One fixture file per failure mode in `tests/fixtures/`. Fixtures are minimal
(typically 1–5 lines) to isolate the specific failure condition.

---

## Dependencies

- `click>=8.0` (already a project dependency)
- No additional runtime dependencies required

---

## Out of Scope

- Validation of metric values or ranges (handled by `trainkit run`)
- Schema versioning or migration
- Streaming validation (entire file is read into memory)
- Custom schema extensions

---

*Task Version: 1.2 · March 2026*
