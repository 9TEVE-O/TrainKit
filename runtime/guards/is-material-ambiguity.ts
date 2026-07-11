/**
 * Guard: isMaterialAmbiguity
 *
 * Returns true when the runtime context contains unresolved material ambiguity
 * in the evaluation results. REST entry is blocked while this returns true.
 * This is the third of three explicit REST-entry criteria.
 *
 * "Material ambiguity" means there is enough missing or contradictory data
 * that the run's outcome cannot be reliably assessed (e.g. >50 % of output
 * rows failed to parse, or required metrics are absent).
 */

import type { RuntimeContext } from "../runtime-context.js";

/**
 * Check whether material ambiguity is present in the current context.
 */
export function isMaterialAmbiguity(ctx: RuntimeContext): boolean {
  return ctx.materialAmbiguity === true;
}
