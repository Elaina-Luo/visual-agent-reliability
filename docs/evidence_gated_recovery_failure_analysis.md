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
