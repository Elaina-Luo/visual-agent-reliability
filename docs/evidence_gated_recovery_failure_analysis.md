# Evidence-Gated Recovery: Smoke-Test Failure Analysis

This document records the bounded v2.1-v2.4 investigation. The versioned
runners were removed after the diagnosis because they were short-lived
experimental branches, not final baselines. Their implementations remain
recoverable from Git history (`fb43535`, `e344937`, `c08f872`, and `c9f8f34`).

The smoke tests used two deterministic episodes rather than a full benchmark,
so these observations are failure cases and design evidence, not aggregate
performance claims.

| Version | Targeted change | No-fault seed 1 | Dropped-action seed 0 |
| --- | --- | --- | --- |
| v2.1 | two-step completion evidence and bounded invalid outputs | repeated the changed toggle until the replan limit | recovered and completed |
| v2.2 | action-aware prompt feedback | emitted the same redundant malformed coordinate three times | recovered and completed |
| v2.3 | safe repair for an unambiguous redundant coordinate | parsed the action, then repeated the changed toggle | recovered and completed |
| v2.4 | one-turn constrained recovery subgoal | still repeated the changed toggle until the replan limit | recovered and completed |

The dropped-action case shows that deterministic pixel evidence plus one retry
can recover an action that was not executed. The no-fault case shows a separate
policy failure: Qwen2.5-VL-3B-Instruct can remain locked on a setting control
after the requested value is already visible. Extra feedback, a stronger goal,
and a repeat guard prevented regression but did not reliably select the next
save action.

The next recovery method should be evaluated as a distinct strategy. A useful
candidate is a locator-only visual recovery call with a minimal prompt and no
action history. It should be compared against the retained clean A/B/C arms and
the evidence-gated v2 baseline rather than added as another prompt revision.

## Locator-only follow-up

Commit `5471c4c` tested that candidate as `locator_recovery_v1`. The locator
shared the loaded Qwen model but received no Actor or verifier history. It was
called once after the first repeat block.

The locator did not execute an action in either smoke episode because it
selected a forbidden setting coordinate:

- no-fault seed 1 returned the already changed Sound alerts toggle at
  `(877, 298)`;
- dropped-action seed 0 reached the correct saved task state, then returned
  the old Compact density coordinate at `(752, 295)` instead of terminating.

This rules out action-history contamination as the sole cause in these cases.
The same 3B VLM remained visually locked on the target setting even under a
minimal locator prompt. The strategy was removed from the maintained code
after this bounded test; its implementation remains recoverable from commit
`5471c4c`.

Future work should treat stronger grounding or a different model as a new
experimental factor. Further prompt-only recovery variants are not supported
by the current evidence.
