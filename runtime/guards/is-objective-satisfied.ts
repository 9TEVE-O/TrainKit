/**
 * Guard: isObjectiveSatisfied
 *
 * Returns true when the runtime context indicates that the primary evaluation
 * objective has been met. This is the first of three explicit REST-entry
 * criteria (see Runtime Control Contract v1, section "REST entry criteria").
 */

import type { RuntimeContext } from "../runtime-context.js";

/**
 * Check whether the objective for the current run is satisfied.
 *
 * A run's objective is considered satisfied when:
 * - The context has a non-null runId (a run was started), AND
 * - `objectiveSatisfied` was explicitly set to `true` (typically after
 *   successful result capture and threshold evaluation).
 */
export function isObjectiveSatisfied(ctx: RuntimeContext): boolean {
  return ctx.runId !== null && ctx.objectiveSatisfied === true;
}
