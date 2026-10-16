
import copy
import unittest

from pitchiq.agents import (
    EvidenceVerificationAgent,
    PitchIQOrchestrator,
)
from pitchiq.insights import generate_insights
from pitchiq.main import analyze_match, load_match


class TestPitchIQAgents(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.match = load_match()
        cls.report = analyze_match(cls.match)
        cls.orchestrator = PitchIQOrchestrator(analyze_match)

    def test_all_three_agents_run(self):
        result = self.orchestrator.run(self.match, "fan")

        self.assertEqual(len(result["steps"]), 3)
        self.assertEqual(
            [step["agent"] for step in result["steps"]],
            [
                "Event Analysis Agent",
                "Storytelling Agent",
                "Evidence Verification Agent",
            ],
        )

        self.assertTrue(
            result["shared_state"]["verification"]["passed"]
        )

    def test_two_handoffs_are_recorded(self):
        result = self.orchestrator.run(self.match, "fan")

        self.assertEqual(len(result["handoffs"]), 2)

        self.assertEqual(
            result["handoffs"][0]["from"],
            "Event Analysis Agent",
        )
        self.assertEqual(
            result["handoffs"][0]["to"],
            "Storytelling Agent",
        )
        self.assertEqual(
            result["handoffs"][1]["from"],
            "Storytelling Agent",
        )
        self.assertEqual(
            result["handoffs"][1]["to"],
            "Evidence Verification Agent",
        )

    def test_fan_and_analyst_modes_differ(self):
        fan_insights = generate_insights(
            self.match, self.report, audience="fan"
        )
        analyst_insights = generate_insights(
            self.match, self.report, audience="analyst"
        )

        self.assertEqual(fan_insights[1]["audience"], "fan")
        self.assertEqual(analyst_insights[1]["audience"], "analyst")

        self.assertNotEqual(
            fan_insights[1]["summary"],
            analyst_insights[1]["summary"],
        )

        self.assertEqual(
            fan_insights[1]["evidence_event_ids"],
            analyst_insights[1]["evidence_event_ids"],
        )

    def test_verifier_rejects_unknown_event_id(self):
        insights = generate_insights(
            self.match, self.report, audience="fan"
        )

        # Deliberately introduce a nonexistent event ID.
        insights[0]["evidence_event_ids"] = [1, 2, 999]

        verification = EvidenceVerificationAgent().run(
            self.match,
            self.report,
            insights,
            "fan",
        )

        self.assertFalse(verification["passed"])
        self.assertIn(
            "All evidence IDs exist in the match events",
            verification["errors"],
        )

    def test_verifier_rejects_wrong_audience_metadata(self):
        insights = generate_insights(
            self.match, self.report, audience="fan"
        )

        verification = EvidenceVerificationAgent().run(
            self.match,
            self.report,
            insights,
            "analyst",
        )

        self.assertFalse(verification["passed"])
        self.assertIn(
            "Insights use the requested audience mode",
            verification["errors"],
        )


    def test_verifier_rejects_saved_shot_described_as_goal(self):
        insights = generate_insights(
            self.match, self.report, audience="fan"
        )
        insights[0]["summary"] = (
            "At minute 13, Harbour FC connected 2 completed "
            "passes before Player H3 scored a goal."
        )

        verification = EvidenceVerificationAgent().run(
            self.match, self.report, insights, "fan"
        )

        self.assertFalse(verification["passed"])
        self.assertIn(
            "All narrative fields are complete",
            verification["errors"],
        )

    def test_verifier_rejects_valid_ids_from_wrong_sequence(self):
        insights = generate_insights(
            self.match, self.report, audience="fan"
        )

        # These event IDs exist, but they do not form a detected attack.
        insights[0]["evidence_event_ids"] = [11, 12, 13]

        verification = EvidenceVerificationAgent().run(
            self.match, self.report, insights, "fan"
        )

        self.assertFalse(verification["passed"])
        self.assertIn(
            "Every insight maps to a detected sequence",
            verification["errors"],
        )

    def test_verifier_rejects_empty_insights(self):
        verification = EvidenceVerificationAgent().run(
            self.match, self.report, [], "fan"
        )

        self.assertFalse(verification["passed"])
        self.assertIn(
            "Every sequence has exactly one insight",
            verification["errors"],
        )

    def test_verifier_rejects_malformed_evidence_without_crashing(self):
        insights = generate_insights(
            self.match, self.report, audience="fan"
        )
        insights[0]["evidence_event_ids"] = "1, 2, 3"

        verification = EvidenceVerificationAgent().run(
            self.match, self.report, insights, "fan"
        )

        self.assertFalse(verification["passed"])
        self.assertIn(
            "All evidence IDs exist in the match events",
            verification["errors"],
        )

    def test_verifier_rejects_non_chronological_sequence(self):
        match = copy.deepcopy(self.match)

        # Make event 2 occur after the finishing shot at minute 13.
        event_2 = next(
            event for event in match["events"]
            if event["id"] == 2
        )
        event_2["minute"] = 14

        insights = generate_insights(
            match, self.report, audience="fan"
        )

        verification = EvidenceVerificationAgent().run(
            match, self.report, insights, "fan"
        )

        self.assertFalse(verification["passed"])
        self.assertIn(
            "Every insight maps to a detected sequence",
            verification["errors"],
        )

if __name__ == "__main__":
    unittest.main()
