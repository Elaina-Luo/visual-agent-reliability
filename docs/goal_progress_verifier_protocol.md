# Goal-Progress Verifier protocol

The Goal-Progress Verifier is a separate experimental role for distinguishing
the direction of an observed GUI transition. It receives only the task goal,
requested action, before screenshot, and after screenshot. It never receives
DOM state, test IDs, fault flags, execution status, or evaluator state.

The strict output schema contains one `status` field:

- `complete`: the full goal is visibly completed and saved;
- `progress`: the transition visibly moved closer to the goal;
- `regression`: the transition undid progress or moved farther from the goal;
- `irrelevant`: the screen changed without meaningful goal progress;
- `no_effect`: the action produced no visible interface effect; or
- `uncertain`: visible evidence cannot support another label.

This protocol addresses a limitation of pixel-change fusion: pixel difference
can establish that a screen changed, but cannot establish whether that change
was useful. The distinction is evaluated relative to the natural-language
goal rather than a particular coordinate, control type, or Settings task.

The protocol is evaluated in shadow mode before it controls the Agent loop.
`run_progress_verifier_shadow.py` replays executed transitions from a saved
episode and writes `progress_shadow.json` beside the original result. Hidden
Settings state is consulted only after each model call to create an offline
oracle label; it is never included in the model prompt. The original B0 and B1
entry points and result files remain unchanged. Loop integration and recovery
behavior will be evaluated separately after shadow predictions are inspected.

## Controlled transition dataset

`generate_progress_transition_dataset.py` creates the first balanced Settings
App evaluation set. It contains one transition for every combination of the
three task families and five observable labels: `progress`, `regression`,
`irrelevant`, `no_effect`, and `complete` (15 samples total).

The generator drives the real page with Playwright and validates every label
against evaluator state. `manifest.json` contains only the goal, screenshots,
requested click, and reference label needed for offline evaluation. Hidden
before/after application states are isolated in `audit_manifest.json` and must
never be passed to a model.

Generate the dataset without loading Qwen:

```bash
python generate_progress_transition_dataset.py
```

This is a controlled Settings-specific evaluation set, not evidence that the
label protocol generalizes to arbitrary applications.

Run the frozen `P0_zero_shot_v1` prompt over the dataset:

```bash
python run_progress_transition_benchmark.py
```

The runner checkpoints after every sample and supports `--resume`. It writes
the full predictions and metrics to `progress_benchmark_p0.json`, plus a CSV
and PNG confusion matrix. The five reference labels are rows; `uncertain` is
preserved as a sixth prediction column rather than silently discarded.

The `P1_goal_state_comparison_v1` ablation keeps the model, images, label
schema, and decoding settings fixed while adding an explicit comparison of
goal conditions in the before and after states:

```bash
python run_progress_transition_benchmark.py \
  --prompt-version P1_goal_state_comparison_v1
```

P1 writes separate `progress_benchmark_p1.json` and `*_p1` confusion-matrix
artifacts, so it cannot overwrite P0. Because P1 was designed after inspecting
P0 errors on these 15 transitions, this comparison is a development-set prompt
ablation rather than a held-out generalization result.
