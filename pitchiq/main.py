
import argparse
import json
from pathlib import Path

from pitchiq.insights import generate_insights
from pitchiq.agents import PitchIQOrchestrator

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = PROJECT_ROOT / "data" / "events.json"


VALID_TYPES = {
    "pass",
    "shot",
    "goal",
    "tackle",
    "carry",
    "interception",
    "recovery",
    "clearance",
    "foul",
    "pressure",
    "duel",
}

VALID_OUTCOMES = {
    "pass": {"complete", "incomplete"},
    "shot": {"on_target", "off_target", "saved", "goal"},
    "goal": {"scored"},
    "tackle": {"won", "lost"},
    "carry": {"successful", "unsuccessful"},
    "interception": {"won", "missed"},
    "recovery": {"secured", "contested"},
    "clearance": {"cleared", "blocked"},
    "foul": {"committed", "drawn"},
    "pressure": {"applied", "escaped"},
    "duel": {"won", "lost"},
}

VALID_PHASES = {
    "build_up",
    "settled_attack",
    "transition",
    "counterattack",
    "defensive_phase",
    "pressing",
    "recovery",
    "set_piece",
}

VALID_PRESSURE_LEVELS = {"low", "medium", "high"}


def validate_event_context(event):
    """Validate synthetic match context and pitch coordinates."""
    period = event["period"]

    if (
        not isinstance(period, int)
        or isinstance(period, bool)
        or period not in {1, 2}
    ):
        raise ValueError(
            f"Invalid period for event {event['id']}: {period}"
        )

    expected_period = 1 if event["minute"] <= 45 else 2

    if period != expected_period:
        raise ValueError(
            f"Event {event['id']} has a period inconsistent "
            "with its minute."
        )

    possession_id = event["possession_id"]

    if not isinstance(possession_id, str) or not possession_id.strip():
        raise ValueError(
            f"Invalid possession ID for event {event['id']}."
        )

    if event["phase"] not in VALID_PHASES:
        raise ValueError(
            f"Invalid phase for event {event['id']}."
        )

    if event["pressure"] not in VALID_PRESSURE_LEVELS:
        raise ValueError(
            f"Invalid pressure level for event {event['id']}."
        )

    moving_types = {
        "pass",
        "carry",
        "shot",
        "goal",
        "clearance",
    }

    for field in ("location", "end_location"):
        point = event[field]

        if point is None:
            if field == "location" or (
                field == "end_location"
                and event["type"] in moving_types
            ):
                raise ValueError(
                    f"Event {event['id']} requires {field} coordinates."
                )
            continue

        if not isinstance(point, dict) or not {"x", "y"}.issubset(point):
            raise ValueError(
                f"Invalid {field} for event {event['id']}."
            )

        for axis, maximum in (("x", 105), ("y", 68)):
            coordinate = point[axis]

            if (
                isinstance(coordinate, bool)
                or not isinstance(coordinate, (int, float))
                or not 0 <= coordinate <= maximum
            ):
                raise ValueError(
                    f"Invalid {axis} coordinate in {field} "
                    f"for event {event['id']}. "
                    f"Expected a value from 0 to {maximum}."
                )



