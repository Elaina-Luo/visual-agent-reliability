# Reliable Visual Agents

Benchmarking GUI grounding, inference failures, and eventually action
verification and recovery.

This undergraduate research project asks how visual input constraints affect
both the accuracy and execution reliability of a vision-language model (VLM),
then extends the evaluation into a controlled visual-agent environment.

## Research question

> How does resolution capping change GUI-grounding accuracy and inference
> reliability, and which target categories are most affected?

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

Resolution capping removed the single native-resolution inference error (a GPU
out-of-memory failure), but reduced grounding accuracy by 10.94 percentage
points. Coordinate predictions from resized images were mapped back to the
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

The B0 reactive runner uses Qwen2.5-VL-3B-Instruct as a screenshot-to-action
policy. It executes an eight-step `observe → decide → act → observe` loop and
saves screenshots, raw model outputs, parsed actions, hidden execution audits,
and the final result. See the [agent protocol](docs/agent_protocol.md) for the
baseline boundary.

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

Run the B1 visual-verification strategy with the same task and action budget:

```bash
python run_settings_verified_agent.py --seed 0 --fault-mode none
```

B1 reuses the Actor's loaded Qwen model as a separate semantic Verifier and
combines it with deterministic screenshot-difference detection. It can retry
one visually ineffective click and terminate on visually verified completion.
Retries count against the eight-action budget; pixel-change measurements,
Verifier calls, and latency are recorded.

See the [Settings App task specification](docs/settings_task_spec.md) for the
observation, action, success, and hidden-information contract.

## Repository structure

```text
environment/   Simple regression task and realistic Settings App for Part B
experiments/   Colab VLM inference notebook
results/       Frozen manifest, predictions, tables, and figures
src/           Dataset inspection, evaluation, sanity checks, and plotting
tests/         Lightweight parser tests
docs/          Research scope and checkpoints
```

## Limitations

- One VLM and one prompt configuration.
- A 128-example stratified pilot, not the full benchmark.
- Descriptive subgroup comparisons without confidence intervals yet.
- Capped-resolution results depend on correct preprocessing-coordinate mapping.
- Part B failure detection and recovery experiments are not complete.

See the [research plan](docs/research_plan.md) for the current checkpoints and
scope boundary.
