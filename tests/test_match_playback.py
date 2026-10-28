import unittest
from pathlib import Path

from pitchiq.match_playback import build_player_html
from pitchiq.statsbomb import _build_event_timeline, _timestamp_seconds


class TestSynchronizedMatchPlayback(unittest.TestCase):
    def test_timestamp_parser_supports_fractional_period_clock(self):
        self.assertEqual(_timestamp_seconds("00:01:10.500"), 70.5)
        self.assertEqual(_timestamp_seconds("00:00:00.000"), 0.0)
        self.assertIsNone(_timestamp_seconds("not-a-timestamp"))

    def test_timeline_includes_unsupported_events_and_marks_imported_events(self):
        events = [
            {
                "id": "pass-uuid", "type": {"name": "Pass"},
                "timestamp": "00:01:02.500", "minute": 2, "period": 1,
                "team": {"name": "Team A"}, "player": {"name": "Player A"},
                "pass": {"recipient": {"name": "Player B"}},
            },
            {
                "id": "receipt-uuid", "type": {"name": "Ball Receipt*"},
                "timestamp": "00:01:03.000", "minute": 2, "period": 1,
                "team": {"name": "Team A"}, "player": {"name": "Player B"},
                "ball_receipt": {},
            },
        ]
        timeline = _build_event_timeline(events, {"pass-uuid": 17})
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0]["pitchiq_event_id"], 17)
        self.assertIn("completed a pass to Player B", timeline[0]["explanation"])
        self.assertIsNone(timeline[1]["pitchiq_event_id"])
        self.assertIn("ball receipt", timeline[1]["explanation"])

    def test_shot_explanation_uses_recorded_outcome(self):
        event = {
            "id": "shot-uuid", "type": {"name": "Shot"},
            "timestamp": "00:04:00.000", "minute": 4, "period": 1,
            "team": {"name": "Team A"}, "player": {"name": "Player A"},
            "shot": {"outcome": {"name": "Saved"}},
        }
        row = _build_event_timeline([event])[0]
        self.assertIn("shot that was saved", row["explanation"])
        self.assertEqual(row["timestamp_seconds"], 240.0)

    def test_player_contains_local_video_and_synchronized_timeline_controls(self):
        html = build_player_html(
            [{"period": 1, "timestamp_seconds": 1.0, "timestamp": "00:00:01.000",
              "minute": 1, "team": "Team A", "player": "Player A", "event_type": "Pass",
              "outcome": None, "explanation": "Player A completed a pass.", "source_event_id": "evt-1",
              "pitchiq_event_id": 1}],
            "Team A vs Team B",
        )
        self.assertIn('type="file"', html)
        self.assertIn("timeupdate", html)
        self.assertIn("seekTo", html)
        self.assertIn("YouTube", html)
        self.assertIn("event explanation", html.lower())
        self.assertNotIn("__EVENTS__", html)

    def test_explorer_uses_the_playback_component(self):
        page = Path(__file__).resolve().parents[1] / "pitchiq" / "pages" / "2_Real_Match_Explorer.py"
        source = page.read_text(encoding="utf-8")
        self.assertIn("render_match_playback", source)
        self.assertIn('meta.get("event_timeline", [])', source)
        self.assertIn("Match playback + synchronized event explanations", source)


if __name__ == "__main__":
    unittest.main()
