# Runtime Control Contract v1

## States

| State | Description |
|-------|-------------|
| `IDLE` | No active run; ready to accept work |
| `RUNNING` | Evaluation script executing; side effects may occur |
| `REST` | Run complete; results available; no side effects permitted |
| `ERROR` | Terminal failure; no further transitions |

## Invariants

1. **REST is terminal for side effects.** No external write or network call may be initiated while the context is in `REST` state.
2. **Precommit precedes every side effect.** A `PRECOMMIT` event must be emitted and appended to the event log before any external side effect is applied.
3. **REST entry is explicit.** A context may only transition to `REST` when all three conditions hold simultaneously:
   - `isObjectiveSatisfied` returns `true`
   - `hasAuthorizedNextAction` returns `false`
   - `isMaterialAmbiguity` returns `false`
4. **REST exit is auditable.** Any transition out of `REST` must emit a `REST_EXITED` event before taking effect.
5. **Events are append-only.** The JSONL event log is never modified; only new lines are appended.

## Transition table

```
IDLE    -> RUNNING   (startRun)
IDLE    -> ERROR     (internalError)
RUNNING -> REST      (completeRun, only when canEnterRest)
RUNNING -> ERROR     (runFailed)
REST    -> IDLE      (reset, emits REST_EXITED)
REST    -> RUNNING   (rerun, emits REST_EXITED)
ERROR   -> IDLE      (reset)
```

## Event types

| Type | When emitted |
|------|-------------|
| `RUN_STARTED` | Immediately after `IDLE -> RUNNING` |
| `PRECOMMIT` | Before any external side effect |
| `RUN_COMPLETED` | After results are captured, before `REST` |
| `RUN_FAILED` | On `RUNNING -> ERROR` |
| `REST_EXITED` | Before any `REST -> *` transition |
| `AUDIT_RECORDED` | After each audit record is written |

## REST entry criteria (composable checks)

```
canEnterRest(ctx) =
  isObjectiveSatisfied(ctx)
  AND NOT hasAuthorizedNextAction(ctx)
  AND NOT isMaterialAmbiguity(ctx)
```

Each check is a standalone exported function with a descriptive boolean return, enabling independent testing and explicit error messaging when REST entry is denied.
