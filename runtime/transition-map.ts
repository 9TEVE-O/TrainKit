/**
 * Valid state transitions for the Runtime Control Contract v1 kernel.
 *
 * The map encodes every permitted (fromState, event) -> toState triple.
 * Any transition not in this map is illegal and must be rejected.
 */

import type { RunStatus, EventType } from "./runtime-types.js";

export type TransitionKey = `${RunStatus}:${EventType}`;

/**
 * Allowed transitions expressed as (state:event) -> nextState.
 *
 * Only `RUN_STARTED`, `RUN_COMPLETED`, `RUN_FAILED`, and `REST_EXITED`
 * cause state changes. `PRECOMMIT` and `AUDIT_RECORDED` are orthogonal
 * side-effect markers and do not change state.
 */
export const TRANSITION_MAP: Partial<Readonly<Record<TransitionKey, RunStatus>>> = {
  "IDLE:RUN_STARTED": "RUNNING",
  "RUNNING:RUN_COMPLETED": "REST",
  "RUNNING:RUN_FAILED": "ERROR",
  "REST:REST_EXITED": "IDLE",
  "ERROR:RUN_STARTED": "RUNNING",
} as const;

/**
 * Return the next state for a given (currentStatus, eventType) pair, or
 * `null` if the transition is not permitted.
 */
export function resolveTransition(
  current: RunStatus,
  event: EventType
): RunStatus | null {
  const key: TransitionKey = `${current}:${event}`;
  return TRANSITION_MAP[key] ?? null;
}
