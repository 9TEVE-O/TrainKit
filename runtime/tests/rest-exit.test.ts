import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { makeIdleContext } from "../runtime-context.js";
import type { RuntimeContext } from "../runtime-context.js";
import { createJsonlEventStore } from "../events/jsonl-event-store.js";
import { emitRestExited } from "../events/emit-rest-exited.js";

let tmpDir: string;
let logPath: string;

beforeEach(() => {
  tmpDir = mkdtempSync(join(tmpdir(), "trainkit-rest-exit-test-"));
  logPath = join(tmpDir, "events.jsonl");
});

afterEach(() => {
  rmSync(tmpDir, { recursive: true, force: true });
});

describe("emitRestExited", () => {
  function restCtx(runId = "run-rest-1"): RuntimeContext {
    return {
      status: "REST",
      runId,
      objectiveSatisfied: true,
      pendingActions: [],
      materialAmbiguity: false,
      startedAt: "2026-01-01T00:00:00.000Z",
    };
  }

  it("appends a REST_EXITED event when context is in REST", () => {
    const store = createJsonlEventStore(logPath);
    emitRestExited(store, restCtx(), "IDLE", "resetting for next run");
    const events = store.readAll();
    expect(events).toHaveLength(1);
    expect(events[0]?.type).toBe("REST_EXITED");
  });

  it("records the correct nextState in the payload", () => {
    const store = createJsonlEventStore(logPath);
    emitRestExited(store, restCtx(), "RUNNING", "rerunning");
    const payload = store.readAll()[0]?.payload as {
      nextState: string;
      reason: string;
      runId: string;
    };
    expect(payload.nextState).toBe("RUNNING");
    expect(payload.reason).toBe("rerunning");
    expect(payload.runId).toBe("run-rest-1");
  });

  it("throws when context is not in REST state", () => {
    const store = createJsonlEventStore(logPath);
    const ctx: RuntimeContext = { ...restCtx(), status: "RUNNING" };
    expect(() =>
      emitRestExited(store, ctx, "IDLE", "should fail")
    ).toThrow(/emitRestExited called while context is in "RUNNING"/);
  });

  it("throws when context is IDLE", () => {
    const store = createJsonlEventStore(logPath);
    expect(() =>
      emitRestExited(store, makeIdleContext(), "IDLE", "should fail")
    ).toThrow(/emitRestExited called while context is in "IDLE"/);
  });

  it("events are append-only (two exits accumulate)", () => {
    const store = createJsonlEventStore(logPath);
    const ctx1 = restCtx("run-1");
    emitRestExited(store, ctx1, "IDLE", "first reset");
    const ctx2 = restCtx("run-2");
    emitRestExited(store, ctx2, "RUNNING", "second rerun");
    expect(store.readAll()).toHaveLength(2);
  });
});
