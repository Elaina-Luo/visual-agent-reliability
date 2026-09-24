# Evidence-gated recovery v2

This strategy is a targeted response to two observed enhanced-v1 failures:

1. A fault-dropped click produced identical before/after screenshots, but the
   shared Qwen Verifier and Completion Gate both approved `complete`.
2. The one-region repeat guard blocked four proposals, consumed half the action
   budget, and forgot an earlier changed control after the Actor changed an
   unrelated setting.

V2 remains separate from the frozen clean A/B/C comparison and enhanced v1.
It is an experimental follow-up, not a replacement for those baselines.

## Policy

- A semantic `complete` label with no deterministic pixel change becomes
  `no_effect`; it can trigger the single bounded retry.
- A `complete` label with pixel change becomes `completion_candidate`. It never
  terminates the episode by itself.
- The Actor must inspect a fresh screenshot and emit `finish`. This supplies a
  temporal confirmation step. The same-model Completion Gate is not treated as
  independent evidence and is not called.
- Every click with visible change is remembered as a forbidden region. The
  Actor prompt lists all remembered regions and explicitly directs the Actor
  toward Save, Apply, or visible confirmation actions once the setting matches.
- A blocked proposal does not consume the environment action budget. It does
  consume a separate bounded replan allowance (`--max-blocked-replans`, default
  3), preventing an infinite proposal loop.
- One `no_effect` retry remains the maximum per episode.

The result distinguishes `steps` (action-budget slots), `proposals` (Actor
decisions), and `blocked_replans`. Outputs are isolated under
`artifacts/settings_evidence_gated_agent_v2`.

## Targeted smoke tests

Run only the two diagnostic cases before considering a larger experiment:

```bash
python run_settings_evidence_gated_agent.py \
  --seed 1 --max-steps 8 --fault-mode none

python run_settings_evidence_gated_agent.py \
  --seed 0 --max-steps 8 --fault-mode drop_first_setting_change
```

Seed 1 tests whether persistent region memory redirects the Actor from the
repeated-toggle loop to Save. Seed 0 tests whether zero-change evidence prevents
the observed false completion and instead permits one retry. Do not scale the
experiment unless at least one targeted mechanism behaves as intended.
