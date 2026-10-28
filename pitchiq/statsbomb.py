"""StatsBomb Open Data connector for PitchIQ.

Uses only the public Hudl StatsBomb Open Data GitHub repository. This is a
historical/open-data connector, not a live-score or live-event feed.

Source: https://github.com/hudl/open-data
Attribution: when publishing/sharing analysis, credit StatsBomb and use the
logo from https://statsbomb.com/media-pack/ as requested in the repository README.
"""
from __future__ import annotations

from copy import deepcopy
from functools import lru_cache
import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pitchiq.importers import parse_uploaded_match
from pitchiq.main import VALID_OUTCOMES, VALID_TYPES, analyze_match

REPOSITORY_URL = "https://github.com/hudl/open-data"
RAW_BASE_URL = "https://raw.githubusercontent.com/hudl/open-data/master/data"
MEDIA_PACK_URL = "https://statsbomb.com/media-pack/"
REQUEST_TIMEOUT_SECONDS = 25
MAX_JSON_BYTES = 50 * 1024 * 1024


class StatsBombDataError(RuntimeError):
    """A clear, user-facing error while retrieving or importing open data."""


def _fetch_json(relative_path: str) -> Any:
    """Fetch JSON from a fixed path within StatsBomb Open Data."""
    # Callers build paths only from validated numeric IDs; do not accept full URLs.
    if not relative_path or relative_path.startswith(("/", "\\")) or ".." in relative_path:
        raise StatsBombDataError("Invalid StatsBomb Open Data path.")
    url = f"{RAW_BASE_URL}/{relative_path}"
    request = Request(
        url,
        headers={
            "User-Agent": "PitchIQ-OpenData-Connector/1.0",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read(MAX_JSON_BYTES + 1)
            if len(body) > MAX_JSON_BYTES:
                raise StatsBombDataError("The selected data file exceeded PitchIQ's 50 MB safety limit.")
    except HTTPError as exc:
        if exc.code == 404:
            raise StatsBombDataError(
                "StatsBomb Open Data does not contain this file. The match may be outside the published open-data collection."
            ) from None
        raise StatsBombDataError(f"StatsBomb Open Data returned HTTP {exc.code}.") from None
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise StatsBombDataError(
            f"Could not reach StatsBomb Open Data. Check your internet connection and try again. Details: {reason}"
        ) from None
    except TimeoutError:
        raise StatsBombDataError("StatsBomb Open Data timed out. Please try again.") from None

    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise StatsBombDataError("StatsBomb Open Data returned invalid JSON.") from None


def _numeric_id(value: Any, field: str) -> str:
    text = str(value).strip() if value is not None else ""
    if not re.fullmatch(r"\d+", text):
        raise ValueError(f"{field} must be a numeric StatsBomb ID.")
    return text


def _name(value: Any, *keys: str) -> str | None:
    if isinstance(value, dict):
        for key in keys:
            candidate = value.get(key)
            if candidate is not None and str(candidate).strip():
                return str(candidate).strip()
        candidate = value.get("name")
        if candidate is not None and str(candidate).strip():
            return str(candidate).strip()
    elif value is not None and str(value).strip():
        return str(value).strip()
    return None


def _allowed_outcomes(event_type: str) -> set[str]:
    values = VALID_OUTCOMES.get(event_type, ())
    try:
        return {str(value) for value in values}
    except TypeError:
        return set()


def _choose_outcome(event_type: str, candidates: tuple[str, ...]) -> str | None:
    allowed = _allowed_outcomes(event_type)
    return next((candidate for candidate in candidates if candidate in allowed), None)


def _scale_location(value: Any) -> dict[str, float] | None:
    """Scale StatsBomb's 120x80 pitch coordinates to PitchIQ's 105x68 pitch."""
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    try:
        x = float(value[0])
        y = float(value[1])
    except (TypeError, ValueError):
        return None
    if not (0 <= x <= 120 and 0 <= y <= 80):
        return None
    return {"x": round(x * 105 / 120, 4), "y": round(y * 68 / 80, 4)}


def _event_type_and_outcome(raw: dict[str, Any]) -> tuple[str, str] | None:
    """Translate only event/outcome combinations PitchIQ can represent honestly."""
    type_name = _name(raw.get("type")) or ""
    details: dict[str, Any] = {}
    candidate_type = ""
    outcome_name: str | None = None

    if type_name == "Pass":
        candidate_type = "pass"
        details = raw.get("pass") if isinstance(raw.get("pass"), dict) else {}
        outcome_name = _name(details.get("outcome"))
        # StatsBomb leaves outcome null for a completed pass. A named pass outcome
        # indicates a failed/non-completed pass (e.g. incomplete, out, offside).
        candidates = ("incomplete",) if outcome_name else ("complete",)
    elif type_name == "Shot":
        candidate_type = "shot"
        details = raw.get("shot") if isinstance(raw.get("shot"), dict) else {}
        outcome_name = _name(details.get("outcome"))
        shot = (outcome_name or "").casefold()
        if shot == "goal":
            candidates = ("goal",)
        elif shot in {"saved", "saved to post", "saved off target", "saved to post"}:
            candidates = ("saved",)
        elif shot in {"off t", "wayward"}:
            candidates = ("off_target",)
        elif shot in {"blocked", "post"}:
            # Keep these only if the active PitchIQ schema has a distinct matching
            # category; never mislabel a blocked shot or a shot off the woodwork.
            candidates = ("blocked",) if shot == "blocked" else ("woodwork", "post")
        elif shot in {"on target", "saved to post"}:
            candidates = ("on_target", "saved")
        else:
            return None
    elif type_name == "Carry":
        candidate_type = "carry"
        candidates = ("successful",)
    elif type_name == "Dribble":
        candidate_type = "carry"
        details = raw.get("dribble") if isinstance(raw.get("dribble"), dict) else {}
        outcome_name = _name(details.get("outcome"))
        status = (outcome_name or "").casefold()
        if not status or status in {"complete", "completed", "success", "successful"}:
            candidates = ("successful",)
        elif status in {"incomplete", "incomplete dribble", "failed", "unsuccessful"}:
            candidates = ("unsuccessful",)
        else:
            return None
    elif type_name == "Interception":
        candidate_type = "interception"
        details = raw.get("interception") if isinstance(raw.get("interception"), dict) else {}
        outcome_name = _name(details.get("outcome"))
        status = (outcome_name or "").casefold()
        if "lost" in status or "fail" in status:
            candidates = ("missed",)
        else:
            # The event itself is recorded as an interception. If the source has no
            # explicit failed/lost outcome, PitchIQ represents it as won.
            candidates = ("won",)
    elif type_name == "Ball Recovery":
        candidate_type = "recovery"
        details = raw.get("ball_recovery") if isinstance(raw.get("ball_recovery"), dict) else {}
        if details.get("recovery_failure") is True:
            return None
        candidates = ("secured",)
    elif type_name == "Clearance":
        candidate_type = "clearance"
        candidates = ("cleared",)
    elif type_name == "Pressure":
        candidate_type = "pressure"
        candidates = ("applied",)
    elif type_name in {"Foul Committed", "Foul Won"}:
        candidate_type = "foul"
        candidates = ("drawn",) if type_name == "Foul Won" else ("committed",)
    elif type_name == "Tackle":
        candidate_type = "tackle"
        details = raw.get("tackle") if isinstance(raw.get("tackle"), dict) else {}
        outcome_name = _name(details.get("outcome")) or _name(raw.get("outcome"))
        status = (outcome_name or "").casefold()
        if "won" in status or "success" in status:
            candidates = ("won",)
        elif "lost" in status or "fail" in status:
            candidates = ("lost",)
        else:
            return None
    elif type_name == "Duel":
        details = raw.get("duel") if isinstance(raw.get("duel"), dict) else {}
        duel_subtype = _name(details.get("type")) or ""
        outcome_name = _name(details.get("outcome"))
        status = (outcome_name or "").casefold()
        if duel_subtype.casefold() == "tackle" and "tackle" in VALID_TYPES:
            candidate_type = "tackle"
        else:
            candidate_type = "duel"
        if "won" in status or "success" in status:
            candidates = ("won",)
        elif "lost" in status or "fail" in status:
            candidates = ("lost",)
        else:
            return None
    else:
        # Do not shoehorn unsupported source events (e.g. goalkeeper actions,
        # substitutions, ball receipts) into unrelated PitchIQ categories.
        return None

    if candidate_type not in VALID_TYPES:
        return None
    outcome = _choose_outcome(candidate_type, candidates)
    if outcome is None:
        return None
    return candidate_type, outcome


def _raw_event_to_pitchiq(raw: dict[str, Any], row_number: int) -> dict[str, Any] | None:
    mapped = _event_type_and_outcome(raw)
    if mapped is None:
        return None
    event_type, outcome = mapped

    team = _name(raw.get("team"))
    minute = raw.get("minute")
    period = raw.get("period")
    if not team or minute is None or period is None:
        return None

    try:
        minute_int = int(minute)
        period_int = int(period)
    except (TypeError, ValueError):
        return None
    if minute_int < 0 or period_int not in {1, 2, 3, 4}:
        return None

    details_key = {
        "pass": "pass",
        "shot": "shot",
        "carry": "carry",
        "interception": "interception",
        "recovery": "ball_recovery",
        "clearance": "clearance",
        "tackle": "tackle",
        "duel": "duel",
        "foul": "foul_committed",
        "pressure": "pressure",
    }.get(event_type)
    details = raw.get(details_key) if details_key else None
    details = details if isinstance(details, dict) else {}
    end_value = details.get("end_location")
    end_location = _scale_location(end_value)
    location = _scale_location(raw.get("location"))

    source_id = raw.get("id")
    possession_id = raw.get("possession")
    player_name = _name(raw.get("player"))

    record: dict[str, Any] = {
        "id": str(source_id) if source_id is not None else None,
        "minute": minute_int,
        "period": period_int,
        "team": team,
        "player": player_name or "Not supplied",
        "type": event_type,
        "outcome": outcome,
        "source_timestamp": raw.get("timestamp"),
        "source_timestamp_seconds": _timestamp_seconds(raw.get("timestamp")),
    }
    if possession_id is not None:
        record["possession_id"] = str(possession_id)
    if location is not None:
        record["location"] = location
    if end_location is not None:
        record["end_location"] = end_location
    # StatsBomb's under_pressure is boolean, not the low/medium/high intensity
    # scale PitchIQ uses. It is deliberately not converted into a guessed level.
    return record




def _timestamp_seconds(value: Any) -> float | None:
    """Convert a StatsBomb period timestamp HH:MM:SS[.mmm] to seconds."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    parts = text.split(":")
    if len(parts) != 3:
        return None
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
    except (TypeError, ValueError):
        return None
    if hours < 0 or not 0 <= minutes < 60 or not 0 <= seconds < 60:
        return None
    return hours * 3600.0 + minutes * 60.0 + seconds


def _timeline_explanation(raw: dict[str, Any]) -> str:
    """Describe only the recorded event and outcome; avoid tactical speculation."""
    type_name = _name(raw.get("type")) or "Unknown event"
    details_key = {
        "Pass": "pass", "Shot": "shot", "Carry": "carry", "Dribble": "dribble",
        "Duel": "duel", "Ball Recovery": "ball_recovery", "Interception": "interception",
        "Clearance": "clearance", "Pressure": "pressure", "Tackle": "tackle",
        "Block": "block", "Goal Keeper": "goalkeeper", "Foul Committed": "foul_committed",
        "Foul Won": "foul_won", "Ball Receipt*": "ball_receipt", "Dispossessed": "dispossessed",
        "Miscontrol": "miscontrol", "Dribbled Past": "dribbled_past", "50/50": "50_50",
        "Offside": "offside", "Substitution": "substitution", "Own Goal For": "own_goal_for",
        "Own Goal Against": "own_goal_against", "Bad Behaviour": "bad_behaviour",
        "Injury Stoppage": "injury_stoppage", "Referee Ball-Drop": "referee_ball_drop",
        "Half End": "half_end", "Half Start": "half_start", "Starting XI": "starting_xi",
        "Player Off": "player_off", "Player On": "player_on", "Shield": "shield",
    }.get(type_name)
    raw_details = raw.get(details_key) if details_key else None
    details = raw_details if isinstance(raw_details, dict) else {}
    outcome = _name(details.get("outcome")) or _name(raw.get("outcome"))
    recipient = _name(details.get("recipient")) if type_name == "Pass" else None

    if type_name == "Pass":
        if not outcome:
            phrase = "completed a pass"
        else:
            phrase = f"attempted a pass; recorded outcome: {outcome}"
        if recipient:
            phrase += f" to {recipient}"
    elif type_name == "Shot":
        lower = (outcome or "").casefold()
        if lower == "goal":
            phrase = "scored a goal"
        elif lower in {"saved", "saved to post", "saved off target"}:
            phrase = "took a shot that was saved"
        elif lower in {"off t", "wayward", "off target"}:
            phrase = "took a shot that went off target"
        elif lower == "blocked":
            phrase = "took a shot that was blocked"
        elif lower == "post":
            phrase = "took a shot recorded as hitting the post"
        elif outcome:
            phrase = f"attempted a shot; recorded outcome: {outcome}"
        else:
            phrase = "attempted a shot; outcome not supplied"
    elif type_name == "Carry":
        phrase = "carried the ball"
    elif type_name == "Ball Receipt*":
        phrase = "recorded a ball receipt" + (f"; outcome: {outcome}" if outcome else "")
    elif type_name == "Pressure":
        phrase = "applied pressure"
    elif type_name == "Ball Recovery":
        phrase = "recorded a ball recovery"
    elif type_name == "Interception":
        phrase = "recorded an interception" + (f"; outcome: {outcome}" if outcome else "")
    elif type_name == "Duel":
        subtype = _name(details.get("type"))
        phrase = "contested a duel" + (f" ({subtype})" if subtype else "")
        if outcome:
            phrase += f"; recorded outcome: {outcome}"
    elif type_name == "Goal Keeper":
        action = _name(details.get("type"))
        phrase = "performed a recorded goalkeeper action" + (f": {action}" if action else "")
        if outcome:
            phrase += f"; outcome: {outcome}"
    elif type_name == "Foul Committed":
        phrase = "was recorded for a foul"
    elif type_name == "Foul Won":
        phrase = "won a foul"
    elif type_name in {"Own Goal For", "Own Goal Against"}:
        phrase = "recorded an own-goal event"
    elif type_name == "Substitution":
        replacement = _name(details.get("replacement"))
        phrase = "a substitution was recorded" + (f"; replacement: {replacement}" if replacement else "")
    else:
        phrase = f"recorded {type_name.casefold()}"
        if outcome:
            phrase += f"; outcome: {outcome}"

    player = _name(raw.get("player"))
    if player:
        return f"{player} {phrase}."
    return phrase[:1].upper() + phrase[1:] + "."


def _build_event_timeline(
    raw_events: list[Any], source_to_pitchiq_ids: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Build a timestamped timeline for all source events, including unsupported analysis events."""
    mapped = source_to_pitchiq_ids or {}
    timeline: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_events):
        if not isinstance(raw, dict):
            continue
        type_name = _name(raw.get("type")) or "Unknown event"
        team = _name(raw.get("team"))
        player = _name(raw.get("player"))
        source_id = raw.get("id")
        source_id_text = str(source_id) if source_id is not None else None
        raw_minute = raw.get("minute")
        raw_period = raw.get("period")
        try:
            minute = int(raw_minute) if raw_minute is not None else None
        except (TypeError, ValueError):
            minute = None
        try:
            period = int(raw_period) if raw_period is not None else None
        except (TypeError, ValueError):
            period = None
        details_key = {
            "Pass": "pass", "Shot": "shot", "Carry": "carry", "Dribble": "dribble",
            "Duel": "duel", "Ball Recovery": "ball_recovery", "Interception": "interception",
            "Clearance": "clearance", "Pressure": "pressure", "Tackle": "tackle",
            "Block": "block", "Goal Keeper": "goalkeeper", "Foul Committed": "foul_committed",
            "Foul Won": "foul_won", "Ball Receipt*": "ball_receipt", "Dispossessed": "dispossessed",
            "Miscontrol": "miscontrol", "Dribbled Past": "dribbled_past", "50/50": "50_50",
        }.get(type_name)
        raw_details = raw.get(details_key) if details_key else None
        details = raw_details if isinstance(raw_details, dict) else {}
        outcome = _name(details.get("outcome")) or _name(raw.get("outcome"))
        timestamp = raw.get("timestamp") if isinstance(raw.get("timestamp"), str) else None
        timeline.append({
            "source_order": index,
            "source_event_id": source_id_text,
            "pitchiq_event_id": mapped.get(source_id_text) if source_id_text is not None else None,
            "minute": minute,
            "period": period,
            "timestamp": timestamp,
            "timestamp_seconds": _timestamp_seconds(timestamp),
            "team": team,
            "player": player,
            "event_type": type_name,
            "outcome": outcome,
            "explanation": _timeline_explanation(raw),
        })
    return timeline


@lru_cache(maxsize=1)
def _cached_competitions() -> tuple[dict[str, Any], ...]:
    payload = _fetch_json("competitions.json")
    if not isinstance(payload, list):
        raise StatsBombDataError("The StatsBomb competitions file has an unexpected structure.")
    rows: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict) or row.get("competition_id") is None or row.get("season_id") is None:
            continue
        rows.append({
            "competition_id": int(row["competition_id"]),
            "season_id": int(row["season_id"]),
            "competition_name": str(row.get("competition_name") or "Unknown competition"),
            "season_name": str(row.get("season_name") or "Unknown season"),
            "country_name": str(row.get("country_name") or "International"),
            "competition_gender": str(row.get("competition_gender") or "Not specified"),
            "competition_youth": bool(row.get("competition_youth", False)),
            "competition_international": bool(row.get("competition_international", False)),
        })
    rows.sort(key=lambda r: (r["competition_name"].casefold(), r["season_name"].casefold()))
    return tuple(rows)


