# Copilot Instructions - TrainKit

## Project overview
I am Subzteveø, an independent developer building TrainKit,
a local-first CLI tool for ML model regression testing, and
Teach the Robot, an AI education game for primary school children.

## Identity and context
Background: software engineering, AI/ML, audio engineering,
education. I think in systems. I verify claims before accepting
them. I expect the same from you.

## General behaviour
- Be direct. No filler, no hype, no corporate language.
- Separate facts from inferences. Label speculation clearly.
- If something is missing or unclear, say so. Do not invent.
- Show reasoning behind numbers and estimates.
- Active voice. Vary sentence length. No em dashes in prose.
- Never use "in conclusion", "certainly", "great question".

## Code behaviour: all projects
- Python 3.9+ unless told otherwise.
- Type hints on all public functions.
- Docstrings on all public classes and non-trivial functions.
- Use pathlib.Path for filesystem operations.
- Use click.echo() for CLI output, never print().
- JSON type names in error messages: string, number, boolean,
  array, null, object. Never Python type names.
- One file read per operation in CLI layer only.
  Never read files inside library or validator logic.
- Collect all errors before reporting. Never halt on first error.
- shlex.split() for argument parsing. Never args.split().

## TrainKit specific
- Layout: src/trainkit/ always. Never flat trainkit/.
- Build system: setuptools only. Never hatchling.
- CLI entrypoint: trainkit.cli:cli. Never main().
- Exit codes are command-specific. See governing documents.
  0 = no errors, 1 = errors detected, 2 = execution failure.
- Run selectors: integer index or compact timestamp prefix.
  e.g. 20260301T100000Z. Full ISO 8601 not supported.
- mkdir uses exist_ok=False. Exit code 2 on collision.
- TrainKit does not inject fields into model output.
- macOS and Linux only for v0.x. Windows out of scope.
- Scope: local only. No cloud, dashboard, or team features.
- Read .github/copilot-instructions.md, docs/PRD-v0.3.md,
  and docs/TASK-validate-v1.2.md before generating anything.

## Teach the Robot specific
- Browser-based React game. No backend required.
- Target: primary school children ages 5 to 11.
- Robot character is named Pip.
- ML simulation uses weighted JavaScript logic, not real models.
- No user accounts. No data transmission. No external links.
- Error states must be friendly, not punishing.
- Minimal text. Icons where possible.

## Testing
- Write fixture files before writing tests.
- One fixture per failure mode.
- Every test must assert exit code and output content.
- Tests using chmod must skip when os.getuid() == 0.
- Use pytest and Click CliRunner for CLI tests.

## Verification
- Run verification gate before showing any output.
- Show each check as PASS or FAIL explicitly.
- If any check fails, fix it and rerun the full gate.
- Do not commit or push without explicit approval.
- Approval phrase: "Approved -- commit only."
- Push via pull request only. Never direct push.

## Hugging Face
- Use transformers library. Pin model versions by commit hash.
- Prefer pipeline() unless performance requires direct calls.
- Set device explicitly: cpu, cuda, or mps.
- Never load models inside a loop.
- For TrainKit: HF model calls go in runner.py as Mode 1
  Python callable. predict() returns a plain dict.
  No HF types leak into TrainKit result layer.
- No HF PRD exists yet. These are provisional principles.
