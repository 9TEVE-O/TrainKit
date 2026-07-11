/**
 * Runtime Control Contract v1 -- core type definitions.
 *
 * All states, events, and context shapes used by the kernel are defined here.
 * Import from this module rather than duplicating the types elsewhere.
 */

// ---------------------------------------------------------------------------
// Run state
// ---------------------------------------------------------------------------

export type RunStatus = "IDLE" | "RUNNING" | "REST" | "ERROR";

// ---------------------------------------------------------------------------
// Event types
// ---------------------------------------------------------------------------

export type EventType =
  | "RUN_STARTED"
  | "PRECOMMIT"
  | "RUN_COMPLETED"
  | "RUN_FAILED"
  | "REST_EXITED"
  | "AUDIT_RECORDED";

// ---------------------------------------------------------------------------
// Event envelope
// ---------------------------------------------------------------------------

export interface EventEnvelope<T = unknown> {
  /** Unique event ID (UUID v4 or similar opaque string). */
  id: string;
  /** ISO 8601 UTC timestamp. */
  timestamp: string;
  /** One of the canonical EventType values. */
  type: EventType;
  /** Arbitrary event-specific payload. */
  payload: T;
}

// ---------------------------------------------------------------------------
// Specific event payloads
// ---------------------------------------------------------------------------

export interface RunStartedPayload {
  runId: string;
  script: string | null;
  command: string | null;
}

export interface PrecommitPayload {
  runId: string;
  /** Human-readable description of the side effect about to occur. */
  description: string;
}

export interface RunCompletedPayload {
  runId: string;
  exitCode: number;
  durationSeconds: number;
}

export interface RunFailedPayload {
  runId: string;
  reason: string;
}

export interface RestExitedPayload {
  runId: string;
  /** The state being transitioned to after leaving REST. */
  nextState: Exclude<RunStatus, "REST">;
  reason: string;
}

export interface AuditRecordedPayload {
  runId: string;
  recordType: string;
}

// ---------------------------------------------------------------------------
// Precommit record (a structured promise before a side effect)
// ---------------------------------------------------------------------------

export interface PrecommitRecord {
  runId: string;
  description: string;
  timestamp: string;
}

// ---------------------------------------------------------------------------
// Audit record
// ---------------------------------------------------------------------------

export interface AuditRecord {
  runId: string;
  recordType: string;
  data: unknown;
  timestamp: string;
}
