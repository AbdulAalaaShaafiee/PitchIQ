"""Offline unit tests for the StatsBomb Open Data connector."""
import unittest
from unittest.mock import patch

from pitchiq.main import VALID_OUTCOMES, analyze_match
from pitchiq.statsbomb import (
    StatsBombDataError,
    _raw_event_to_pitchiq,
    _scale_location,
    clear_cache,
    import_statsbomb_match,
    list_competitions,
    list_matches,
)


class TestStatsBombTransformations(unittest.TestCase):
    def test_statsbomb_coordinates_scale_to_pitchiq_pitch(self):
        self.assertEqual(_scale_location([120, 80]), {"x": 105.0, "y": 68.0})
        self.assertEqual(_scale_location([60, 40]), {"x": 52.5, "y": 34.0})
        self.assertIsNone(_scale_location([121, 40]))
        self.assertIsNone(_scale_location([60]))

    def test_completed_pass_maps_to_pitchiq_pass(self):
        event = {
            "id": "evt-pass-1", "minute": 12, "period": 1,
            "type": {"name": "Pass"}, "team": {"name": "Home FC"},
            "player": {"name": "Player One"}, "possession": 9,
            "location": [60, 40],
            "pass": {"outcome": None, "end_location": [80, 45]},
        }
        converted = _raw_event_to_pitchiq(event, 1)
        if "complete" not in VALID_OUTCOMES["pass"]:
            self.skipTest("This PitchIQ version does not define a canonical completed-pass outcome.")
        self.assertIsNotNone(converted)
        self.assertEqual(converted["type"], "pass")
        self.assertEqual(converted["outcome"], "complete")
        self.assertEqual(converted["location"], {"x": 52.5, "y": 34.0})
        self.assertEqual(converted["end_location"], {"x": 70.0, "y": 38.25})
        self.assertEqual(converted["possession_id"], "9")

    def test_goal_shot_is_not_mislabeled(self):
        event = {
            "id": "evt-shot-1", "minute": 72, "period": 2,
            "type": {"name": "Shot"}, "team": {"name": "Home FC"},
            "player": {"name": "Striker"}, "possession": 21,
            "location": [110, 40],
            "shot": {"outcome": {"name": "Goal"}, "end_location": [120, 40]},
        }
        converted = _raw_event_to_pitchiq(event, 1)
        if "goal" not in VALID_OUTCOMES["shot"]:
            self.skipTest("This PitchIQ version does not define a canonical goal-shot outcome.")
        self.assertIsNotNone(converted)
        self.assertEqual(converted["type"], "shot")
        self.assertEqual(converted["outcome"], "goal")

    def test_unknown_or_unrepresentable_event_is_not_forced_into_schema(self):
        event = {
            "id": "evt-1", "minute": 18, "period": 1,
            "type": {"name": "Bad Behaviour"}, "team": {"name": "Home FC"},
            "player": {"name": "Player One"},
        }
        self.assertIsNone(_raw_event_to_pitchiq(event, 1))


class TestStatsBombCatalogue(unittest.TestCase):
    def setUp(self):
        clear_cache()

    def tearDown(self):
        clear_cache()

    @patch("pitchiq.statsbomb._fetch_json")
    def test_competitions_catalogue_normalizes_competition_seasons(self, fetch):
        fetch.return_value = [{
            "competition_id": 11, "season_id": 22,
            "competition_name": "Example League", "season_name": "2020/2021",
            "country_name": "Exampleland", "competition_gender": "male",
        }]
        result = list_competitions()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["competition_id"], 11)
        self.assertEqual(result[0]["season_name"], "2020/2021")

    @patch("pitchiq.statsbomb._fetch_json")
    def test_match_catalogue_returns_team_names_and_result(self, fetch):
        fetch.return_value = [{
            "match_id": 99, "match_date": "2022-01-01", "kick_off": "15:00:00",
            "home_team": {"home_team_name": "Home FC"},
            "away_team": {"away_team_name": "Away FC"},
            "home_score": 2, "away_score": 1,
        }]
        result = list_matches(1, 2)
        self.assertEqual(result[0]["match_id"], 99)
        self.assertEqual(result[0]["home_team"], "Home FC")
        self.assertEqual(result[0]["away_score"], 1)

    @patch("pitchiq.statsbomb._fetch_json")
    def test_import_rejects_match_not_in_selected_competition_season(self, fetch):
        fetch.return_value = []
        with self.assertRaisesRegex(StatsBombDataError, "not found"):
            import_statsbomb_match(100, 1, 2)
        self.assertEqual(fetch.call_count, 1)

    @patch("pitchiq.statsbomb._fetch_json")
    def test_imported_match_runs_through_existing_pitchiq_analysis(self, fetch):
        match_rows = [{
            "match_id": 99,
            "match_date": "2022-01-01",
            "kick_off": "15:00:00",
            "home_team": {"home_team_name": "Home FC"},
            "away_team": {"away_team_name": "Away FC"},
            "home_score": 1,
            "away_score": 0,
        }]
        event_rows = [
            {
                "id": "evt-pass-home", "minute": 7, "period": 1,
                "type": {"name": "Pass"}, "team": {"name": "Home FC"},
                "player": {"name": "Home Player"}, "possession": 1,
                "location": [60, 40], "pass": {"outcome": None, "end_location": [70, 40]},
            },
            {
                "id": "evt-goal-home", "minute": 24, "period": 1,
                "type": {"name": "Shot"}, "team": {"name": "Home FC"},
                "player": {"name": "Home Striker"}, "possession": 1,
                "location": [110, 40], "shot": {"outcome": {"name": "Goal"}, "end_location": [120, 40]},
            },
            {
                "id": "evt-pass-away", "minute": 35, "period": 1,
                "type": {"name": "Pass"}, "team": {"name": "Away FC"},
                "player": {"name": "Away Player"}, "possession": 2,
                "location": [40, 40], "pass": {"outcome": None, "end_location": [50, 40]},
            },
        ]
        competition_rows = [{
            "competition_id": 1, "season_id": 2,
            "competition_name": "Example League", "season_name": "2021/2022",
            "country_name": "Exampleland",
        }]
        fetch.side_effect = [match_rows, event_rows, competition_rows]

        imported = import_statsbomb_match(99, 1, 2)
        report = analyze_match(imported)

        self.assertEqual(imported["home_team"], "Home FC")
        self.assertEqual(imported["away_team"], "Away FC")
        self.assertEqual(imported["_pitchiq_import"]["source_provider"], "StatsBomb Open Data")
        self.assertEqual(imported["_pitchiq_import"]["imported_event_count"], 3)
        self.assertEqual(imported["_pitchiq_import"]["source_home_score"], 1)
        self.assertEqual(report["score"]["Home FC"], 1)
        self.assertEqual(report["score"]["Away FC"], 0)
        self.assertEqual(imported["events"][0]["source_event_id"], "evt-pass-home")

    def test_invalid_ids_are_rejected_before_network_access(self):
        with self.assertRaisesRegex(ValueError, "numeric"):
            list_matches("../../evil", 2)


if __name__ == "__main__":
    unittest.main()
