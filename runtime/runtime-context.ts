/**
 * Runtime context -- the single mutable value that represents the kernel's
 * current state for one evaluation run.
 */

import type { RunStatus } from "./runtime-types.js";

// ---------------------------------------------------------------------------
// Context shape
// ---------------------------------------------------------------------------

export interface RuntimeContext {
  /** Current state machine state. */
  status: RunStatus;
  /** Unique ID for the current (or most recent) run. Null when IDLE. */
  runId: string | null;
  /**
   * True once the evaluation script has exited and results have been
   * captured successfully.
   */
  objectiveSatisfied: boolean;
  /**
   * A list of pending authorised next actions (e.g. retry, compare).
   * REST entry is blocked while this list is non-empty.
   */
  pendingActions: string[];
  /**
   * True when there is unresolved ambiguity in the results that prevents a
   * definitive conclusion (e.g. missing required fields in >50 % of rows).
   */
  materialAmbiguity: boolean;
  /**
   * Wall-clock timestamp (ISO 8601 UTC) when the current run started.
   * Null when IDLE.
   */
  startedAt: string | null;
}

// ---------------------------------------------------------------------------
// Factory
// ---------------------------------------------------------------------------

/**
 * Create a fresh IDLE context.
 */
export function makeIdleContext(): RuntimeContext {
  return {
    status: "IDLE",
    runId: null,
    objectiveSatisfied: false,
    pendingActions: [],
    materialAmbiguity: false,
    startedAt: null,
  };
}
