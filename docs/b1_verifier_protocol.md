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

The B1 recovery policy retries the same coordinate at most once after
`no_effect`. `complete` terminates the episode. `changed` and `uncertain`
return control to the Actor with the verification result in visible history.

Retries count against the same eight-action budget as Actor actions. Each trace
records the raw Verifier output, parsed status, Verifier latency, retry source,
and evaluator-only audit state. The audit state is written after the episode
step and is never included in either model prompt.
