/**
 * Emit a REST_EXITED event before any transition out of REST state.
 *
 * Per Contract v1 Invariant 4, this event must be appended to the log
 * before the state machine leaves REST.
 */

import type { JsonlEventStore } from "./jsonl-event-store.js";
import type { RuntimeContext } from "../runtime-context.js";
import type { RestExitedPayload, RunStatus, EventEnvelope } from "../runtime-types.js";
import { EventTypes } from "./event-types.js";

/**
 * Append a REST_EXITED event to the store.
 *
 * @param store - The event store to write to.
 * @param ctx - Current runtime context (must be in REST state).
 * @param nextState - The state being transitioned to.
 * @param reason - Human-readable reason for exiting REST.
 * @returns The persisted event envelope.
 * @throws {Error} If the context is not currently in REST state.
 */
export function emitRestExited(
  store: JsonlEventStore,
  ctx: RuntimeContext,
  nextState: Exclude<RunStatus, "REST">,
  reason: string
): EventEnvelope<RestExitedPayload> {
  if (ctx.status !== "REST") {
    throw new Error(
      `emitRestExited called while context is in "${ctx.status}" state; must be "REST".`
    );
  }
  const payload: RestExitedPayload = {
    runId: ctx.runId ?? "unknown",
    nextState,
    reason,
  };
  return store.append(EventTypes.REST_EXITED, payload);
}
