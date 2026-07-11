import { describe, it, expect } from "vitest";
import { makeIdleContext } from "../runtime-context.js";
import type { RuntimeContext } from "../runtime-context.js";
import { isObjectiveSatisfied } from "../guards/is-objective-satisfied.js";
import { hasAuthorizedNextAction } from "../guards/has-authorized-next-action.js";
import { isMaterialAmbiguity } from "../guards/is-material-ambiguity.js";
import { canEnterRest } from "../guards/can-enter-rest.js";
import { resolveTransition } from "../transition-map.js";

describe("isObjectiveSatisfied", () => {
  it("returns false for a fresh IDLE context", () => {
    expect(isObjectiveSatisfied(makeIdleContext())).toBe(false);
  });

  it("returns false when objectiveSatisfied is false even with a runId", () => {
    const ctx: RuntimeContext = {
      ...makeIdleContext(),
      runId: "run-1",
      objectiveSatisfied: false,
    };
    expect(isObjectiveSatisfied(ctx)).toBe(false);
  });

  it("returns true when runId is set and objectiveSatisfied is true", () => {
    const ctx: RuntimeContext = {
      ...makeIdleContext(),
      runId: "run-1",
      objectiveSatisfied: true,
    };
    expect(isObjectiveSatisfied(ctx)).toBe(true);
  });

  it("returns false when runId is null even if objectiveSatisfied is true", () => {
    const ctx: RuntimeContext = {
      ...makeIdleContext(),
      runId: null,
      objectiveSatisfied: true,
    };
    expect(isObjectiveSatisfied(ctx)).toBe(false);
  });
});

describe("hasAuthorizedNextAction", () => {
  it("returns false when pendingActions is empty", () => {
    expect(hasAuthorizedNextAction(makeIdleContext())).toBe(false);
  });

  it("returns true when there is at least one pending action", () => {
    const ctx: RuntimeContext = {
      ...makeIdleContext(),
      pendingActions: ["retry"],
    };
    expect(hasAuthorizedNextAction(ctx)).toBe(true);
  });
});

describe("isMaterialAmbiguity", () => {
  it("returns false for a fresh IDLE context", () => {
    expect(isMaterialAmbiguity(makeIdleContext())).toBe(false);
  });

  it("returns true when materialAmbiguity flag is set", () => {
    const ctx: RuntimeContext = {
      ...makeIdleContext(),
      materialAmbiguity: true,
    };
    expect(isMaterialAmbiguity(ctx)).toBe(true);
  });
});

describe("canEnterRest", () => {
  function readyCtx(): RuntimeContext {
    return {
      status: "RUNNING",
      runId: "run-abc",
      objectiveSatisfied: true,
      pendingActions: [],
      materialAmbiguity: false,
      startedAt: "2026-01-01T00:00:00.000Z",
    };
  }

  it("allows REST when all criteria are met", () => {
    const diagnosis = canEnterRest(readyCtx());
    expect(diagnosis.allowed).toBe(true);
    expect(diagnosis.objectiveSatisfied).toBe(true);
    expect(diagnosis.noPendingActions).toBe(true);
    expect(diagnosis.noMaterialAmbiguity).toBe(true);
  });

  it("blocks REST when objective is not satisfied", () => {
    const ctx = { ...readyCtx(), objectiveSatisfied: false };
    const diagnosis = canEnterRest(ctx);
    expect(diagnosis.allowed).toBe(false);
    expect(diagnosis.objectiveSatisfied).toBe(false);
  });

  it("blocks REST when there are pending actions", () => {
    const ctx = { ...readyCtx(), pendingActions: ["upload"] };
    const diagnosis = canEnterRest(ctx);
    expect(diagnosis.allowed).toBe(false);
    expect(diagnosis.noPendingActions).toBe(false);
  });

  it("blocks REST when material ambiguity is present", () => {
    const ctx = { ...readyCtx(), materialAmbiguity: true };
    const diagnosis = canEnterRest(ctx);
    expect(diagnosis.allowed).toBe(false);
    expect(diagnosis.noMaterialAmbiguity).toBe(false);
  });

  it("blocks REST when multiple criteria fail simultaneously", () => {
    const ctx = {
      ...readyCtx(),
      objectiveSatisfied: false,
      materialAmbiguity: true,
    };
    const diagnosis = canEnterRest(ctx);
    expect(diagnosis.allowed).toBe(false);
    expect(diagnosis.objectiveSatisfied).toBe(false);
    expect(diagnosis.noMaterialAmbiguity).toBe(false);
  });
});

describe("resolveTransition", () => {
  it("IDLE + RUN_STARTED -> RUNNING", () => {
    expect(resolveTransition("IDLE", "RUN_STARTED")).toBe("RUNNING");
  });

  it("RUNNING + RUN_COMPLETED -> REST", () => {
    expect(resolveTransition("RUNNING", "RUN_COMPLETED")).toBe("REST");
  });

  it("RUNNING + RUN_FAILED -> ERROR", () => {
    expect(resolveTransition("RUNNING", "RUN_FAILED")).toBe("ERROR");
  });

  it("REST + REST_EXITED -> IDLE", () => {
    expect(resolveTransition("REST", "REST_EXITED")).toBe("IDLE");
  });

  it("ERROR + RUN_STARTED -> RUNNING", () => {
    expect(resolveTransition("ERROR", "RUN_STARTED")).toBe("RUNNING");
  });

  it("returns null for illegal transitions", () => {
    expect(resolveTransition("REST", "RUN_STARTED")).toBeNull();
    expect(resolveTransition("IDLE", "RUN_COMPLETED")).toBeNull();
    expect(resolveTransition("REST", "RUN_FAILED")).toBeNull();
  });

  it("PRECOMMIT and AUDIT_RECORDED do not change state", () => {
    expect(resolveTransition("RUNNING", "PRECOMMIT")).toBeNull();
    expect(resolveTransition("RUNNING", "AUDIT_RECORDED")).toBeNull();
  });
});
