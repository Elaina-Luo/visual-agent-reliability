# B1 visual verifier protocol

B1 adds an explicit visual verification stage after an executed click. The
Verifier receives only the task goal, requested action, before screenshot, and
after screenshot. It never receives DOM state, test IDs, fault flags,
execution status, or evaluator state.

The Verifier emits one status:

- `complete`: visible evidence shows the full goal is completed and saved;
- `changed`: visible progress occurred, but the full goal is not complete;
- `no_effect`: the relevant visible GUI state did not change; or
- `uncertain`: the images do not justify another label.

`complete` additionally requires that no visible dialog, prompt, or pending
user action remains. Opening a confirmation dialog after clicking Save is
`changed`, not `complete`; completion is only justified after the confirmation
UI has closed and visible evidence establishes that the setting was saved.

The output contract is one JSON object, such as:

```json
{"status": "no_effect"}
```

The B1 recovery policy uses hybrid verification. A deterministic pixel-change
detector decides whether the two screenshots visibly differ, while the VLM
decides whether visible evidence establishes full completion. A VLM
`no_effect` label cannot trigger a retry when the pixel detector found a
change. A VLM `complete` label can terminate the episode and is later audited
against hidden task state.

The initial detector counts pixels whose maximum RGB-channel difference is at
least 8 and marks the screenshot as changed when at least 0.01% of pixels meet
that condition. Both thresholds are stored in every result file.

The policy retries the same coordinate at most once after the fused
`no_effect` result. `complete` terminates the episode. Other results return
control to the Actor with verification feedback in visible history.

An action-level repeat guard prevents an immediate same or nearby Actor click
after the previous executed click produced the fused `changed` result. The
guard uses only action coordinates and visual-verification history; it does
not read DOM or evaluator state. The blocked proposal is recorded as
`repeat_blocked` and consumes one step of the shared budget, but is not sent
to the browser or Verifier. The guard does not interfere with the bounded
recovery retry after `no_effect`. Its coordinate radius and block count are
stored in every result file.

Whenever that region is active, the next Actor prompt also exposes it as a
hard replanning constraint with its center and radius. This gives the Actor
the constraint before it proposes another action, instead of relying only on
natural-language history after a block. The number of Actor calls containing
this constraint is logged separately. A `no_effect` result creates no
forbidden region, so the bounded recovery retry remains available.

Before a `complete` candidate may terminate the episode, a separate Completion
Gate inspects only the after screenshot and goal. It emits a strict
`pending_action` boolean. An open dialog, visible Apply/Confirm/Save decision,
or insufficient evidence of saved completion sets `pending_action` to true and
downgrades the candidate to `changed`. Gate inference or parsing failures fail
closed to `pending_action: true`. Completion Gate calls and latency are logged
separately from transition-verifier calls.

Retries count against the same eight-action budget as Actor actions. Each trace
records the raw Verifier output, parsed status, Verifier latency, retry source,
and evaluator-only audit state. The audit state is written after the episode
step and is never included in either model prompt.
