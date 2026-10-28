import unittest
from pathlib import Path


class TestStatsBombReadablePresentation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[1]
        cls.source = (root / "pitchiq" / "pages" / "2_Real_Match_Explorer.py").read_text(encoding="utf-8")

    def test_sequences_render_as_cards_with_explicit_method(self):
        self.assertIn("with st.container(border=True):", self.source)
        self.assertIn("Evidence method: completed passes recorded in the same possession", self.source)
        self.assertIn("Inspect event evidence", self.source)

    def test_event_evidence_has_human_readable_table(self):
        self.assertIn("PitchIQ ID", self.source)
        self.assertIn("Source ID", self.source)
        self.assertIn("st.dataframe(pd.DataFrame(evidence_rows)", self.source)

    def test_agent_insights_are_rendered_as_readable_cards(self):
        self.assertIn('shared_state.get("insights", [])', self.source)
        self.assertIn("Verified insights", self.source)
        self.assertIn("Why it matters", self.source)
        self.assertIn("Evidence event IDs:", self.source)

    def test_verification_failure_withholds_insights(self):
        self.assertIn("Insight narratives are withheld", self.source)
        self.assertIn("did not display insights because the evidence-verification stage did not pass", self.source)

    def test_raw_nested_agent_json_is_not_rendered(self):
        self.assertNotIn("st.json(json.loads(json.dumps(agent_output", self.source)
        self.assertNotIn("st.json(sequence)", self.source)


if __name__ == "__main__":
    unittest.main()