def list_competitions(refresh: bool = False) -> list[dict[str, Any]]:
    """List published competition/season pairs, not a claim of live coverage."""
    if refresh:
        _cached_competitions.cache_clear()
        _cached_matches.cache_clear()
    return deepcopy(list(_cached_competitions()))


@lru_cache(maxsize=48)
def _cached_matches(competition_id: str, season_id: str) -> tuple[dict[str, Any], ...]:
    payload = _fetch_json(f"matches/{competition_id}/{season_id}.json")
    if not isinstance(payload, list):
        raise StatsBombDataError("The StatsBomb matches file has an unexpected structure.")
    rows: list[dict[str, Any]] = []
    for row in payload:
        if not isinstance(row, dict) or row.get("match_id") is None:
            continue
        home_obj = row.get("home_team")
        away_obj = row.get("away_team")
        rows.append({
            "match_id": int(row["match_id"]),
            "match_date": str(row.get("match_date") or "Date not supplied"),
            "kick_off": str(row.get("kick_off") or "Time not supplied"),
            "home_team": _name(home_obj, "home_team_name") or "Home team not supplied",
            "away_team": _name(away_obj, "away_team_name") or "Away team not supplied",
            "home_score": row.get("home_score"),
            "away_score": row.get("away_score"),
            "competition_stage": _name(row.get("competition_stage")) or "",
            "stadium": _name(row.get("stadium")) or "",
            "raw_match": deepcopy(row),
        })
    rows.sort(key=lambda r: (r["match_date"], r["home_team"].casefold(), r["away_team"].casefold()))
    return tuple(rows)


