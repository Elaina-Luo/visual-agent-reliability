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

The action adapter also accepts Qwen's unambiguous native single-click form,
`{"type": "click", "x": [420, 210]}`, and normalizes it to the internal
`x`/`y` schema. Raw output remains in the trace. Outputs containing multiple
JSON actions are rejected rather than guessed.

The prompt explicitly requires separate integer `x` and `y` fields and rejects
coordinate arrays or multiple actions in one response. This output contract was
calibrated on the three development smoke tests before freezing B0.

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
budget is exhausted, or inference fails. The evaluator reports three fields:

- `task_state_success`: the requested value was saved, with no unapplied
  changes or open confirmation dialog;
- `agent_terminated_correctly`: the Agent explicitly returned `finish`; and
- `success`: both conditions are true.

This exposes cases where the Agent completes the GUI task but continues acting
until its step budget is exhausted.

## First smoke-test sequence

1. Run seed 0 without a fault.
2. Inspect every screenshot, raw output, parsed action, and final state.
3. Run seeds 1 and 2 without faults only after seed 0 is structurally valid.
4. Run one dropped-click episode only after the normal path is understood.

These runs are development examples, not reportable test-set results.
