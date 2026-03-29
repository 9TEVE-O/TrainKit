"""Runtime bridge -- Python-side event emitter for the Runtime Control Contract v1.

This module lets the Python CLI emit events to the same append-only JSONL event
log consumed by the TypeScript runtime kernel.  It mirrors the envelope schema
defined in runtime/schemas/event-envelope.schema.json.

Default log path: .runtime/events/events.jsonl (relative to cwd).
Events are never deleted or modified; new lines are always appended.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_EVENT_LOG: Path = Path(".runtime") / "events" / "events.jsonl"

# Canonical event type literals (mirrors runtime/events/event-types.ts).
EVENT_RUN_STARTED = "RUN_STARTED"
EVENT_PRECOMMIT = "PRECOMMIT"
EVENT_RUN_COMPLETED = "RUN_COMPLETED"
EVENT_RUN_FAILED = "RUN_FAILED"
EVENT_REST_EXITED = "REST_EXITED"
EVENT_AUDIT_RECORDED = "AUDIT_RECORDED"


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")


def append_event(
    event_type: str,
    payload: dict[str, Any],
    log_path: Path = DEFAULT_EVENT_LOG,
) -> dict[str, Any]:
    """Append one event envelope to the JSONL log and return it.

    Parameters
    ----------
    event_type:
        One of the EVENT_* constants defined in this module.
    payload:
        Arbitrary event-specific data that will be serialised as the
        ``payload`` field of the envelope.
    log_path:
        Path to the JSONL file.  The parent directory is created
        automatically.

    Returns
    -------
    dict
        The event envelope that was written.
    """
    log_path.parent.mkdir(parents=True, exist_ok=True)
    envelope: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "timestamp": _utc_now(),
        "type": event_type,
        "payload": payload,
    }
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(envelope) + "\n")
    return envelope


def emit_run_started(
    run_id: str,
    *,
    script: str | None = None,
    command: str | None = None,
    log_path: Path = DEFAULT_EVENT_LOG,
) -> dict[str, Any]:
    """Emit a RUN_STARTED event."""
    return append_event(
        EVENT_RUN_STARTED,
        {"runId": run_id, "script": script, "command": command},
        log_path,
    )


def emit_precommit(
    run_id: str,
    description: str,
    log_path: Path = DEFAULT_EVENT_LOG,
) -> dict[str, Any]:
    """Emit a PRECOMMIT event before an external side effect.

    Call this before writing artefacts, uploading results, or any other
    external mutation.
    """
    return append_event(
        EVENT_PRECOMMIT,
        {"runId": run_id, "description": description},
        log_path,
    )


def emit_run_completed(
    run_id: str,
    exit_code: int,
    duration_seconds: float,
    log_path: Path = DEFAULT_EVENT_LOG,
) -> dict[str, Any]:
    """Emit a RUN_COMPLETED event after results are captured."""
    return append_event(
        EVENT_RUN_COMPLETED,
        {
            "runId": run_id,
            "exitCode": exit_code,
            "durationSeconds": round(duration_seconds, 3),
        },
        log_path,
    )


def emit_run_failed(
    run_id: str,
    reason: str,
    log_path: Path = DEFAULT_EVENT_LOG,
) -> dict[str, Any]:
    """Emit a RUN_FAILED event on an error exit."""
    return append_event(
        EVENT_RUN_FAILED,
        {"runId": run_id, "reason": reason},
        log_path,
    )
