# Reliable Visual Agents

Benchmarking GUI grounding, failure detection, and bounded recovery.

This undergraduate research project studies where vision-language-model (VLM)
agents fail during GUI interaction and whether explicit post-action
verification and bounded recovery improve reliability. It combines an external
GUI-grounding benchmark with a controlled browser environment in which task
state, termination, injected faults, and recovery cost can be measured
separately.

## Research questions

> **Grounding:** How does input-resolution capping change GUI-grounding
> accuracy and inference reliability, and which target categories are most
> affected?
>
> **Agent reliability:** Why do visual agents fail during multi-step GUI
> interaction, and when do post-action verification and bounded recovery help
> rather than introduce new failures?

## Current findings

- On a fixed 128-example ScreenSpot subset, input-resolution capping reduced
  GUI-grounding accuracy by 10.94 percentage points while avoiding the single
  native-resolution GPU OOM observed in this sample.
- Controlled agent traces show that correct GUI state and correct termination
  are distinct reliability problems: an Agent can complete the requested state
  change but fail to recognize completion.
- Early failure analysis suggests that verification is not inherently
  beneficial: false-negative verification can trigger unnecessary recovery
  and reverse correct progress.

The final B0/B1/B2 comparison and Goal-Progress Verifier benchmark are ongoing.

## Part A — ScreenSpot grounding

Each benchmark example contains a GUI screenshot, a natural-language
instruction, and a target bounding box. Qwen2.5-VL-3B-Instruct predicts one
click coordinate. A prediction is correct when the point falls inside the
ground-truth box.

The first experiment uses one fixed stratified sample of 128 ScreenSpot
examples: 64 icon targets and 64 text targets, balanced across four target-area
quartiles. The same examples are evaluated under native and capped input
resolution.

### Initial results

| Input condition | Correct | Wrong location | No valid action | Inference error | Accuracy | Valid action rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Native resolution | 89 | 30 | 8 | 1 | **69.53%** | 92.97% |
| Capped resolution | 75 | 44 | 9 | 0 | **58.59%** | 92.97% |

Resolution capping avoided the single native-resolution GPU OOM observed in
this sample, but reduced grounding accuracy by 10.94 percentage points. Coordinate predictions from resized images were mapped back to the
correct coordinate system before evaluation; this correction was performed
offline without rerunning model inference.

![Grounding accuracy by target type](results/accuracy_by_target_type.png)

Text targets remained easier than icon targets in both conditions. The
observed reduction was 12.50 percentage points for text and 9.38 points for
icons.

![Grounding accuracy by target size](results/accuracy_by_target_size.png)

The size effect was not monotonic. Medium targets showed the largest observed
decline (25.00 percentage points), while large targets improved by 3.12 points.
Because each size group contains only 32 examples, these are preliminary
descriptive results rather than claims of statistical significance.

### Reproduce the evaluation components

Inspect one ScreenSpot sample:

```powershell
.\.venv\Scripts\python.exe src\dataset.py
```

Run the evaluator sanity check:

```powershell
.\.venv\Scripts\python.exe src\run_sanity_check.py
```

The model inference notebook is
[`experiments/screenspot_qwen_baseline.ipynb`](experiments/screenspot_qwen_baseline.ipynb).
It is intended for a GPU-backed Google Colab runtime. The frozen sample
manifest and per-example predictions are stored in [`results/`](results/).

Regenerate the result figures:

```powershell
.\.venv\Scripts\python.exe src\plot_results.py
```

## Part B — Controlled agent reliability

The primary Part B environment is a realistic, click-only Settings App with
Appearance, Notifications, and Privacy task families. Each task requires four
visible interactions: navigate to a section, change one setting, save, and
confirm. Hidden evaluator state checks the saved value and is never provided to
the Agent.

The original six-card environment remains as a small regression test. Both
environments now support deterministic dropped-click faults with evaluator-only
audit state. The Settings App drops the first click that would change a setting
while leaving navigation and submission actions unaffected. Scripted checks
compare no retry against one repeated setting click; they validate the fault
mechanism, not autonomous Agent recovery.

### Experimental strategies

All strategies use the same Qwen2.5-VL-3B-Instruct model, click-only action
space, task distribution, and eight-action budget. Retries count as actions;
Verifier calls and latency are reported rather than treated as free.

| Strategy | Added mechanism | Purpose |
| --- | --- | --- |
| **B0 — Reactive** | Screenshot-to-action Actor only | Establish the no-verification baseline |
| **B1 — Verification** | Semantic before/after judgment plus deterministic pixel-change detection | Measure whether an action had a visible effect without changing policy in shadow evaluation |
| **B2 — Verification + bounded recovery** | At most one no-effect retry, completion gate, and repeated-click guard | Test whether constrained recovery improves completion without unbounded action loops |

