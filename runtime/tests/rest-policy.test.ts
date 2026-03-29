import { describe, it, expect } from "vitest";
import { makeIdleContext } from "../runtime-context.js";
import type { RuntimeContext } from "../runtime-context.js";
import { assertNotRestForSideEffects } from "../policy/assert-not-rest-for-side-effects.js";

describe("assertNotRestForSideEffects", () => {
  it("does not throw when status is IDLE", () => {
    const ctx = makeIdleContext();
    expect(() => assertNotRestForSideEffects(ctx, "write file")).not.toThrow();
  });

  it("does not throw when status is RUNNING", () => {
    const ctx: RuntimeContext = { ...makeIdleContext(), status: "RUNNING" };
    expect(() =>
      assertNotRestForSideEffects(ctx, "write results")
    ).not.toThrow();
  });

  it("does not throw when status is ERROR", () => {
    const ctx: RuntimeContext = { ...makeIdleContext(), status: "ERROR" };
    expect(() =>
      assertNotRestForSideEffects(ctx, "error recovery")
    ).not.toThrow();
  });

  it("throws when status is REST", () => {
    const ctx: RuntimeContext = { ...makeIdleContext(), status: "REST" };
    expect(() =>
      assertNotRestForSideEffects(ctx, "upload artefacts")
    ).toThrow(/Policy violation/);
  });

  it("includes the side-effect description in the error message", () => {
    const ctx: RuntimeContext = { ...makeIdleContext(), status: "REST" };
    expect(() =>
      assertNotRestForSideEffects(ctx, "send telemetry")
    ).toThrow(/send telemetry/);
  });
});
