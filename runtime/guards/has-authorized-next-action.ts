/**
 * Guard: hasAuthorizedNextAction
 *
 * Returns true when the runtime context has at least one pending authorised
 * next action queued. REST entry is blocked while this returns true.
 * This is the second of three explicit REST-entry criteria.
 */

import type { RuntimeContext } from "../runtime-context.js";

/**
 * Check whether any authorised next actions are still pending.
 *
 * Examples of pending actions: "retry", "compare-baseline", "upload-artefacts".
 * The list must be empty before the kernel can enter REST.
 */
export function hasAuthorizedNextAction(ctx: RuntimeContext): boolean {
  return ctx.pendingActions.length > 0;
}
