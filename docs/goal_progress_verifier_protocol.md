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
