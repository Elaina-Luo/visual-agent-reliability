def build_action_aware_recovery_context(verification_history):
    if not verification_history:
        return ""

    latest_status = verification_history[-1].get("status")
    if latest_status == "changed":
        return """

ACTION-AWARE RECOVERY:
The most recent executed click visibly changed the interface. Treat that as
evidence that the action took effect. Before clicking any setting control,
compare its current visible state with the goal. Do not immediately click the
same control again. If the requested setting now visibly matches the goal and
the screenshot shows unsaved changes or a Save changes button, choose the
visible save action.
"""
    if latest_status == "repeat_blocked":
        return """

ACTION-AWARE RECOVERY:
The most recent proposal was blocked and was not executed. A prior click near
that coordinate already changed the interface. Do not propose that control
again. Inspect the current screenshot and choose the next distinct task step.
If the requested setting already visibly matches the goal and the screenshot
shows unsaved changes or a Save changes button, choose the visible save action.
"""
    return ""