def list_matches(competition_id: Any, season_id: Any, refresh: bool = False) -> list[dict[str, Any]]:
    """List matches for a selected competition and season."""
    comp = _numeric_id(competition_id, "competition_id")
    season = _numeric_id(season_id, "season_id")
    if refresh:
        _cached_matches.cache_clear()
    return deepcopy(list(_cached_matches(comp, season)))


def clear_cache() -> None:
    """Clear competition and match metadata cached in this process."""
    _cached_competitions.cache_clear()
    _cached_matches.cache_clear()


def import_statsbomb_match(match_id: Any, competition_id: Any, season_id: Any) -> dict[str, Any]:
    """Download a selected match's event log and normalize it for PitchIQ."""
    selected_id = _numeric_id(match_id, "match_id")
    comp_id = _numeric_id(competition_id, "competition_id")
    season = _numeric_id(season_id, "season_id")

    matches = list_matches(comp_id, season)
    selected = next((row for row in matches if str(row["match_id"]) == selected_id), None)
    if selected is None:
        raise StatsBombDataError("That match ID was not found in the selected StatsBomb competition/season.")

    raw_events = _fetch_json(f"events/{selected_id}.json")
    if not isinstance(raw_events, list):
        raise StatsBombDataError("The StatsBomb event file has an unexpected structure.")
    if not raw_events:
        raise StatsBombDataError("StatsBomb returned an empty event log for this match.")

    converted: list[dict[str, Any]] = []
    unsupported_types: dict[str, int] = {}
    for index, raw in enumerate(raw_events, start=1):
        if not isinstance(raw, dict):
            unsupported_types["non-object event"] = unsupported_types.get("non-object event", 0) + 1
            continue
        converted_row = _raw_event_to_pitchiq(raw, index)
        if converted_row is None:
            label = _name(raw.get("type")) or "Unknown event"
            unsupported_types[label] = unsupported_types.get(label, 0) + 1
            continue
        converted.append(converted_row)

    if not converted:
        raise StatsBombDataError(
            "This match contains no events that the current PitchIQ schema can analyse. "
            "No unsupported event types or outcomes were relabelled to force an import."
        )

    home = selected["home_team"]
    away = selected["away_team"]
    present_teams = {row["team"] for row in converted}
    if home not in present_teams or away not in present_teams:
        raise StatsBombDataError(
            "The supported event subset does not contain events for both teams, so PitchIQ cannot safely analyse this match."
        )

    payload = {
        "match_id": f"statsbomb-{selected_id}",
        "home_team": home,
        "away_team": away,
        "events": converted,
    }
    match = parse_uploaded_match(
        f"statsbomb-{selected_id}.json",
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )

    competition_entry = next((
        row for row in list_competitions()
        if row["competition_id"] == int(comp_id) and row["season_id"] == int(season)
    ), None)
    competition_name = competition_entry["competition_name"] if competition_entry else "StatsBomb Open Data"
    season_name = competition_entry["season_name"] if competition_entry else "Unknown season"
    skipped_count = len(raw_events) - len(converted)
    if skipped_count:
        top_skipped = sorted(unsupported_types.items(), key=lambda item: (-item[1], item[0]))[:8]
        summary = ", ".join(f"{name}: {count}" for name, count in top_skipped)
        match["_pitchiq_import"]["warnings"].append(
            f"PitchIQ imported {len(converted)} of {len(raw_events)} StatsBomb source events. "
            f"{skipped_count} event(s) were omitted because their type/outcome is unsupported or insufficiently specified. "
            f"Most common omitted types: {summary}."
        )
    match["_pitchiq_import"].update({
        "source_provider": "StatsBomb Open Data",
        "source_repository": REPOSITORY_URL,
        "source_event_url": f"{REPOSITORY_URL}/blob/master/data/events/{selected_id}.json",
        "source_matches_url": f"{REPOSITORY_URL}/blob/master/data/matches/{comp_id}/{season}.json",
        "source_attribution": "Credit StatsBomb and use the official StatsBomb logo when publishing or sharing analysis.",
        "source_media_pack_url": MEDIA_PACK_URL,
        "statsbomb_match_id": int(selected_id),
        "competition": competition_name,
        "season": season_name,
        "match_date": selected["match_date"],
        "kick_off": selected["kick_off"],
        "source_home_score": selected["home_score"],
        "source_away_score": selected["away_score"],
        "source_event_count": len(raw_events),
        "imported_event_count": len(converted),
        "skipped_event_count": skipped_count,
        "warnings": list(dict.fromkeys(match["_pitchiq_import"]["warnings"])),
    })

    # Link supported source IDs to PitchIQ's internal evidence IDs while retaining
    # the source timestamps on imported events. Unsupported events remain in the
    # playback timeline, but are marked as timeline-only.
    source_to_pitchiq_ids: dict[str, Any] = {}
    for source_row, imported_event in zip(converted, match.get("events", [])):
        source_id = source_row.get("id")
        if source_id is None:
            continue
        source_id_text = str(source_id)
        source_to_pitchiq_ids[source_id_text] = imported_event.get("id")
        imported_event["source_timestamp"] = source_row.get("source_timestamp")
        imported_event["source_timestamp_seconds"] = source_row.get("source_timestamp_seconds")

    event_timeline = _build_event_timeline(raw_events, source_to_pitchiq_ids)
    match["_pitchiq_import"].update({
        "event_timeline": event_timeline,
        "timeline_event_count": len(event_timeline),
        "timeline_timestamped_count": sum(row.get("timestamp_seconds") is not None for row in event_timeline),
        "timeline_missing_timestamp_count": sum(row.get("timestamp_seconds") is None for row in event_timeline),
    })
    return match


