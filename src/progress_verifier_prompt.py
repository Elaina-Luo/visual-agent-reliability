import json


PROGRESS_PROMPT_VERSION = "P0_zero_shot_v1"


def build_progress_verifier_prompt(goal, requested_action):
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
