# Research plan

## Project question

How do visual input constraints affect both GUI-grounding accuracy and
inference reliability, and can a visual agent later detect and recover from
perception or action failures?

## Part A — GUI grounding evaluation

Evaluate a pretrained vision-language model on ScreenSpot using screenshot and
instruction inputs. The model predicts a click point and receives credit when
the point lies inside the ground-truth target bounding box.

The first controlled comparison uses the same stratified sample of 128 targets
under two image-processing conditions:

- Native resolution: preserve the source image resolution.
- Capped resolution: restrict visual pixels to reduce GPU memory pressure.

Report accuracy, valid-action rate, inference errors, target-type breakdowns,
and target-size breakdowns. Treat the 128-sample study as a pilot rather than a
population-level estimate.

## Part B — Agent reliability

Use the controlled six-card web environment to study action verification and
bounded recovery. Compare a reactive agent, verification-only agent, and an
agent with verification plus bounded retry under matched normal and injected
click-failure conditions.

Part B starts only after the Part A evaluation pipeline and results are
packaged reproducibly.

## Current checkpoints

- [x] Inspect and visualize a real ScreenSpot sample.
- [x] Implement point-in-bounding-box evaluation and an oracle sanity check.
- [x] Run a Qwen2.5-VL-3B pilot on 10 samples.
- [x] Freeze a stratified 128-sample manifest.
- [x] Run native-resolution and capped-resolution conditions.
- [x] Correct resized-image coordinate mapping without rerunning inference.
- [x] Save overall, target-type, and target-size results.
- [ ] Document the Colab environment and exact inference configuration.
- [ ] Add paired failure examples and uncertainty estimates.
- [ ] Validate deterministic click-failure injection locally.
- [ ] Connect the VLM agent and begin Part B controlled comparisons.

## Interpretation boundary

The current results establish behavior on one model, one prompt, and one
stratified pilot sample. They do not establish statistical significance,
generalization to other models, or universal effects of resolution capping.
