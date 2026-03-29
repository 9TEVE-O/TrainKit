/**
 * Guard: canEnterRest (composed from explicit sub-checks)
 *
 * Implements the REST entry criteria from Runtime Control Contract v1:
 *
 *   canEnterRest(ctx) =
 *     isObjectiveSatisfied(ctx)
 *     AND NOT hasAuthorizedNextAction(ctx)
 *     AND NOT isMaterialAmbiguity(ctx)
 *
 * Each sub-check is imported as a named export so callers can inspect which
 * condition failed individually.
 */

import type { RuntimeContext } from "../runtime-context.js";
import { isObjectiveSatisfied } from "./is-objective-satisfied.js";
import { hasAuthorizedNextAction } from "./has-authorized-next-action.js";
import { isMaterialAmbiguity } from "./is-material-ambiguity.js";

export { isObjectiveSatisfied, hasAuthorizedNextAction, isMaterialAmbiguity };

export interface RestEntryDiagnosis {
  /** True if all criteria are met and REST entry is permitted. */
  allowed: boolean;
  /** True when the objective is satisfied. */
  objectiveSatisfied: boolean;
  /** True when there are no pending authorised next actions. */
  noPendingActions: boolean;
  /** True when there is no material ambiguity. */
  noMaterialAmbiguity: boolean;
}

/**
 * Evaluate all three REST entry criteria and return a structured diagnosis.
 *
 * Use `diagnosis.allowed` for the gate decision, and the individual boolean
 * fields to produce informative error messages when entry is denied.
 */
export function canEnterRest(ctx: RuntimeContext): RestEntryDiagnosis {
  const objectiveSatisfied = isObjectiveSatisfied(ctx);
  const noPendingActions = !hasAuthorizedNextAction(ctx);
  const noMaterialAmbiguity = !isMaterialAmbiguity(ctx);

  return {
    allowed: objectiveSatisfied && noPendingActions && noMaterialAmbiguity,
    objectiveSatisfied,
    noPendingActions,
    noMaterialAmbiguity,
  };
}
