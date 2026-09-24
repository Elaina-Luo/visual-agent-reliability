# Evidence-gated recovery v2.1

V2.1 is a targeted follow-up to two v2 smoke-test findings. It remains a
separate strategy so the v2 trace and all earlier baselines stay reproducible.

## Observed triggers

- In the dropped-click density case, v2 recovered the correct saved state. The
  Save transition and the subsequent Confirm transition both produced a
  `completion_candidate`, but the Actor then proposed Save three more times and
  exhausted the blocked-replan allowance instead of emitting `finish`.
- In the Sound alerts case, the Actor emitted the same malformed coordinate
  object seven times. Invalid outputs consumed the action budget and the parser
  error was not exposed to the Actor.

## V2.1 policy

- Completion requires two consecutive `completion_candidate` transitions from
  distinct executed click actions. A non-candidate transition, invalid output,
  or blocked proposal resets the sequence.
- The sequence is temporal evidence, not ground truth. The hidden evaluator
  still scores false two-candidate termination as failure. Every trace record
  stores `completion_evidence_count`.
- Invalid proposals do not consume the environment action budget. The parser
  error and required JSON form are added to Actor history, and the prompt tells
  the Actor to use separate integer `x` and `y` fields.
- Invalid recovery has its own strict allowance
  (`--max-invalid-replans`, default 3). Reaching it terminates with
  `invalid_replan_limit_exhausted`.
- V2's deterministic no-change gate, one retry, persistent changed-region
  memory, and bounded blocked-replan policy remain unchanged.

## Diagnostic runs only

```bash
python run_settings_evidence_gated_agent_v21.py \
  --seed 1 --max-steps 8 --fault-mode none

python run_settings_evidence_gated_agent_v21.py \
  --seed 0 --max-steps 8 --fault-mode drop_first_setting_change
```

Do not scale this strategy from two cases unless the malformed-output feedback
changes the seed 1 trajectory and the two-candidate rule correctly terminates
the saved seed 0 trajectory. Passing deterministic unit tests establishes
policy mechanics, not VLM effectiveness or generalization.
