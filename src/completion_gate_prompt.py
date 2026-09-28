BASELINE_PROMPT_VERSION = "G0_baseline_v1"
EVIDENCE_PROMPT_VERSION = "G1_evidence_required_v1"
COMPLETION_GATE_PROMPT_VERSIONS = (
    BASELINE_PROMPT_VERSION,
    EVIDENCE_PROMPT_VERSION,
)


def build_completion_gate_prompt(goal, prompt_version=BASELINE_PROMPT_VERSION):
    if prompt_version == EVIDENCE_PROMPT_VERSION:
        return f"""
You are a conservative final-completion auditor for a GUI Agent.

Goal:
{goal}

Inspect only the current screenshot. The safe default is that another action is
pending. Set pending_action to false only if the screenshot visibly proves ALL
of the following:

1. The exact setting named in the goal visibly has the requested value.
2. The change is visibly saved or committed, rather than merely selected.
3. No modal, confirmation dialog, enabled Save/Apply/Confirm control, unsaved
   indicator, or other required action remains.
4. The full goal is complete; ordinary navigation or partial progress is not
   completion.

A changed control, open confirmation dialog, toast by itself, or the fact that
the Agent requested Save is insufficient evidence. Do not guess hidden state.
When any required evidence is absent, occluded, or ambiguous, return true.

Use only visible evidence. You cannot access DOM state, test IDs, execution
logs, action history, or the hidden evaluator.

Return exactly one JSON object and no other text:
{{"pending_action": true}}
or
{{"pending_action": false}}
""".strip()
    if prompt_version != BASELINE_PROMPT_VERSION:
        raise ValueError(f"Unknown completion gate prompt: {prompt_version}")
    return f"""
You are the final stop gate for a GUI Agent.

Goal:
{goal}

Inspect only the current screenshot. Decide whether the user must perform any
additional visible action before the goal is fully completed and saved.

Set pending_action to true when:
- a modal or dialog is open;
- Apply, Confirm, Save, Continue, Cancel, or another decision is still visible;
- changes appear selected but not visibly saved; or
- the screenshot does not clearly establish final saved completion.

Set pending_action to false only when no further user action is visibly needed
and the screenshot clearly establishes that the full goal is completed and
saved.

Do not infer completion merely because Save was clicked. Use only visible
evidence. You cannot access DOM state, test IDs, execution logs, or the hidden
evaluator. When evidence is insufficient, use true so the Agent continues.

Return exactly one JSON object and no other text:
{{"pending_action": true}}
or
{{"pending_action": false}}
""".strip()