def load_match():
    """Load and validate the synthetic match dataset."""
    with DATA_FILE.open("r", encoding="utf-8") as file:
        match = json.load(file)

    # These fields belong to the match as a whole.
    required_fields = {
        "match_id",
        "home_team",
        "away_team",
        "events",
    }

    if not isinstance(match, dict):
        raise ValueError("Match data must be a JSON object.")

    if not required_fields.issubset(match):
        raise ValueError("Match is missing required fields.")

    if not isinstance(match["events"], list):
        raise ValueError("Events must be a list.")

    teams = {match["home_team"], match["away_team"]}

    if len(teams) != 2 or not all(
        isinstance(team, str) and team.strip()
        for team in teams
    ):
        raise ValueError("Match must have two distinct team names.")

    seen_ids = set()

    for event in match["events"]:
        # These fields belong to each individual event.
        required_event_fields = {
            "id",
            "minute",
            "team",
            "player",
            "type",
            "outcome",
            "period",
            "possession_id",
            "phase",
            "pressure",
            "location",
            "end_location",
        }

        if not isinstance(event, dict):
            raise ValueError("Every event must be a JSON object.")

        if not required_event_fields.issubset(event):
            raise ValueError("An event is missing required fields.")

        event_id = event["id"]

        if (
            not isinstance(event_id, int)
            or isinstance(event_id, bool)
        ):
            raise ValueError("Event ID must be an integer.")

        if event_id in seen_ids:
            raise ValueError(f"Duplicate event ID: {event_id}")

        seen_ids.add(event_id)

        if event["team"] not in teams:
            raise ValueError(f"Unknown team: {event['team']}")

        if (
            not isinstance(event["player"], str)
            or not event["player"].strip()
        ):
            raise ValueError(
                f"Invalid player name for event {event_id}."
            )

        event_type = event["type"]

        if event_type not in VALID_TYPES:
            raise ValueError(f"Unknown event type: {event_type}")

        if event["outcome"] not in VALID_OUTCOMES[event_type]:
            raise ValueError(
                f"Invalid outcome for event {event_id}"
            )

        minute = event["minute"]

        if (
            not isinstance(minute, int)
            or isinstance(minute, bool)
            or minute < 0
        ):
            raise ValueError(
                "Event minute must be a nonnegative integer."
            )

        # Keep this call INSIDE the for event loop.
        validate_event_context(event)

    return match



def analyze_match(match):
    """Calculate basic team statistics and attacking sequences."""
    home = match["home_team"]
    away = match["away_team"]

    events = sorted(
        match["events"],
        key=lambda event: (event["minute"], event["id"]),
    )

    stats = {
        team: {
            "goals": 0,
            "shots": 0,
            "passes_attempted": 0,
            "passes_completed": 0,
            "tackles_won": 0,
        }
        for team in (home, away)
    }

    for event in events:
        team_stats = stats[event["team"]]
        event_type = event["type"]
        outcome = event["outcome"]

        if event_type == "pass":
            team_stats["passes_attempted"] += 1

            if outcome == "complete":
                team_stats["passes_completed"] += 1

        elif event_type == "shot":
            team_stats["shots"] += 1

            if outcome == "goal":
                team_stats["goals"] += 1

        elif event_type == "goal":
            team_stats["goals"] += 1

        elif event_type == "tackle" and outcome == "won":
            team_stats["tackles_won"] += 1

    for team_stats in stats.values():
        attempted = team_stats["passes_attempted"]
        completed = team_stats["passes_completed"]

        team_stats["pass_accuracy_pct"] = (
            round(completed / attempted * 100, 1)
            if attempted
            else None
        )

    return {
        "match_id": match["match_id"],
        "home_team": home,
        "away_team": away,
        "score": {
            home: stats[home]["goals"],
            away: stats[away]["goals"],
        },
        "stats": stats,
        "attacking_sequences": find_attacking_sequences(events),
    }


def find_attacking_sequences(events):
    """
    Find two or more consecutive completed passes followed by
    a shot or goal for the same team within three minutes.

    This transparent demonstration rule is not a validated
    tactical model.
    """
    sequences = []

    for index, event in enumerate(events):
        if event["type"] not in {"shot", "goal"}:
            continue

        team = event["team"]
        passes = []
        previous_index = index - 1

        while previous_index >= 0:
            previous = events[previous_index]

            if previous["team"] != team:
                break

            if event["minute"] - previous["minute"] > 3:
                break

            if previous["type"] != "pass":
                break

            if previous["outcome"] != "complete":
                break

            passes.append(previous)
            previous_index -= 1

        passes.reverse()

        if len(passes) < 2:
            continue

        sequence_events = passes + [event]

        sequences.append({
            "team": team,
            "start_minute": passes[0]["minute"],
            "end_minute": event["minute"],
            "passes": len(passes),
            "finish": (
    "goal"
    if event["type"] == "goal"
    or event["outcome"] in {"goal", "scored"}
    else "shot"
),
            "event_ids": [
                item["id"] for item in sequence_events
            ],
        })

    return sequences


