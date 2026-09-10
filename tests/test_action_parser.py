import unittest

from src.action_parser import parse_agent_action


class ParseAgentActionTests(unittest.TestCase):
    def parse(self, raw_output):
        return parse_agent_action(
            raw_output,
            viewport_width=980,
            viewport_height=644,
        )

    def test_parses_click(self):
        self.assertEqual(
            self.parse('{"type": "click", "x": 420, "y": 210}'),
            {"type": "click", "x": 420, "y": 210},
        )

    def test_parses_finish(self):
        self.assertEqual(
            self.parse('{"type": "finish"}'),
            {"type": "finish"},
        )

    def test_rejects_out_of_bounds_click(self):
        with self.assertRaises(ValueError):
            self.parse('{"type": "click", "x": 980, "y": 100}')

    def test_rejects_non_integer_coordinates(self):
        with self.assertRaises(ValueError):
            self.parse('{"type": "click", "x": 20.5, "y": 100}')

    def test_rejects_extra_fields(self):
        with self.assertRaises(ValueError):
            self.parse('{"type": "finish", "reason": "done"}')

    def test_rejects_missing_json(self):
        with self.assertRaises(ValueError):
            self.parse("click the save button")


if __name__ == "__main__":
    unittest.main()
