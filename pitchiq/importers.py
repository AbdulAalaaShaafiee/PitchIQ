"""Import event-level football data from a normalized CSV or JSON file.

CSV required columns: minute, team, type, outcome. Common optional aliases are
accepted for IDs, player names, periods, possession IDs, pressure labels, phases,
and pitch coordinates. Missing context is left missing rather than fabricated.
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path
from typing import Any

from pitchiq.main import VALID_OUTCOMES, VALID_TYPES

CSV_TEMPLATE = """id,minute,period,team,player,type,outcome,possession_id,phase,pressure,x,y,end_x,end_y,home_team,away_team,match_id
1,10,1,Harbour FC,Player H1,pass,complete,H-P01,build_up,low,24,32,38,31,Harbour FC,Riverside United,pitchiq-import-template
2,11,1,Harbour FC,Player H2,pass,complete,H-P01,build_up,medium,38,31,57,29,Harbour FC,Riverside United,pitchiq-import-template
3,12,1,Harbour FC,Player H3,shot,saved,H-P01,settled_attack,high,83,29,104,34,Harbour FC,Riverside United,pitchiq-import-template
4,20,1,Riverside United,Player R1,shot,goal,R-P01,settled_attack,medium,88,33,104,34,Harbour FC,Riverside United,pitchiq-import-template
"""


def _key(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").strip().lower())


ALIASES = {
    "id": ("id", "eventid", "eventidentifier"),
    "minute": ("minute", "min", "eventminute", "timestampminute"),
    "period": ("period", "half", "periodnumber"),
    "team": ("team", "teamname"),
    "player": ("player", "playername", "actor", "actorname"),
    "type": ("type", "eventtype", "action"),
    "outcome": ("outcome", "result", "eventresult"),
    "possession_id": ("possessionid", "possession", "possessionidentifier"),
    "phase": ("phase", "tacticalphase"),
    "pressure": ("pressure", "pressurelevel"),
    "x": ("x", "locationx", "startx", "xstart"),
    "y": ("y", "locationy", "starty", "ystart"),
    "end_x": ("endx", "endlocationx", "targetx", "xend"),
    "end_y": ("endy", "endlocationy", "targety", "yend"),
    "home_team": ("hometeam", "hometeamname"),
    "away_team": ("awayteam", "awayteamname"),
    "match_id": ("matchid", "fixtureid"),
}

TYPE_ALIASES = {
    "ballrecovery": "recovery",
    "recovery": "recovery",
    "interception": "interception",
    "shotattempt": "shot",
    "attempt": "shot",
    "shot": "shot",
    "goal": "goal",
    "pass": "pass",
    "tackle": "tackle",
    "carry": "carry",
    "dribble": "carry",
    "dribbling": "carry",
    "clearance": "clearance",
    "foul": "foul",
    "pressure": "pressure",
    "duel": "duel",
}

OUTCOME_ALIASES = {
    "pass": {
        "complete": "complete", "completed": "complete", "successful": "complete", "success": "complete",
        "incomplete": "incomplete", "unsuccessful": "incomplete", "failed": "incomplete", "incompletepass": "incomplete",
    },
    "shot": {
        "ontarget": "on_target", "offtarget": "off_target", "saved": "saved", "savedbygoalkeeper": "saved",
        "goal": "goal", "scored": "goal", "missedwide": "off_target", "wide": "off_target",
    },
    "goal": {"scored": "scored", "goal": "scored", "true": "scored"},
    "tackle": {"won": "won", "successful": "won", "lost": "lost", "unsuccessful": "lost"},
    "carry": {"successful": "successful", "success": "successful", "unsuccessful": "unsuccessful", "failed": "unsuccessful"},
    "interception": {"won": "won", "successful": "won", "missed": "missed", "failed": "missed"},
    "recovery": {"secured": "secured", "won": "secured", "contested": "contested"},
    "clearance": {"cleared": "cleared", "successful": "cleared", "blocked": "blocked"},
    "foul": {"committed": "committed", "drawn": "drawn"},
    "pressure": {"applied": "applied", "escaped": "escaped"},
    "duel": {"won": "won", "successful": "won", "lost": "lost", "unsuccessful": "lost"},
}


def _mapping(row: dict[str, Any]) -> dict[str, Any]:
    return {_key(k): v for k, v in row.items()}


def _pick(row: dict[str, Any], field: str) -> Any:
    for alias in ALIASES[field]:
        value = row.get(alias)
        if value is not None and str(value).strip() != "":
            return value
    return None


def _text(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _integer(value: Any, field: str) -> int:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"Event field '{field}' must be a whole number; received {value!r}.") from None
    if not number.is_integer():
        raise ValueError(f"Event field '{field}' must be a whole number; received {value!r}.")
    return int(number)


def _number(value: Any, field: str) -> float:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError(f"Coordinate '{field}' must be numeric; received {value!r}.") from None
    return number


def _location(row: dict[str, Any], raw: dict[str, Any], name: str) -> dict[str, float] | None:
    nested_value = row.get(_key(name))
    nested = _mapping(nested_value) if isinstance(nested_value, dict) else {}
    if name == "location":
        x_val = nested.get("x") if nested.get("x") not in (None, "") else _pick(row, "x")
        y_val = nested.get("y") if nested.get("y") not in (None, "") else _pick(row, "y")
        x_field, y_field = "x", "y"
    else:
        x_val = nested.get("x") if nested.get("x") not in (None, "") else _pick(row, "end_x")
        y_val = nested.get("y") if nested.get("y") not in (None, "") else _pick(row, "end_y")
        x_field, y_field = "end_x", "end_y"
    has_x = x_val is not None and str(x_val).strip() != ""
    has_y = y_val is not None and str(y_val).strip() != ""
    if not has_x and not has_y:
        return None
    if has_x != has_y:
        raise ValueError(f"Event has only one coordinate for {name}; provide both x and y or leave both blank.")
    x = _number(x_val, x_field)
    y = _number(y_val, y_field)
    if not 0 <= x <= 105 or not 0 <= y <= 68:
        raise ValueError(f"Coordinates for {name} must use PitchIQ's 105 × 68 pitch scale (x 0–105, y 0–68).")
    return {"x": x, "y": y}


def _normalise_event(raw: dict[str, Any], row_number: int, warnings: list[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"Event row {row_number} must be an object or CSV row.")
    row = _mapping(raw)

    raw_id = _pick(row, "id")
    source_event_id = _text(raw_id)
    if raw_id is None:
        event_id = row_number
        warnings.append("Some events had no ID; PitchIQ generated row-order IDs for evidence references.")
    else:
        try:
            event_id = _integer(raw_id, "id")
        except ValueError:
            event_id = row_number
            warnings.append("Some source IDs were not numeric; row-order IDs are used internally and original IDs are retained separately.")

    minute_val = _pick(row, "minute")
    if minute_val is None:
        raise ValueError(f"Event row {row_number} is missing a minute value.")
    minute = _integer(minute_val, "minute")
    if minute < 0:
        raise ValueError(f"Event row {row_number} has a negative minute.")

    period_val = _pick(row, "period")
    if period_val is None:
        if minute > 90:
            raise ValueError(f"Event row {row_number} occurs after minute 90; provide its period explicitly to distinguish normal time from extra time.")
        period = 1 if minute <= 45 else 2
        warnings.append("Some periods were inferred from minute values; check first-half stoppage time and source conventions.")
    else:
        period = _integer(period_val, "period")
        if period not in {1, 2, 3, 4}:
            raise ValueError(f"Event row {row_number} has unsupported period {period}; expected 1, 2, 3, or 4.")

    team = _text(_pick(row, "team"))
    if not team:
        raise ValueError(f"Event row {row_number} is missing a team name.")
    player = _text(_pick(row, "player")) or "Not supplied"
    if player == "Not supplied":
        warnings.append("Some events have no player name; PitchIQ displays 'Not supplied' rather than inventing one.")

    type_raw = _text(_pick(row, "type"))
    event_type = TYPE_ALIASES.get(_key(type_raw)) if type_raw else None
    if event_type not in VALID_TYPES:
        allowed = ", ".join(sorted(VALID_TYPES))
        raise ValueError(f"Event row {row_number} has unsupported type {type_raw!r}. Normalize event types to one of: {allowed}.")

    outcome_raw = _text(_pick(row, "outcome"))
    outcome = OUTCOME_ALIASES.get(event_type, {}).get(_key(outcome_raw)) if outcome_raw else None
    if outcome is None:
        # Preserve exact canonical outcomes, including values such as off_target.
        key_to_canonical = {_key(value): value for value in VALID_OUTCOMES[event_type]}
        outcome = key_to_canonical.get(_key(outcome_raw))
    if outcome not in VALID_OUTCOMES[event_type]:
        allowed = ", ".join(sorted(VALID_OUTCOMES[event_type]))
        raise ValueError(f"Event row {row_number} has unsupported outcome {outcome_raw!r} for {event_type!r}. Normalize it to one of: {allowed}.")

    possession = _text(_pick(row, "possession_id"))
    phase = _text(_pick(row, "phase"))
    pressure = _text(_pick(row, "pressure"))
    location = _location(row, raw, "location")
    end_location = _location(row, raw, "end_location")

    event = {
        "id": event_id,
        "minute": minute,
        "period": period,
        "team": team,
        "player": player,
        "type": event_type,
        "outcome": outcome,
        "possession_id": possession,
        "phase": phase,
        "pressure": pressure,
        "location": location,
        "end_location": end_location,
    }
    if source_event_id and not source_event_id.replace(".", "", 1).isdigit():
        event["source_event_id"] = source_event_id
    return event


def parse_uploaded_match(filename: str, content: bytes) -> dict[str, Any]:
    """Parse a PitchIQ-style JSON or normalized event CSV upload."""
    suffix = Path(filename).suffix.lower()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("The uploaded file must be UTF-8 encoded CSV or JSON.") from None

    source_metadata: dict[str, Any] = {}
    if suffix == ".json":
        try:
            payload = json.loads(decoded)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
            raise ValueError("JSON must be a match object with an 'events' list and optional match_id, home_team, and away_team fields.")
        records = payload["events"]
        source_metadata = {
            "match_id": payload.get("match_id"),
            "home_team": payload.get("home_team"),
            "away_team": payload.get("away_team"),
        }
    elif suffix == ".csv":
        reader = csv.DictReader(io.StringIO(decoded))
        if not reader.fieldnames:
            raise ValueError("CSV is empty or has no header row.")
        records = list(reader)
        if not records:
            raise ValueError("CSV has a header but no event rows.")
        first = _mapping(records[0])
        source_metadata = {field: _pick(first, field) for field in ("match_id", "home_team", "away_team")}
    else:
        raise ValueError("Unsupported file type. Upload a .csv or .json event file.")

    if not records:
        raise ValueError("The uploaded match contains no event rows.")

    warnings: list[str] = []
    events = [_normalise_event(record, idx, warnings) for idx, record in enumerate(records, start=1)]
    ids = [event["id"] for event in events]
    if len(ids) != len(set(ids)):
        raise ValueError("Event IDs are duplicated. Provide unique numeric IDs or leave non-numeric IDs to be assigned row-order IDs.")

    teams = list(dict.fromkeys(event["team"] for event in events))
    if len(teams) != 2:
        raise ValueError(f"PitchIQ currently expects exactly two teams in a match event file; found {len(teams)}.")

    home = _text(source_metadata.get("home_team"))
    away = _text(source_metadata.get("away_team"))
    inferred = not (home and away)
    if not home:
        home = teams[0]
    if not away:
        away = next((team for team in teams if team != home), None)
    if not home or not away or home == away or home not in teams or away not in teams:
        raise ValueError("home_team and away_team must identify the two distinct teams found in the uploaded events.")
    if inferred:
        warnings.append("Home/away labels were inferred from the first team names in the file; verify the scoreboard orientation.")

    coordinates_count = sum(event["location"] is not None for event in events)
    possession_count = sum(bool(event["possession_id"]) for event in events)
    phase_count = sum(bool(event["phase"]) for event in events)
    pressure_count = sum(bool(event["pressure"]) for event in events)
    if coordinates_count == 0:
        warnings.append("No event coordinates were supplied; the pitch will be shown without event markers.")
    elif coordinates_count < len(events):
        warnings.append(f"Only {coordinates_count} of {len(events)} events have coordinates; only those events can appear on the pitch.")
    if possession_count < len(events):
        warnings.append("Some possession IDs are missing. Attacking sequences are only reported when a sequence has consistent possession evidence.")
    if phase_count == 0:
        warnings.append("Tactical phase labels were not supplied; PitchIQ will not infer them.")
    if pressure_count == 0:
        warnings.append("Pressure labels were not supplied; PitchIQ will not infer them.")

    match_id = _text(source_metadata.get("match_id")) or f"import-{Path(filename).stem}"
    return {
        "match_id": match_id,
        "home_team": home,
        "away_team": away,
        "events": events,
        "_pitchiq_import": {
            "filename": Path(filename).name,
            "format": suffix.lstrip("."),
            "event_count": len(events),
            "coordinate_events": coordinates_count,
            "possession_events": possession_count,
            "has_coordinates": coordinates_count > 0,
            "has_possession_ids": possession_count == len(events),
            "home_away_inferred": inferred,
            "warnings": list(dict.fromkeys(warnings)),
        },
    }