def print_report(report):
    """Display a readable match report in the terminal."""
    home = report["home_team"]
    away = report["away_team"]

    print("\n" + "=" * 48)
    print("PITCHIQ | SYNTHETIC MATCH INTELLIGENCE")
    print("=" * 48)

    print(f"Match: {home} vs {away}")
    print(
        f"Score: {home} {report['score'][home]} - "
        f"{report['score'][away]} {away}"
    )

    print("\nTEAM STATISTICS")

    for team in (home, away):
        stat = report["stats"][team]
        accuracy = stat["pass_accuracy_pct"]

        accuracy_text = (
            f"{accuracy}%"
            if accuracy is not None
            else "N/A"
        )

        print(f"\n{team}")
        print(f"  Shots: {stat['shots']}")
        print(
            f"  Passes completed: "
            f"{stat['passes_completed']}/"
            f"{stat['passes_attempted']}"
        )
        print(f"  Pass accuracy: {accuracy_text}")
        print(f"  Tackles won: {stat['tackles_won']}")

    print("\nKEY ATTACKING SEQUENCES")

    sequences = report["attacking_sequences"]

    if not sequences:
        print("  No sequences matched the current detection rule.")

    for sequence in sequences:
        print(
            f"  {sequence['team']}, minutes "
            f"{sequence['start_minute']}-"
            f"{sequence['end_minute']}: "
            f"{sequence['passes']} completed passes "
            f"followed by a {sequence['finish']}."
        )

        print(
            f"    Supporting event IDs: "
            f"{sequence['event_ids']}"
        )

    print("\nNote: All match data is synthetic.")
    print("=" * 48)


def print_insights(match, report, audience, insights=None):
    """Display personalized insights with traceable evidence."""
    if insights is None:
        insights = generate_insights(
            match,
            report,
            audience=audience,
        )
    print(f"\nPITCHIQ | {audience.upper()} INSIGHTS")
    print("-" * 48)

    if not insights:
        print("No attacking sequences were detected.")
        return

    for insight in insights:
        print(f"\n{insight['title']}")
        print(f"  {insight['summary']}")
        print(f"  Why it matters: {insight['why_it_matters']}")

        evidence = ", ".join(
            str(event_id)
            for event_id in insight["evidence_event_ids"]
        )

        print(f"  Supporting event IDs: [{evidence}]")

    print("\nDATA LIMITATION")
    print(f"  {insights[0]['limitation']}")


def print_agent_workflow(result):
    """Show agent execution, handoffs, and evidence checks."""
    print("\nPITCHIQ | MULTI-AGENT WORKFLOW")
    print("-" * 48)

    for number, step in enumerate(result["steps"], start=1):
        print(
            f"{number}. {step['agent']} "
            f"[{step['status'].upper()}]"
        )
        print(f"   {step['detail']}")

    print("\nAGENT HANDOFFS")

    for handoff in result["handoffs"]:
        print(
            f"  {handoff['from']} -> {handoff['to']} "
            f"[{handoff['status'].upper()}]"
        )

    verification = result["shared_state"]["verification"]

    status = "PASSED" if verification["passed"] else "FAILED"

    print(
        f"\nEVIDENCE VERIFICATION: {status} "
        f"({verification['checks_passed']}/"
        f"{verification['checks_total']} checks)"
    )

    for check in verification["checks"]:
        check_status = "PASS" if check["passed"] else "FAIL"
        print(f"  [{check_status}] {check['name']}")


def main():
    parser = argparse.ArgumentParser(
        description="PitchIQ football match intelligence"
    )

    parser.add_argument(
        "--audience",
        choices=("fan", "analyst"),
        default="fan",
        help="Choose fan-friendly or analyst-focused insights.",
    )

    args = parser.parse_args()

    try:
        match = load_match()

        orchestrator = PitchIQOrchestrator(analyze_match)
        result = orchestrator.run(match, args.audience)

        report = result["shared_state"]["report"]
        insights = result["shared_state"]["insights"]
        verification = result["shared_state"]["verification"]

        print_report(report)
        print_agent_workflow(result)

        if not verification["passed"]:
            raise ValueError(
                "Evidence verification failed. "
                "Personalized insights have been withheld."
            )

        print_insights(
            match,
            report,
            args.audience,
            insights=insights,
        )

    except (
        OSError,
        json.JSONDecodeError,
        ValueError,
    ) as error:
        raise SystemExit(
            f"PitchIQ could not process the match: {error}"
        )


if __name__ == "__main__":
    main()


