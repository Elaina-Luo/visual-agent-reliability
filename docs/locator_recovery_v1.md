# Locator-Based Recovery v1

## Hypothesis

When the repeat guard detects a deterministic action loop, a history-free
visual locator call can identify the next save or confirmation action more
reliably than adding more feedback to the Actor prompt.

## Controlled intervention

The strategy is the retained evidence-gated v2 baseline plus one bounded
intervention. After the first `repeat_blocked` proposal, it calls a locator
role that reuses the loaded Qwen model but receives only:

- the current screenshot;
- the original task;
- screenshot dimensions;
- blocked click regions.

The locator does not receive Actor action history or verifier history. It may
return one click for a visible enabled Save changes, Apply, or confirmation
action, or report `unavailable`. A locator click still passes through the same
executor, verifier, action budget, repeat guard memory, and hidden evaluator.
The Actor remains responsible for emitting the final `finish` action.

The locator is called at most once by default. Its raw output, latency, parse
or execution status, and selected action are recorded in the trace. Episode
results also record `locator_calls`, `locator_executed_actions`, cumulative
locator latency, and locator errors.

## Initial smoke test

```bash
python run_settings_locator_recovery_agent.py --seed 1 --max-steps 8 --fault-mode none
python run_settings_locator_recovery_agent.py --seed 0 --max-steps 8 --fault-mode drop_first_setting_change
```

Do not scale to a batch unless both episodes reach the target state and
terminate correctly.
