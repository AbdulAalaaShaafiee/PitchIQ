"""Tests for the additive local browser UI adapter."""
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from pitchiq.main import load_match
from pitchiq.webapp import answer_match_question, make_payload


class TestPitchIQWebPayload(unittest.TestCase):
    def payload_without_local_model(self, audience="fan"):
        # Keep this adapter test deterministic and independent of Ollama state.
        with patch.dict(os.environ, {"PITCHIQ_USE_LOCAL_AI": "0"}):
            return make_payload(load_match(), audience)

    def test_payload_uses_existing_agent_pipeline(self):
        match = load_match()
        payload = self.payload_without_local_model()
        self.assertEqual(payload["match"]["match_id"], match["match_id"])
        self.assertIn("report", payload)
        self.assertIn("insights", payload)
        self.assertEqual(len(payload["steps"]), 3)
        self.assertEqual(len(payload["handoffs"]), 2)
        self.assertIn("verification", payload)

    def test_audience_switch_is_passed_to_orchestrator(self):
        payload = self.payload_without_local_model("analyst")
        self.assertEqual(payload["audience"], "analyst")
        self.assertEqual(payload["steps"][1]["status"], "completed")

    def test_unknown_audience_is_rejected(self):
        with self.assertRaises(ValueError):
            make_payload(load_match(), "coach")

    def test_invalid_match_shape_is_rejected(self):
        with self.assertRaises(ValueError):
            make_payload({"home_team": "A", "away_team": "B"}, "fan")

    def test_assistant_answers_score_from_recorded_match(self):
        match = load_match()
        answer = answer_match_question(match, "What is the score?")
        report = self.payload_without_local_model("fan")["report"]
        home, away = report["home_team"], report["away_team"]
        self.assertIn(str(report["score"][home]), answer["answer"])
        self.assertIn(str(report["score"][away]), answer["answer"])
        self.assertEqual(answer["mode"], "evidence-grounded")

    def test_assistant_declines_unavailable_predictive_metrics(self):
        answer = answer_match_question(load_match(), "What is the xG and next goal probability?")
        self.assertIn("not calculated", answer["answer"].lower())
        self.assertIn("model capability boundary", answer["source"])
        self.assertEqual(answer["evidence_event_ids"], [])

    def test_assistant_goal_answer_returns_real_evidence_ids(self):
        match = load_match()
        answer = answer_match_question(match, "What led to the goal?")
        valid_ids = {event["id"] for event in match["events"]}
        self.assertTrue(answer["evidence_event_ids"])
        self.assertTrue(set(answer["evidence_event_ids"]).issubset(valid_ids))

    def test_assistant_rejects_blank_and_oversized_questions(self):
        match = load_match()
        with self.assertRaises(ValueError):
            answer_match_question(match, "   ")
        with self.assertRaises(ValueError):
            answer_match_question(match, "x" * 501)

    def test_assistant_unknown_question_explains_supported_topics(self):
        answer = answer_match_question(load_match(), "Tell me something impossible and unrelated")
        self.assertIn("I can answer from this match's event log", answer["answer"])
        self.assertEqual(answer["mode"], "evidence-grounded")

    def test_reference_ui_contains_missing_figma_panels(self):
        html = (Path(__file__).resolve().parents[1] / "webui" / "index.html").read_text(encoding="utf-8")
        for required in (
            "AI Assistant",
            "Next goal probability",
            "Why the outcome matters",
            "One moment. Three connected decisions",
            "Player intelligence",
            "Every match has a story",
        ):
            with self.subTest(component=required):
                self.assertIn(required, html)

    def test_assistant_frontend_uses_local_evidence_endpoint(self):
        html = (Path(__file__).resolve().parents[1] / "webui" / "index.html").read_text(encoding="utf-8")
        self.assertIn("/api/assistant", html)
        self.assertIn("evidence_event_ids", html)
        self.assertIn("function sendAssistantQuestion", html)


    def test_floating_ai_hud_is_global_and_uses_same_assistant(self):
        html = (Path(__file__).resolve().parents[1] / "webui" / "index.html").read_text(encoding="utf-8")
        for required in (
            'id="floatingAiHud"',
            'id="hudLauncher"',
            'id="hudPanel"',
            'id="hudMessages"',
            'id="hudForm"',
            'data-hud-ask=',
            "sendAssistantQuestion(value,'hud')",
            "/api/assistant",
            "evidence_event_ids",
        ):
            with self.subTest(component=required):
                self.assertIn(required, html)

    def test_floating_ai_hud_has_mobile_and_accessibility_controls(self):
        html = (Path(__file__).resolve().parents[1] / "webui" / "index.html").read_text(encoding="utf-8")
        for required in (
            'aria-expanded="false"',
            'aria-live="polite"',
            'id="hudMinimize"',
            'id="hudClose"',
            "safe-area-inset-bottom",
            "prefers-reduced-motion",
            "event.key==='Escape'",
        ):
            with self.subTest(feature=required):
                self.assertIn(required, html)


if __name__ == "__main__":
    unittest.main()
