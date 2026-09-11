import json


def build_verifier_prompt(goal, requested_action):
    return f"""
You verify a GUI Agent action using only two screenshots.

Goal:
{goal}

Requested action:
{json.dumps(requested_action)}

The first image is BEFORE the action. The second image is AFTER the action.

Classify the current result:
- complete: the AFTER image visibly shows the full goal is completed and saved,
  with no dialog, prompt, or pending user action remaining.
- changed: the action caused visible progress, but the full goal is not yet complete.
- no_effect: the relevant GUI state did not visibly change.
- uncertain: the screenshots do not provide enough evidence for another label.

Completion rules:
- A Save click that opens a confirmation dialog is changed, not complete.
- If a dialog still asks the user to Apply, Confirm, Save, Cancel, or choose
  another action, the task is not complete.
- Use complete only after all required confirmation UI is closed and the AFTER
  image visibly establishes that the requested setting was saved.
- If saved completion is not visibly established, use changed or uncertain.

Use only visible evidence. You cannot access DOM state, test IDs, execution logs,
or the hidden evaluator. Do not assume a requested click succeeded.

Return exactly one JSON object and no other text:
{{"status": "complete"}}
{{"status": "changed"}}
{{"status": "no_effect"}}
{{"status": "uncertain"}}
""".strip()
