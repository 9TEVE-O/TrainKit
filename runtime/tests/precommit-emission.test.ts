import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { makeIdleContext } from "../runtime-context.js";
import type { RuntimeContext } from "../runtime-context.js";
import { createJsonlEventStore } from "../events/jsonl-event-store.js";
import { emitPrecommit } from "../events/emit-precommit.js";
import { assertPrecommitBeforeSideEffects } from "../policy/assert-precommit-before-side-effects.js";

let tmpDir: string;
let logPath: string;

beforeEach(() => {
  tmpDir = mkdtempSync(join(tmpdir(), "trainkit-precommit-test-"));
  logPath = join(tmpDir, "events.jsonl");
});

afterEach(() => {
  rmSync(tmpDir, { recursive: true, force: true });
});

describe("emitPrecommit", () => {
  it("appends a PRECOMMIT event to the log", () => {
    const store = createJsonlEventStore(logPath);
    const ctx: RuntimeContext = {
      ...makeIdleContext(),
      status: "RUNNING",
      runId: "run-xyz",
    };
    emitPrecommit(store, ctx, "write results to disk");
    const events = store.readAll();
    expect(events).toHaveLength(1);
    expect(events[0]?.type).toBe("PRECOMMIT");
  });

  it("returns a token with the correct description", () => {
    const store = createJsonlEventStore(logPath);
    const ctx: RuntimeContext = {
      ...makeIdleContext(),
      status: "RUNNING",
      runId: "run-xyz",
    };
    const token = emitPrecommit(store, ctx, "write summary.json");
    expect(token.description).toBe("write summary.json");
    expect(token.eventId).toBeTruthy();
    expect(token.timestamp).toBeTruthy();
  });

  it("records the runId in the payload", () => {
    const store = createJsonlEventStore(logPath);
    const ctx: RuntimeContext = {
      ...makeIdleContext(),
      status: "RUNNING",
      runId: "run-42",
    };
    emitPrecommit(store, ctx, "upload");
    const events = store.readAll();
    const payload = events[0]?.payload as { runId: string };
    expect(payload.runId).toBe("run-42");
  });
});

describe("assertPrecommitBeforeSideEffects", () => {
  it("does not throw when a valid token is provided", () => {
    const store = createJsonlEventStore(logPath);
    const ctx: RuntimeContext = {
      ...makeIdleContext(),
      status: "RUNNING",
      runId: "run-1",
    };
    const token = emitPrecommit(store, ctx, "write file");
    expect(() => assertPrecommitBeforeSideEffects(token)).not.toThrow();
  });

  it("throws when token is null", () => {
    expect(() => assertPrecommitBeforeSideEffects(null)).toThrow(
      /Policy violation/
    );
  });

  it("throws when token is undefined", () => {
    expect(() => assertPrecommitBeforeSideEffects(undefined)).toThrow(
      /Policy violation/
    );
  });
});
