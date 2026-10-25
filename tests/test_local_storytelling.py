import os
import unittest
from unittest.mock import patch

from pitchiq.local_storytelling import _clean_and_validate, add_local_ai_commentary


class TestLocalStorytelling(unittest.TestCase):
    def test_rejects_new_numeric_claims(self):
        self.assertEqual(
            _clean_and_validate("They completed 4 passes before the shot.", "They completed 2 passes before the shot."),
            "",
        )

    def test_accepts_short_paraphrase_without_new_numbers(self):
        self.assertEqual(
            _clean_and_validate("At minute 13, Harbour FC completed 2 passes before the shot.", "At minute 13, Harbour FC connected 2 completed passes before the shot."),
            "At minute 13, Harbour FC completed 2 passes before the shot.",
        )

    def test_disabled_mode_keeps_original_verified_summary(self):
        insight = {"summary": "At minute 13, the player had a shot saved."}
        with patch.dict(os.environ, {"PITCHIQ_USE_LOCAL_AI": "0"}):
            result = add_local_ai_commentary({}, [insight], "fan")
        self.assertEqual(result[0]["summary"], "At minute 13, the player had a shot saved.")
        self.assertEqual(result[0]["ai_commentary"], "")
        self.assertEqual(result[0]["ai_commentary_status"], "disabled")


if __name__ == "__main__":
    unittest.main()
