import unittest

from src.repeat_guard import should_block_repeated_click


class RepeatGuardTests(unittest.TestCase):
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
