import json
import unittest
from pathlib import Path

from agent_core.actions import VALID_ACTION_NAMES, normalize_response, validate_actions
from agent_core.actions.simulator import simulate_actions
from agent_core.model_config import FALLBACK_OR_RAG_MODEL, FAST_CHAT_MODEL


class Phase0ActionTests(unittest.TestCase):
    def test_unknown_actions_are_removed(self):
        actions, warnings = validate_actions(["fly", "eye_happy", "head_center"])

        self.assertNotIn("fly", actions)
        self.assertIn("eye_happy", actions)
        self.assertTrue(any(w.startswith("unknown_action") for w in warnings))

    def test_aliases_are_canonicalized(self):
        actions, _ = validate_actions(["eye_angry", "eye_surprised"])

        self.assertIn("eye_anger", actions)
        self.assertIn("eye_surprise", actions)

    def test_response_falls_back_on_invalid_json(self):
        response, warnings = normalize_response("not-json")

        self.assertIn("invalid_json", warnings)
        self.assertIn("answer", response)
        self.assertIn("actions", response)

    def test_actions_end_with_center_and_blink(self):
        actions, _ = validate_actions(["eye_blink"])

        self.assertEqual(actions[-2:], ["head_center", "eye_blink"])

    def test_simulator_returns_safe_timeline(self):
        result = simulate_actions(["head_left", "eye_left", "unknown"])

        self.assertLessEqual(len(result["actions"]), 8)
        self.assertGreater(result["total_duration_ms"], 0)
        for action in result["actions"]:
            self.assertIn(action, VALID_ACTION_NAMES)

    def test_golden_cases_exist(self):
        path = Path(__file__).parents[1] / "agent_core" / "evals" / "golden_cases.jsonl"
        cases = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

        self.assertGreaterEqual(len(cases), 20)
        for case in cases:
            self.assertIn("input", case)
            self.assertTrue(case["expect_actions_valid"])

    def test_actions_yaml_exists(self):
        path = Path(__file__).parents[1] / "agent_core" / "actions" / "actions.yaml"

        self.assertIn("max_actions: 8", path.read_text())

    def test_phase0_model_config(self):
        self.assertEqual(FAST_CHAT_MODEL, "qwen3.6-flash")
        self.assertEqual(FALLBACK_OR_RAG_MODEL, "deepseek-v4-flash")


if __name__ == "__main__":
    unittest.main()
