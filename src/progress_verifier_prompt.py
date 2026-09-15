import json


P0_PROMPT_VERSION = "P0_zero_shot_v1"
P1_PROMPT_VERSION = "P1_goal_state_comparison_v1"
PROGRESS_PROMPT_VERSIONS = (P0_PROMPT_VERSION, P1_PROMPT_VERSION)
PROGRESS_PROMPT_VERSION = P0_PROMPT_VERSION


def build_progress_verifier_prompt(
    goal,
    requested_action,
    prompt_version=PROGRESS_PROMPT_VERSION,
):
    if prompt_version == P1_PROMPT_VERSION:
        return build_goal_state_comparison_prompt(goal, requested_action)
    if prompt_version != P0_PROMPT_VERSION:
        raise ValueError(f"Unknown progress prompt version: {prompt_version}")
    return f"""
You evaluate whether one GUI action changed progress toward a task goal.
Use only the two screenshots, the goal, and the requested action.

Goal:
{goal}

Requested action:
{json.dumps(requested_action)}

The first image is BEFORE the action. The second image is AFTER the action.

Return exactly one status:
- complete: the AFTER image visibly shows the full goal is completed and
  saved, with no dialog, prompt, or pending user action remaining.
- progress: the action visibly moved closer to the goal but the full goal is
  not complete. Opening the section containing a required control counts as
  progress.
- regression: the action visibly moved farther from the goal or undid a
  previously satisfied goal condition.
- irrelevant: the screen visibly changed, but the change neither completed a
  required goal condition nor moved meaningfully closer to the goal.
- no_effect: there is no visible action effect relevant to the interface.
- uncertain: the screenshots do not justify another label.

Important distinctions:
- Do not call every pixel or control change progress. Judge direction relative
  to the stated goal.
- Changing an unrelated setting is irrelevant, even if the screen changed.
- Reversing a target control from its requested state is regression.
- A Save click that opens a confirmation dialog is progress, not complete.
- If Apply, Confirm, Save, Cancel, or another required decision remains
  visible, the task is not complete.
- If the relevant control state or saved state cannot be read reliably, use
  uncertain rather than guessing.

You cannot access DOM state, test IDs, fault flags, execution logs, or the
hidden evaluator. Do not assume the requested click succeeded.

Return exactly one JSON object and no other text:
{{"status": "complete"}}
{{"status": "progress"}}
{{"status": "regression"}}
{{"status": "irrelevant"}}
{{"status": "no_effect"}}
{{"status": "uncertain"}}
""".strip()


def build_goal_state_comparison_prompt(goal, requested_action):
    return f"""
You classify how a single GUI action changed progress toward a task goal.
Use only the BEFORE screenshot, AFTER screenshot, goal, and requested action.

Goal:
{goal}

Requested action:
{json.dumps(requested_action)}

The first image is BEFORE the action. The second image is AFTER the action.
The requested action is context only: never assume that it succeeded.

Perform this comparison before choosing a label:
1. Decompose the goal into visible required conditions, including the target
   setting, whether changes are saved, and whether a confirmation or other
   required user action remains.
2. Determine which required conditions are visibly satisfied in BEFORE.
3. Determine which required conditions are visibly satisfied in AFTER.
4. Compare AFTER with BEFORE relative to those same goal conditions.

Choose exactly one label using this priority order:
- complete: every visible goal condition is satisfied in AFTER, changes are
  saved, and no dialog, prompt, or pending user action remains.
- no_effect: BEFORE and AFTER show no meaningful interface change caused by
  the action.
- regression: AFTER is farther from the goal than BEFORE, including undoing a
  previously satisfied target condition.
- progress: AFTER is closer to the goal than BEFORE, but at least one required
  condition remains. Opening the required section or opening a required save
  confirmation dialog counts as progress.
- irrelevant: the interface visibly changed, but no required goal condition
  became more or less satisfied.
- uncertain: the screenshots do not provide enough visible evidence for any
  label above.

Do not classify direction from whether a switch looks on or off in isolation.
Relate its visible state to the requested goal. A change to an unrelated
setting is irrelevant. A Save click that leaves Apply, Confirm, Save, Cancel,
or another required decision visible is not complete.

You cannot access DOM state, test IDs, fault flags, execution logs, or hidden
evaluator state.

Return exactly one JSON object and no other text:
{{"status": "complete"}}
{{"status": "progress"}}
{{"status": "regression"}}
{{"status": "irrelevant"}}
{{"status": "no_effect"}}
{{"status": "uncertain"}}
""".strip()
