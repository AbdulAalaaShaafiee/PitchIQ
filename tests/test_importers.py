import json
import unittest

from pitchiq.importers import parse_uploaded_match
from pitchiq.main import analyze_match


CSV_HEADER = "id,minute,period,team,player,type,outcome,possession_id,phase,pressure,x,y,end_x,end_y,home_team,away_team,match_id"
CSV_ROWS = [
    "1,10,1,Harbour FC,Player H1,pass,complete,H-P01,build_up,low,24,32,38,31,Harbour FC,Riverside United,test-match",
    "2,11,1,Harbour FC,Player H2,pass,complete,H-P01,build_up,medium,38,31,57,29,Harbour FC,Riverside United,test-match",
    "3,12,1,Harbour FC,Player H3,shot,saved,H-P01,settled_attack,high,83,29,104,34,Harbour FC,Riverside United,test-match",
    "4,20,1,Riverside United,Player R1,shot,goal,R-P01,settled_attack,medium,88,33,104,34,Harbour FC,Riverside United,test-match",
]


class TestUploadedMatchImport(unittest.TestCase):
    def _csv(self, rows=None, header=CSV_HEADER):
        return (header + "\n" + "\n".join(rows if rows is not None else CSV_ROWS) + "\n").encode("utf-8")

    def test_csv_import_normalizes_records_and_coordinates(self):
        match = parse_uploaded_match("match.csv", self._csv())
        self.assertEqual(match["home_team"], "Harbour FC")
        self.assertEqual(match["away_team"], "Riverside United")
        self.assertEqual(match["events"][0]["location"], {"x": 24.0, "y": 32.0})
        self.assertEqual(match["_pitchiq_import"]["event_count"], 4)
        report = analyze_match(match)
        self.assertEqual(report["score"]["Riverside United"], 1)
        self.assertEqual(len(report["attacking_sequences"]), 1)

    def test_missing_coordinates_are_not_fabricated(self):
        # Keep CSV shape by explicitly blanking the four coordinate columns.
        rows = []
        for row in CSV_ROWS:
            fields = row.split(",")
            fields[10:14] = ["", "", "", ""]
            rows.append(",".join(fields))
        match = parse_uploaded_match("no-coords.csv", self._csv(rows=rows))
        self.assertIsNone(match["events"][0]["location"])
        self.assertEqual(match["_pitchiq_import"]["coordinate_events"], 0)
        self.assertTrue(any("No event coordinates" in w for w in match["_pitchiq_import"]["warnings"]))

    def test_missing_possession_ids_do_not_create_unverified_sequences(self):
        rows = []
        for row in CSV_ROWS:
            fields = row.split(",")
            fields[7] = ""
            rows.append(",".join(fields))
        match = parse_uploaded_match("no-possession.csv", self._csv(rows=rows))
        report = analyze_match(match)
        self.assertEqual(report["stats"]["Harbour FC"]["shots"], 1)
        self.assertEqual(report["attacking_sequences"], [])

    def test_invalid_event_type_is_rejected(self):
        rows = list(CSV_ROWS)
        fields = rows[0].split(",")
        fields[5] = "tennis"
        rows[0] = ",".join(fields)
        with self.assertRaisesRegex(ValueError, "unsupported type"):
            parse_uploaded_match("bad.csv", self._csv(rows=rows))

    def test_json_upload_uses_match_metadata(self):
        payload = {
            "match_id": "json-match",
            "home_team": "Harbour FC",
            "away_team": "Riverside United",
            "events": [
                {"id": 1, "minute": 10, "period": 1, "team": "Harbour FC", "player": "H1", "type": "pass", "outcome": "complete", "possession_id": "H1", "location": {"x": 1, "y": 2}},
                {"id": 2, "minute": 11, "period": 1, "team": "Riverside United", "player": "R1", "type": "shot", "outcome": "off_target"},
            ],
        }
        match = parse_uploaded_match("match.json", json.dumps(payload).encode("utf-8"))
        self.assertEqual(match["match_id"], "json-match")
        self.assertEqual(match["events"][1]["location"], None)
        self.assertEqual(match["events"][1]["possession_id"], None)


if __name__ == "__main__":
    unittest.main()
