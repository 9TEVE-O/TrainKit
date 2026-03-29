/**
 * Canonical event type constants.
 *
 * Using a const object (instead of a TypeScript enum) keeps the values
 * tree-shakeable and serialisable without a compilation step.
 */

export const EventTypes = {
  RUN_STARTED: "RUN_STARTED",
  PRECOMMIT: "PRECOMMIT",
  RUN_COMPLETED: "RUN_COMPLETED",
  RUN_FAILED: "RUN_FAILED",
  REST_EXITED: "REST_EXITED",
  AUDIT_RECORDED: "AUDIT_RECORDED",
} as const;

export type EventTypesValue = (typeof EventTypes)[keyof typeof EventTypes];
