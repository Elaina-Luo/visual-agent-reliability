import unittest

from src.repeat_guard import (
    active_forbidden_click_region,
    format_forbidden_region_prompt,
    should_block_repeated_click,
)


class RepeatGuardTests(unittest.TestCase):
    def test_exposes_changed_click_as_forbidden_region(self):
        action = {"type": "click", "x": 878, "y": 225}

        self.assertEqual(
            active_forbidden_click_region(action, "changed"),
            {
                "x": 878,
                "y": 225,
                "radius": 12,
                "reason": "previous_click_caused_visible_change",
            },
        )

    def test_no_forbidden_region_after_no_effect(self):
        action = {"type": "click", "x": 878, "y": 225}

        self.assertIsNone(
            active_forbidden_click_region(action, "no_effect")
        )

    def test_formats_hard_replanning_constraint(self):
        region = {
            "x": 876,
            "y": 298,
            "radius": 12,
            "reason": "previous_click_caused_visible_change",
        }

        prompt = format_forbidden_region_prompt(region)

        self.assertIn("HARD REPLANNING CONSTRAINT", prompt)
        self.assertIn("12 pixels", prompt)
        self.assertIn("(876, 298)", prompt)
        self.assertIn("choose a different control", prompt)

    def test_omits_constraint_without_active_region(self):
        self.assertEqual(format_forbidden_region_prompt(None), "")

    def test_blocks_same_click_after_visible_change(self):
        action = {"type": "click", "x": 878, "y": 225}

        self.assertTrue(
            should_block_repeated_click(action, action, "changed")
        )

    def test_blocks_nearby_click_within_radius(self):
        previous = {"type": "click", "x": 878, "y": 225}
        current = {"type": "click", "x": 884, "y": 231}

        self.assertTrue(
            should_block_repeated_click(current, previous, "changed")
        )

    def test_allows_different_click_after_visible_change(self):
        previous = {"type": "click", "x": 878, "y": 225}
        current = {"type": "click", "x": 771, "y": 587}

        self.assertFalse(
            should_block_repeated_click(current, previous, "changed")
        )

    def test_allows_same_click_after_no_effect(self):
        action = {"type": "click", "x": 878, "y": 225}

        self.assertFalse(
            should_block_repeated_click(action, action, "no_effect")
        )

    def test_allows_click_without_previous_execution(self):
        action = {"type": "click", "x": 878, "y": 225}

        self.assertFalse(
            should_block_repeated_click(action, None, None)
        )


if __name__ == "__main__":
    unittest.main()
