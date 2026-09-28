# Part B Pilot Report: When Verification Becomes a Failure Channel

## Research question

Can post-action visual verification improve a GUI Agent's reliability under a
controlled dropped-click fault, and what changes when verifier output is
allowed to control retry and termination?

## Hypothesis

A verifier that reliably distinguishes `changed`, `no_effect`, and `complete`
should help recover a dropped action with one bounded retry. That benefit
depends on precision: a false `complete` prediction can terminate an otherwise
recoverable episode before the hidden task state is correct.

## Experimental design

The environment is a click-only Settings application. Tasks require navigating
to a section, changing a requested setting, saving, and confirming. In the
fault condition, the environment deterministically drops the first click that
would modify a setting. Navigation and save clicks are unaffected.

All clean arms use Qwen2.5-VL-3B-Instruct, the same Actor prompt, the same
eight-step budget, the same tasks, and the same visual verifier where present.

| Arm | Verifier use | Policy effect |
| --- | --- | --- |
| A | None | Reactive Actor baseline |
| B | Called after every action | Record only; no Actor feedback or control |
| C | Same verifier as B | Stop on `complete`; retry the first `no_effect` once |

The evaluator separately records whether the requested setting was actually
saved (`task_state_success`) and whether the Agent stopped correctly
(`agent_terminated_correctly`). Hidden state is never exposed to the Actor or
Verifier.

## Data status

The planned experiment contains 72 episodes. The saved batch contains 51:
nine seeds per arm under the dropped-action fault and eight seeds per arm under
no fault. Because the batch is incomplete and evaluates one VLM and prompt,
all results below are diagnostic pilot evidence.

## Results

| Fault mode | Arm | n | Task-state success | Correct termination | False-completion termination | Mean retries | Mean verifier latency |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Dropped action | A | 9 | 22.2% | 22.2% | 0.0% | 0.00 | 0.0 s |
| Dropped action | B | 9 | 22.2% | 22.2% | 0.0% | 0.00 | 18.5 s |
| Dropped action | C | 9 | 0.0% | 0.0% | 55.6% | 0.78 | 12.2 s |
| No fault | A | 8 | 25.0% | 12.5% | 0.0% | 0.00 | 0.0 s |
| No fault | B | 8 | 25.0% | 12.5% | 0.0% | 0.00 | 18.0 s |
| No fault | C | 8 | 0.0% | 0.0% | 62.5% | 0.75 | 11.4 s |

Pooling the two conditions for a compact descriptive view:

- A and B each reached the correct hidden task state in 4/17 episodes (23.5%).
- C reached the correct task state in 0/17 episodes.
- C terminated on a false verifier-completion signal in 10/17 episodes (58.8%).
- In shadow arm B, 27 of 36 `complete` predictions (75%) were false against
  hidden state.
- B incurred about 18 seconds of verifier generation latency per episode while
  preserving A's aggregate outcome rates, as required by the control design.

## Main finding

The pilot identifies a specific causal failure mechanism:

> The verifier's completion output was insufficiently precise for policy
> control. In shadow mode its errors were observable but harmless; in recovery
> mode the same errors became premature termination decisions and eliminated
> the baseline's observed task-state successes.

This is stronger and more useful than the vague statement that “verification
did not help.” The experiment separates three facts:

1. Verification has measurable inference cost.
2. Verification can be audited without changing policy.
3. Giving an uncalibrated signal control creates a new reliability hazard.

The result does not show that visual verification or recovery is universally
harmful. It shows that completion precision is a prerequisite for using a
verifier as a stopping authority in this setting.

## Failure analysis

### False completion

The dominant C failure was premature `verifier_complete`. Ordinary visual
change was often interpreted as completion even though the requested value had
not been saved. This failure directly converts a perception error into a policy
error.

### Correct state without correct stopping

A/B traces also show the opposite problem: the environment can reach the
correct saved state while the Actor fails to emit `finish`. Task execution and
completion recognition therefore require separate metrics.

### Repeated control selection

Several recovery investigations showed that the 3B VLM repeatedly selected an
already changed setting control instead of moving to Save. Repeat blocking
prevented some regressions but did not reliably produce the missing next-step
grounding.

### Correlated model errors

Actor and Verifier share the same base VLM. Using different prompts does not
make their errors independent. The same visual or semantic weakness can affect
both roles.

## Limitations

- The batch stopped after 51 of 72 planned episodes.
- One model, one main prompt configuration, and one synthetic Settings
  environment were evaluated.
- The sample is too small for broad statistical or cross-application claims.
- Verifier latency changes wall-clock execution, although B is isolated at the
  policy level.
- The result diagnoses this configuration; it does not compare stronger or
  independently trained verifiers.

## Next experiment

The next useful experiment should improve or calibrate the verification signal
before adding more recovery rules. A strong follow-up would compare:

1. the current shared-model verifier;
2. a verifier that requires explicit visual evidence of both the requested
   value and the saved/confirmed state;
3. a confidence or two-stage gate that abstains on uncertain completion.

The primary target metric should be completion precision against hidden state.
Only a verifier that clears a preregistered precision threshold should be
allowed to terminate the Agent. Recovery success can then be evaluated without
confounding it with an unsafe stopping signal.

The repository now includes `summarize_completion_verifier.py` for this first
offline audit. It defaults to shadow arm B, labels each prediction using hidden
state immediately after the corresponding action, and reports a conservative
qualification gate. The proposed next-study rule requires at least ten
`complete` predictions and a 95% Wilson lower bound of at least 90% precision.
This rule is prospective; it was not preregistered for the existing pilot.

## Offline completion audit result

The B-arm traces supplied 127 action-level verification samples. The binary
completion confusion matrix was 9 true positives, 27 false positives, 91 true
negatives, and 0 false negatives. Completion recall was therefore 100%, while
precision was 25.0% (95% Wilson interval: 13.8%-41.1%) and the false-positive
rate was 22.9%.

This resolves an ambiguity in the episode summary. The verifier did recognize
every observed completed state, but it was strongly over-sensitive: three of
every four completion predictions were premature. Overall accuracy (78.7%) is
misleading here because non-complete steps dominate the sample. Completion
precision is the policy-safety metric that explains C's premature stopping.
The proposed conservative control gate failed.
