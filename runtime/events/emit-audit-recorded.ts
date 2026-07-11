/**
 * Emit an AUDIT_RECORDED event after writing an audit record.
 *
 * This provides a durable, ordered trail of every audit record the kernel
 * produces, enabling replay and verification.
 */

import type { JsonlEventStore } from "./jsonl-event-store.js";
import type { AuditRecord, AuditRecordedPayload, EventEnvelope } from "../runtime-types.js";
import { EventTypes } from "./event-types.js";

/**
 * Append an AUDIT_RECORDED event to the store after persisting an audit record.
 *
 * @param store - The event store to write to.
 * @param record - The audit record that was just persisted.
 * @returns The persisted event envelope.
 */
export function emitAuditRecorded(
  store: JsonlEventStore,
  record: AuditRecord
): EventEnvelope<AuditRecordedPayload> {
  const payload: AuditRecordedPayload = {
    runId: record.runId,
    recordType: record.recordType,
  };
  return store.append(EventTypes.AUDIT_RECORDED, payload);
}