class StatsBombOpenDataAgent:
    """Small deterministic discovery/import agent; no LLM or API key required."""

    name = "StatsBomb Open Data Discovery Agent"

    def list_competitions(self, refresh: bool = False) -> list[dict[str, Any]]:
        return list_competitions(refresh=refresh)

    def list_matches(self, competition_id: Any, season_id: Any, refresh: bool = False) -> list[dict[str, Any]]:
        return list_matches(competition_id, season_id, refresh=refresh)

    def import_match(self, match_id: Any, competition_id: Any, season_id: Any) -> dict[str, Any]:
        return import_statsbomb_match(match_id, competition_id, season_id)



def find_statsbomb_attacking_sequences(match: dict[str, Any], max_minutes: int = 3) -> list[dict[str, Any]]:
    """Find completed passes preceding a shot within one recorded possession.

    Unlike PitchIQ's original synthetic-demo rule, this StatsBomb-specific rule
    allows carries and defensive events to occur between passes. It only reports
    the selected completed passes and final shot as evidence; it does not claim
    that the passes were consecutive actions.
    """
    raw_events = match.get("events", []) if isinstance(match, dict) else []
    indexed: list[tuple[int, dict[str, Any]]] = []
    for source_index, event in enumerate(raw_events):
        if not isinstance(event, dict):
            continue
        if not isinstance(event.get("minute"), int) or not isinstance(event.get("period"), int):
            continue
        indexed.append((source_index, event))

    def sort_key(item: tuple[int, dict[str, Any]]) -> tuple[int, int, int]:
        source_index, event = item
        event_id = event.get("id")
        stable_id = event_id if type(event_id) is int else source_index
        return (event["period"], event["minute"], stable_id)

    indexed.sort(key=sort_key)
    timeline = [event for _, event in indexed]
    sequences: list[dict[str, Any]] = []

    for finish_index, finish_event in enumerate(timeline):
        if finish_event.get("type") not in {"shot", "goal"}:
            continue
        team = finish_event.get("team")
        possession_id = finish_event.get("possession_id")
        if not isinstance(team, str) or not team.strip() or not possession_id:
            continue

        finish_period = finish_event["period"]
        finish_minute = finish_event["minute"]
        passes: list[dict[str, Any]] = []

        for previous in reversed(timeline[:finish_index]):
            if previous.get("period") != finish_period:
                break
            if finish_minute - previous.get("minute", finish_minute) > max_minutes:
                break
            previous_possession = previous.get("possession_id")
            if not previous_possession or previous_possession != possession_id:
                # Do not bridge a change of possession or missing possession evidence.
                break

            previous_team = previous.get("team")
            previous_type = previous.get("type")
            previous_outcome = previous.get("outcome")

            # A previous finish closes the earlier build-up within this possession.
            if previous_team == team and previous_type in {"shot", "goal"}:
                break
            if previous_team == team and previous_type == "pass":
                if previous_outcome == "complete":
                    passes.append(previous)
                else:
                    # Do not use passes from before a failed pass as one build-up.
                    break
            elif (
                previous_team == team
                and previous_type in {"tackle", "duel"}
                and previous_outcome in {"lost", "missed"}
            ):
                break
            elif previous_team == team and previous_type == "foul":
                break
            # Carries and opponent defensive actions can occur within a possession.
            # They are deliberately not labelled as passes or included in evidence.

        passes.reverse()
        if len(passes) < 2:
            continue

        evidence_events = passes + [finish_event]
        sequences.append({
            "team": team,
            "start_minute": passes[0]["minute"],
            "end_minute": finish_minute,
            "passes": len(passes),
            "finish": (
                "goal"
                if finish_event.get("type") == "goal"
                or finish_event.get("outcome") in {"goal", "scored"}
                else "shot"
            ),
            "event_ids": [item["id"] for item in evidence_events],
            "evidence_basis": "same_possession",
        })

    return sequences


def analyze_statsbomb_match(match: dict[str, Any]) -> dict[str, Any]:
    """Run normal PitchIQ statistics and the StatsBomb-aware sequence rule."""
    report = analyze_match(match)
    report["attacking_sequences"] = find_statsbomb_attacking_sequences(match)
    return report
