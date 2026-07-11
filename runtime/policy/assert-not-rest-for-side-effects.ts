/**
 * Policy: assertNotRestForSideEffects
 *
 * Enforces the invariant that no external side effect may be initiated while
 * the runtime context is in the REST state (Contract v1, Invariant 1).
 */

import type { RuntimeContext } from "../runtime-context.js";

/**
 * Throw if the context is in REST state, preventing an illegal side effect.
 *
 * Call this immediately before any function that writes to disk, makes a
 * network request, or otherwise affects external state.
 *
 * @param ctx - Current runtime context.
 * @param sideEffectDescription - Human-readable label used in the error message.
 * @throws {Error} If `ctx.status === "REST"`.
 */
export function assertNotRestForSideEffects(
  ctx: RuntimeContext,
  sideEffectDescription: string
): void {
  if (ctx.status === "REST") {
    throw new Error(
      `Policy violation: side effect "${sideEffectDescription}" is not permitted while runtime is in REST state.`
    );
  }
}
