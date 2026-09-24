import unittest

from src.repeat_guard import (
    active_forbidden_click_region,
    format_forbidden_region_prompt,
    should_block_repeated_click,
    click_in_forbidden_regions,
    format_forbidden_regions_prompt,
    remember_changed_click,
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

    def test_remembers_multiple_changed_regions(self):
        first = {"type": "click", "x": 878, "y": 298}
        second = {"type": "click", "x": 850, "y": 583}
        regions = remember_changed_click([], first, "changed")
        regions = remember_changed_click(regions, second, "changed")

        self.assertEqual(len(regions), 2)
        self.assertTrue(click_in_forbidden_regions(first, regions))
        self.assertTrue(click_in_forbidden_regions(second, regions))

    def test_does_not_remember_no_effect_or_duplicate_click(self):
        action = {"type": "click", "x": 878, "y": 298}
        regions = remember_changed_click([], action, "no_effect")
        self.assertEqual(regions, [])
        regions = remember_changed_click([], action, "changed")
        self.assertEqual(
            remember_changed_click(regions, action, "changed"), regions
        )

    def test_multi_region_prompt_directs_actor_to_save(self):
        prompt = format_forbidden_regions_prompt([
            {"x": 878, "y": 298, "radius": 12},
            {"x": 878, "y": 370, "radius": 12},
        ])
        self.assertIn("(878, 298, radius 12)", prompt)
        self.assertIn("(878, 370, radius 12)", prompt)
        self.assertIn("Save, Apply", prompt)
        self.assertIn("Do not change an unrelated setting", prompt)


if __name__ == "__main__":
    unittest.main()
