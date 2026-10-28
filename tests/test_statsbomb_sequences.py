"""Tests for evidence-backed StatsBomb same-possession attack sequences."""
import unittest

from pitchiq.agents import PitchIQOrchestrator
from pitchiq.statsbomb import analyze_statsbomb_match, find_statsbomb_attacking_sequences


def _event(event_id, minute, team, event_type, outcome, possession="7", period=1):
    return {
        "id": event_id,
        "minute": minute,
        "period": period,
        "team": team,
        "player": f"{team} player {event_id}",
        "type": event_type,
        "outcome": outcome,
        "possession_id": possession,
        "location": {"x": 40.0, "y": 30.0},
        "end_location": {"x": 50.0, "y": 30.0},
    }


def _match(events):
    return {
        "match_id": "statsbomb-test",
        "home_team": "Home FC",
        "away_team": "Away FC",
        "events": events,
        "_pitchiq_import": {"source_provider": "StatsBomb Open Data"},
    }


class TestStatsBombPossessionSequences(unittest.TestCase):
    def test_finds_passes_with_intervening_carries_and_defensive_events(self):
        match = _match([
            _event(1, 10, "Home FC", "pass", "complete"),
            _event(2, 10, "Home FC", "carry", "successful"),
            _event(3, 11, "Home FC", "pass", "complete"),
            _event(4, 11, "Away FC", "pressure", "applied"),
            _event(5, 12, "Home FC", "pass", "complete"),
            _event(6, 13, "Home FC", "shot", "saved"),
        ])
        sequences = find_statsbomb_attacking_sequences(match)
        self.assertEqual(len(sequences), 1)
        self.assertEqual(sequences[0]["event_ids"], [1, 3, 5, 6])
        self.assertEqual(sequences[0]["passes"], 3)
        self.assertEqual(sequences[0]["evidence_basis"], "same_possession")

    def test_does_not_bridge_possessions(self):
        match = _match([
            _event(1, 10, "Home FC", "pass", "complete", possession="6"),
            _event(2, 11, "Home FC", "pass", "complete", possession="7"),
            _event(3, 12, "Home FC", "shot", "saved", possession="7"),
        ])
        self.assertEqual(find_statsbomb_attacking_sequences(match), [])

    def test_does_not_bridge_failed_pass(self):
        match = _match([
            _event(1, 10, "Home FC", "pass", "complete"),
            _event(2, 11, "Home FC", "pass", "incomplete"),
            _event(3, 11, "Home FC", "pass", "complete"),
            _event(4, 12, "Home FC", "shot", "saved"),
        ])
        self.assertEqual(find_statsbomb_attacking_sequences(match), [])

    def test_does_not_include_passes_older_than_three_minutes(self):
        match = _match([
            _event(1, 5, "Home FC", "pass", "complete"),
            _event(2, 10, "Home FC", "pass", "complete"),
            _event(3, 11, "Home FC", "shot", "saved"),
        ])
        self.assertEqual(find_statsbomb_attacking_sequences(match), [])

    def test_orchestrator_verifies_non_consecutive_possession_narrative(self):
        match = _match([
            _event(1, 10, "Home FC", "pass", "complete"),
            _event(2, 10, "Home FC", "carry", "successful"),
            _event(3, 11, "Home FC", "pass", "complete"),
            _event(4, 11, "Away FC", "pressure", "applied"),
            _event(5, 12, "Home FC", "pass", "complete"),
            _event(6, 13, "Home FC", "shot", "saved"),
        ])
        report = analyze_statsbomb_match(match)
        self.assertEqual(len(report["attacking_sequences"]), 1)
        result = PitchIQOrchestrator(analyze_statsbomb_match).run(match, "analyst")
        state = result["shared_state"]
        self.assertTrue(state["verification"]["passed"], state["verification"]["errors"])
        self.assertEqual(len(state["insights"]), 1)
        summary = state["insights"][0]["summary"].lower()
        self.assertIn("same possession", summary)
        self.assertNotIn("consecutive passes", summary)


if __name__ == "__main__":
    unittest.main()
