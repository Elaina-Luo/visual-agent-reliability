# Evidence-Gated Recovery v2.4

v2.4 keeps the v2.3 parser repair and adds a constrained recovery subgoal for
deterministic repeat loops. The v2.3 smoke trace showed that the Actor
successfully changed the target setting, then proposed the same toggle three
more times despite ordinary feedback and a forbidden region.

After the first `repeat_blocked` result, only the next Actor turn receives a
temporary recovery goal. It states that the blocked click was not executed,
forbids clicking that setting again, and prioritizes an enabled visible Save
changes action when the requested setting already matches. The original task
is retained in the recovery goal. After any different result, the Actor again
receives the original task.

This intervention does not execute an action, identify a coordinate, inspect
hidden environment state, add retries, or consume the action budget. The trace
records the effective Actor goal for every proposal so the intervention is
auditable.

```bash
python run_settings_evidence_gated_agent_v24.py --seed 1 --max-steps 8 --fault-mode none
python run_settings_evidence_gated_agent_v24.py --seed 0 --max-steps 8 --fault-mode drop_first_setting_change
```
