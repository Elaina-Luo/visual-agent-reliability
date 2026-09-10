# Settings App task specification

## Purpose

The Settings App is the primary interactive environment for Part B. It is a
realistic but controlled GUI for studying whether a visual agent can detect and
recover from action failures.

## Task families

| Family | Example goal | Required interaction |
| --- | --- | --- |
| Appearance | Select Compact density and save | Navigate, choose option, save, confirm |
| Notifications | Turn off Sound alerts and save | Navigate, toggle, save, confirm |
| Privacy | Turn off Analytics sharing and save | Navigate, toggle, save, confirm |

The initial target value is always different from the requested value, so an
episode cannot succeed without changing the setting.

## Agent-visible information

- Natural-language goal.
- Current 980 × 644 screenshot. Both dimensions are divisible by Qwen's
  28-pixel visual-processing factor, avoiding an extra coordinate resize.
- Previous action and a bounded recent history.
- Remaining action budget.

## Action space

- `{"type": "click", "x": integer, "y": integer}`
- `{"type": "finish"}`

The first agent experiment will use an eight-action budget. Invalid actions
count against the budget.

## Success condition

An episode succeeds only when all of the following hold:

1. The agent calls `finish` within the action budget.
2. The saved value for the target setting equals the requested value.
3. There are no unapplied changes.
4. The confirmation dialog is closed.

## Evaluator-only information

- Initial, draft, and saved settings state.
- Target setting key and target value.
- Fault mode and whether a fault was triggered.
- Exact success judgment and failure category.

Evaluator-only information may be written to experiment logs but must never be
included in the model prompt.

## Current validation boundary

`run_settings_scripted.py` uses DOM test identifiers only to construct known
correct coordinate-click traces and validate the environment. The future Agent
will not receive DOM access or test identifiers; it will act from screenshots.

The first Settings App fault mode drops the first click that would change a
setting. Navigation, Save, and confirmation clicks are unaffected. Hidden audit
state verifies that the dropped action leaves the page unchanged. The scripted
check compares no retry against one repeated setting click; it validates the
fault mechanism, not autonomous Agent recovery.

Delayed-feedback injection remains a later extension.
