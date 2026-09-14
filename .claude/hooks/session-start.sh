#!/bin/bash
# SessionStart hook: install TrainKit's Python and Node dependencies so tests,
# typecheck, and the CLI work inside Claude Code on the web sessions.
#
# Mirrors the install steps in .github/workflows/tests.yml:
#   - Python: pip install -e ".[dev]"   (pytest + coverage + click)
#   - Node:   npm install                (vitest + typescript)
#
# Idempotent and non-interactive; safe to run on every session start.
set -euo pipefail

# Only run in the remote (Claude Code on the web) environment. Local sessions
# manage their own virtualenvs and node_modules.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"

echo "[session-start] Installing Python package with dev extras..."
# Best-effort pip upgrade: the web container ships a distro-managed pip that
# cannot be uninstalled, so a failure here must not abort the real install.
python -m pip install --upgrade pip || echo "[session-start] pip upgrade skipped"
python -m pip install -e ".[dev]"

echo "[session-start] Installing Node dependencies..."
# Prefer `npm install` over `npm ci` so a warm container cache is reused
# instead of wiping and rebuilding node_modules from scratch each session.
npm install

echo "[session-start] Dependencies installed."
