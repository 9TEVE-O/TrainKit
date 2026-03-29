/**
 * Policy: assertPrecommitBeforeSideEffects
 *
 * Enforces the invariant that a PRECOMMIT event must be emitted and appended
 * to the event log before any external side effect is applied
 * (Contract v1, Invariant 2).
 *
 * Usage pattern:
 *   const token = await emitPrecommit(store, ctx, "write results to disk");
 *   assertPrecommitBeforeSideEffects(token);
 *   // ... perform side effect ...
 */

/**
 * Opaque token returned by `emitPrecommit`.
 * Its presence (non-null) is the proof that a precommit was recorded.
 */
export interface PrecommitToken {
  /** The event ID of the PRECOMMIT event that was emitted. */
  eventId: string;
  /** ISO 8601 UTC timestamp when the precommit was emitted. */
  timestamp: string;
  /** Description of the side effect covered by this precommit. */
  description: string;
}

/**
 * Assert that a valid precommit token was obtained before a side effect.
 *
 * @param token - The token returned by `emitPrecommit`. Must be non-null.
 * @throws {Error} If `token` is null or undefined.
 */
export function assertPrecommitBeforeSideEffects(
  token: PrecommitToken | null | undefined
): void {
  if (token == null) {
    throw new Error(
      "Policy violation: a PRECOMMIT event must be emitted before applying any external side effect."
    );
  }
}
