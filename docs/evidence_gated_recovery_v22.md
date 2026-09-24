# Evidence-Gated Recovery v2.2

v2.2 keeps every v2.1 policy rule and adds action-aware recovery feedback for
the Actor. It addresses a failure where a setting click visibly succeeded, but
the Actor repeatedly proposed the same toggle instead of saving the pending
change.

After a `changed` result, the prompt asks the Actor to compare the visible
control state with the goal before clicking another setting. When the target
already matches and the interface shows unsaved changes, it directs attention
to the visible save action. After `repeat_blocked`, it explicitly states that
the blocked proposal was not executed and requests a distinct next step.

The repeat guard, completion evidence rule, retry limit, action budget, and
invalid-output budget are unchanged. v2.1 remains the default behavior of its
own runner; v2.2 has a separate runner and artifact directory.

```bash
python run_settings_evidence_gated_agent_v22.py --seed 1 --max-steps 8 --fault-mode none
python run_settings_evidence_gated_agent_v22.py --seed 0 --max-steps 8 --fault-mode drop_first_setting_change
```