`run_settings_agent.py` implements B0. The verification components can be
evaluated in shadow mode on saved traces; `run_settings_verified_agent.py`
implements the current bounded-recovery strategy. Hidden evaluator state is
written only for offline audit and is never included in an Actor or Verifier
prompt. See the [agent protocol](docs/agent_protocol.md) for the baseline
boundary.

B1 is an observational ablation: verification is evaluated without influencing
the Actor. B2 then tests the causal effect of allowing verification signals to
change behavior through bounded recovery.

### Development smoke results

The initial three no-fault B0 episodes are development cases, not a final
statistical comparison:

| Metric | Result |
| --- | ---: |
| Full task-and-termination success | 0/3 |
| Correct final GUI task state | 1/3 |
| Correct termination | 0/3 |

These runs motivated separating task-state success from correct termination
instead of reporting one ambiguous success flag.

### Observed failure cases

| Failure | Trace evidence | Reliability implication |
| --- | --- | --- |
| **Termination failure** | The Compact setting was saved with no unapplied changes, but the Actor continued until its action budget was exhausted. | Reaching the requested GUI state does not guarantee that an Agent knows when to stop. |
| **Repeated-action loop** | After correctly turning off Sound alerts, the Actor repeatedly clicked the same switch, reversed progress, and never saved. | Grounding the correct control is insufficient without state-change and progress tracking. |
| **False-negative verification** | Hidden offline audit recorded `comfortable → compact`, while the visual Verifier classified the click as `no_effect` and triggered an unnecessary retry. | A noisy Verifier can make bounded recovery less reliable rather than more reliable. |

Start the environment:

```powershell
.\.venv\Scripts\python.exe run_environment.py
```

Run the scripted action/scoring check:

```powershell
.\.venv\Scripts\python.exe run_scripted.py
```

Run the multi-step Settings App check:

```powershell
.\.venv\Scripts\python.exe run_settings_scripted.py
```

Run one B0 episode in a GPU environment after installing
`requirements-agent.txt` and Playwright Chromium:

```bash
python run_settings_agent.py --seed 0 --fault-mode none
```

After the normal smoke test is inspected, run one dropped-click episode:

```bash
python run_settings_agent.py --seed 1 --fault-mode drop_first_setting_change
```

Run the bounded visual-verification strategy with the same task and action
budget:

```bash
python run_settings_verified_agent.py --seed 0 --fault-mode none
```

B2 reuses the Actor's loaded Qwen model as a separate semantic Verifier and
combines it with deterministic screenshot-difference detection. It can retry
one visually ineffective click and terminate through an independent completion
gate. Pixel-change measurements, blocked repeats, Verifier calls, and latency
are recorded.

### Goal-progress benchmark — ongoing

Pixel difference can establish that the screen changed, but not whether the
change was progress, regression, or irrelevant. A separate Goal-Progress
Verifier therefore predicts one of `progress`, `regression`, `irrelevant`,
`no_effect`, `complete`, or `uncertain` from the goal, requested click, and
before/after screenshots.

Generate the balanced 15-transition Settings pilot and evaluate the frozen
`P0_zero_shot_v1` prompt without letting it control the Agent:

```bash
python generate_progress_transition_dataset.py
python run_progress_transition_benchmark.py
```

The controlled pilot contains three task families and three examples per
reference label (`progress`, `regression`, `irrelevant`, `no_effect`, and
`complete`). The runner reports overall and per-class metrics and saves the
complete predictions plus CSV/PNG confusion matrices. Hidden Settings state is
isolated in the dataset's audit manifest and is never included in model input.
The dataset and evaluator are complete; valid GPU inference and analysis are
ongoing, so no Goal-Progress accuracy is reported yet.

See the [Settings App task specification](docs/settings_task_spec.md) for the
observation, action, success, and hidden-information contract.

## Repository structure

```text
environment/   Simple regression task and realistic Settings App for Part B
experiments/   Colab VLM inference notebook
results/       Frozen manifest, predictions, tables, and figures
src/           Dataset inspection, evaluation, sanity checks, and plotting
tests/         Unit tests for protocols, policies, metrics, and evaluators
docs/          Research scope and checkpoints
```

## Limitations

- One VLM and one prompt configuration.
- A 128-example stratified pilot, not the full benchmark.
- Descriptive subgroup comparisons without confidence intervals yet.
- Capped-resolution results depend on correct preprocessing-coordinate mapping.
- The three B0 episodes are development smoke tests rather than a held-out
  statistical evaluation.
- The 15-transition Goal-Progress set is a small Settings-specific pilot and
  does not establish cross-application generalization.
- The final B0/B1/B2 comparison and valid Goal-Progress GPU benchmark remain
  ongoing.

See the [research plan](docs/research_plan.md) for the current checkpoints and
scope boundary.
