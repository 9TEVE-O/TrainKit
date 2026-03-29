/**
 * Emit a PRECOMMIT event before an external side effect.
 *
 * Returns a PrecommitToken that must be passed to
 * `assertPrecommitBeforeSideEffects` immediately before the side effect runs.
 */

import type { JsonlEventStore } from "./jsonl-event-store.js";
import type { RuntimeContext } from "../runtime-context.js";
import type { PrecommitPayload } from "../runtime-types.js";
import type { PrecommitToken } from "../policy/assert-precommit-before-side-effects.js";
import { EventTypes } from "./event-types.js";

/**
 * Append a PRECOMMIT event to the store and return a token that proves it.
 *
 * @param store - The event store to write to.
 * @param ctx - Current runtime context (must have a non-null runId).
 * @param description - Human-readable label for the upcoming side effect.
 * @returns A PrecommitToken to pass to `assertPrecommitBeforeSideEffects`.
 */
export function emitPrecommit(
  store: JsonlEventStore,
  ctx: RuntimeContext,
  description: string
): PrecommitToken {
  const runId = ctx.runId ?? "unknown";
  const payload: PrecommitPayload = { runId, description };
  const envelope = store.append(EventTypes.PRECOMMIT, payload);
  return {
    eventId: envelope.id,
    timestamp: envelope.timestamp,
    description,
  };
}
