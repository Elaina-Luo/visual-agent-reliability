def select_actor_goal(original_goal, verification_history, enabled=False):
    if not enabled or not verification_history:
        return original_goal
    if verification_history[-1].get("status") != "repeat_blocked":
        return original_goal

    return f"""RECOVERY SUBGOAL:
The last proposed setting-control click was blocked and was not executed.
Do not click that setting control again. Inspect the current screenshot.
If the requested setting already matches the task and enabled Save changes is
visible with unsaved changes, click Save changes now. Otherwise choose one
different visible action required to advance the original task.

Original task: {original_goal}"""
