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

Retries count against the same eight-action budget as Actor actions. Each trace
records the raw Verifier output, parsed status, Verifier latency, retry source,
and evaluator-only audit state. The audit state is written after the episode
step and is never included in either model prompt.
