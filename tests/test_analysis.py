
import unittest

from pitchiq.main import analyze_match, load_match
from pitchiq.insights import generate_insights


class TestPitchIQ(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.match = load_match()
        cls.report = analyze_match(cls.match)

    def test_final_score_is_one_all(self):
        self.assertEqual(
            self.report["score"],
            {
                "Harbour FC": 1,
                "Riverside United": 1,
            },
        )


    def test_harbour_statistics(self):
        stats = self.report["stats"]["Harbour FC"]

        self.assertEqual(stats["shots"], 3)
        self.assertEqual(stats["passes_completed"], 8)
        self.assertEqual(stats["passes_attempted"], 8)
        self.assertEqual(stats["pass_accuracy_pct"], 100.0)
        self.assertEqual(stats["tackles_won"], 1)


    def test_riverside_statistics(self):
        stats = self.report["stats"]["Riverside United"]

        self.assertEqual(stats["shots"], 2)
        self.assertEqual(stats["passes_completed"], 3)
        self.assertEqual(stats["passes_attempted"], 4)
        self.assertEqual(stats["pass_accuracy_pct"], 75.0)
        self.assertEqual(stats["tackles_won"], 0)


    def test_attacking_sequences_have_evidence(self):
        sequences = self.report["attacking_sequences"]

        self.assertEqual(len(sequences), 2)
        self.assertEqual(sequences[0]["event_ids"], [1, 2, 3])
        self.assertEqual(sequences[1]["event_ids"], [7, 8, 9])

    def test_fan_insights_include_evidence(self):
        insights = generate_insights(
            self.match, self.report, audience="fan"
        )

        self.assertEqual(len(insights), 2)
        self.assertEqual(
            insights[1]["evidence_event_ids"],
            [7, 8, 9],
        )
        self.assertIn("goal", insights[1]["summary"].lower())

    def test_analyst_insights_include_limitations(self):
        insights = generate_insights(
            self.match, self.report, audience="analyst"
        )

        goal_insight = insights[1]

        self.assertIn("outcome: goal", goal_insight["summary"])
        self.assertIn(
            "does not prove",
            goal_insight["why_it_matters"],
        )
        self.assertEqual(
            goal_insight["evidence_event_ids"],
            [7, 8, 9],
        )

    def test_invalid_audience_is_rejected(self):
        with self.assertRaises(ValueError):
            generate_insights(
                self.match,
                self.report,
                audience="unknown",
            )


if __name__ == "__main__":
    unittest.main()
