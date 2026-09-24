# Clean A/B/C ablation

Base: `74ba595 Add control-held-out progress transitions`.

Research question: what is the effect of using visual verification for recovery,
separately from merely paying its inference cost?

| Arm | Verification | Policy |
| --- | --- | --- |
| A (default) | None | Existing reactive Actor |
| B | Audit every valid action | Exactly A's policy; feedback stays in trace |
| C | Same verifier as B | Stop on complete; at most one automatic no_effect retry per episode |

All arms use `run_settings_agent.py` and the unchanged reactive Actor prompt.
B/C use `QwenSettingsVerifier`, its existing prompt and parser. Clean verification
uses the raw parsed VLM label: no pixel fusion, completion gate, repeat guard,
forbidden region, or verification history in Actor input. The original
`run_settings_verified_agent.py` remains the separate enhanced strategy, unchanged.
Do not pool enhanced results into clean C.

## Run paired episodes

Use the same model, seed, fault mode and max-steps for each arm:

```powershell
python run_settings_agent.py --strategy A --seed 0 --max-steps 8 --fault-mode drop_first_setting_change
python run_settings_agent.py --strategy B --seed 0 --max-steps 8 --fault-mode drop_first_setting_change
python run_settings_agent.py --strategy C --seed 0 --max-steps 8 --fault-mode drop_first_setting_change
python -m unittest discover -s tests -v
```

Repeat across a preregistered seed set and both fault modes (`none` and
`drop_first_setting_change`). Compare paired success and termination outcomes,
retry counts, action counts, and latency. No empirical success improvement is
claimed by the unit tests.

For the quantitative run, load the model once and execute 12 seeds (two per
task family) across both fault modes and all three arms:

```bash
python run_settings_ablation_batch.py --seeds 0:12 --run-id clean_abc_v1
```

This creates an isolated directory at
`artifacts/settings_ablation_runs/clean_abc_v1`. If Colab disconnects, rerun
the exact command with `--resume`; completed result files are skipped. Never
reuse a run id without `--resume`. To regenerate tables from saved results:

```bash
python summarize_settings_ablation.py \
  artifacts/settings_ablation_runs/clean_abc_v1
```

The run directory contains `manifest.json`, `episodes.csv`, `aggregate.csv`,
`paired.csv`, and `summary.json`. The episode table includes false completion
terminations and false `complete` predictions checked against hidden evaluator
state. The paired table aligns A/B/C by seed and fault mode. Summaries are
rewritten after every completed episode so an interrupted run remains usable.

Outputs: `artifacts/settings_agent/<fault>/<task>/result.json` for A;
`artifacts/settings_clean_B/...` and `artifacts/settings_clean_C/...` for B/C.
Rerunning the same arm/fault/task overwrites its output; archive independent
replications before rerunning.

## Exact control semantics

- Verification runs after every valid click, including fault-dropped clicks and
  the automatic retry. Actor finish is a no-op action audited with identical
  before/after images. Invalid Actor output is not an action and is not verified.
- B ignores all labels, malformed responses, and verifier exceptions. It never
  schedules a retry or vetoes Actor finish. Errors are logged as uncertain.
- C stops after a click labeled complete. This label is a model prediction,
  not ground truth: evaluator state independently determines success.
- C's first no_effect may schedule one retry of that exact click, if budget
  remains. That retry is itself verified. Neither its no_effect nor later
  no_effect labels can schedule another retry in the episode.
- Retry consumes one step and appears as an ordinary action in recent_actions;
  no verifier label, reason, or hidden environment state enters the Actor input.
  Remaining budget reflects the retry. C's trajectory can consequently differ
  from A/B, but its prompt template and input contract are unchanged.
- Actor finish remains authoritative in all arms, even if its audit disagrees.
  False finishes are counted as failed termination by the evaluator.
- The existing executor's render wait is shared across arms. B/C necessarily
  introduce screenshot/inference overhead. For dynamic GUI environments, wall
  time can change subsequent observations even though B never controls policy;
  the unit tests establish policy isolation, not live timing equivalence.

## Metrics

- `task_state_success`, `agent_terminated_correctly`, `termination_reason`:
  existing evaluator semantics, with final_state retained for audit.
- `steps`: budget slots consumed, including invalid outputs, Actor inference
  failures and retries. `action_count`: valid clicks plus finish signals;
  `click_count`: attempted clicks, including fault-dropped clicks and retries.
- `retry_count`: automatic retries actually attempted (0 or 1).
- `actor_latency_seconds` / `verifier_latency_seconds`: summed generation
  latencies returned by the model wrappers. Unavailable latency is not estimated.
  Trace records retain missing verifier latency as null.
- `actor_wall_latency_seconds` / `verifier_wall_latency_seconds`: measured call
  time, including failed calls, separately from model generation latency.
- `actor_calls`, `verifier_calls`: include failed invocations.
- `failure_details`: state mismatch, missing stop signal, premature termination,
  and per-step Actor/parser/verifier errors. Verifier errors can coexist with a
  successful episode. Each verification retains raw output, status and latency.

The test suite uses deterministic fake Actors/verifiers and a fake page to test
runner policy. It does not load Qwen or measure real model/GPU performance.
