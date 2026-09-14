import copy
import unittest

from src.progress_audit import classify_settings_transition


TASK = {
    "section": "notifications",
    "target_key": "sound_alerts",
    "target_value": False,
}


def state():
    return {
        "active_section": "appearance",
        "draft": {
            "sound_alerts": True,
            "weekly_summary": False,
        },
        "saved": {
            "sound_alerts": True,
            "weekly_summary": False,
        },
        "has_unapplied_changes": False,
        "confirmation_visible": False,
        "toast_visible": False,
    }


class ProgressAuditTests(unittest.TestCase):
    def test_opening_target_section_is_progress(self):
        before = state()
        after = copy.deepcopy(before)
        after["active_section"] = "notifications"

        self.assertEqual(
            classify_settings_transition(before, after, TASK),
            "progress",
        )

    def test_satisfying_target_is_progress(self):
        before = state()
        before["active_section"] = "notifications"
        after = copy.deepcopy(before)
        after["draft"]["sound_alerts"] = False
        after["has_unapplied_changes"] = True

        self.assertEqual(
            classify_settings_transition(before, after, TASK),
            "progress",
        )

    def test_unrelated_setting_change_is_irrelevant(self):
        before = state()
        before["active_section"] = "notifications"
        before["draft"]["sound_alerts"] = False
        before["has_unapplied_changes"] = True
        after = copy.deepcopy(before)
        after["draft"]["weekly_summary"] = True

        self.assertEqual(
            classify_settings_transition(before, after, TASK),
            "irrelevant",
        )

    def test_undoing_target_is_regression(self):
        before = state()
        before["active_section"] = "notifications"
        before["draft"]["sound_alerts"] = False
        before["has_unapplied_changes"] = True
        after = copy.deepcopy(before)
        after["draft"]["sound_alerts"] = True

        self.assertEqual(
            classify_settings_transition(before, after, TASK),
            "regression",
        )

    def test_opening_confirmation_is_progress(self):
        before = state()
        before["active_section"] = "notifications"
        before["draft"]["sound_alerts"] = False
        before["has_unapplied_changes"] = True
        after = copy.deepcopy(before)
        after["confirmation_visible"] = True

        self.assertEqual(
            classify_settings_transition(before, after, TASK),
            "progress",
        )

    def test_saved_target_is_complete(self):
        before = state()
        before["active_section"] = "notifications"
        before["draft"]["sound_alerts"] = False
        before["has_unapplied_changes"] = True
        before["confirmation_visible"] = True
        after = copy.deepcopy(before)
        after["saved"]["sound_alerts"] = False
        after["has_unapplied_changes"] = False
        after["confirmation_visible"] = False

        self.assertEqual(
            classify_settings_transition(before, after, TASK),
            "complete",
        )

    def test_identical_state_is_no_effect(self):
        before = state()

        self.assertEqual(
            classify_settings_transition(before, copy.deepcopy(before), TASK),
            "no_effect",
        )


if __name__ == "__main__":
    unittest.main()
