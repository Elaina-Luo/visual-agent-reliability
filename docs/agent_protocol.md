# Part B agent protocol

## B0 — Reactive baseline

B0 uses `Qwen/Qwen2.5-VL-3B-Instruct` as a screenshot-to-action policy. At each
step, the model receives:

- the natural-language task goal;
- the current 980 × 644 screenshot;
- up to four actions it previously requested; and
- the remaining action budget.

It returns exactly one action:

```json
{"type": "click", "x": 420, "y": 210}
```

or:

```json
{"type": "finish"}
```

B0 receives a new screenshot after every click but has no explicit
`achieved / failed / uncertain` verification stage and no forced retry rule.
This allows natural reactive recovery without building an artificially weak
baseline.

## Execution and hidden state

Playwright executes valid coordinate clicks. Invalid model outputs consume one
step but do not change the page. Under `drop_first_setting_change`, the executor
drops the first click on a switch or segmented setting control.

The Agent never receives execution status, the fault flag, DOM information,
test identifiers, draft/saved settings, or the evaluator's success judgment.
Those fields are stored only in the trace for later auditing.

## Termination and scoring

The action budget is eight. An episode ends when the Agent calls `finish`, the
budget is exhausted, or inference fails. Success requires an explicit finish,
the requested value in saved settings, no unapplied changes, and no open
confirmation dialog.

## First smoke-test sequence

1. Run seed 0 without a fault.
2. Inspect every screenshot, raw output, parsed action, and final state.
3. Run seeds 1 and 2 without faults only after seed 0 is structurally valid.
4. Run one dropped-click episode only after the normal path is understood.

These runs are development examples, not reportable test-set results.
