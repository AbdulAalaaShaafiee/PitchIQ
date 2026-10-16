
"""Local multi-agent orchestration for PitchIQ.

These are deterministic specialist agents, not LLM-powered agents yet.
"""

from pitchiq.insights import AUDIENCE_MODES


def _normalise_ids(value):
    """Return valid event IDs as a tuple, or None for invalid input."""
    if not isinstance(value, list) or not value:
        return None

    if any(type(event_id) not in (int, str) for event_id in value):
        return None

    return tuple(value)


def _finish_description(event):
    """Independently describe the outcome recorded in a finish event."""
    player = event.get("player")
    outcome = event.get("outcome")

    if event.get("type") == "goal" or outcome in {"goal", "scored"}:
        return "a goal", f"{player} scored a goal"

    if outcome == "saved":
        return "a saved shot", f"{player} had a shot saved"

    if outcome == "off_target":
        return "an off-target shot", f"{player} sent a shot off target"

    if outcome == "on_target":
        return "an on-target shot", f"{player} put a shot on target"

    return "a shot", f"{player} attempted a shot"


def _sequence_is_consistent(sequence, events_by_id):
    """Check that a reported attack agrees with its underlying event records."""
    if not isinstance(sequence, dict):
        return False

    event_ids = _normalise_ids(sequence.get("event_ids"))
    if event_ids is None or len(set(event_ids)) != len(event_ids):
        return False

    if any(event_id not in events_by_id for event_id in event_ids):
        return False

    events = [events_by_id[event_id] for event_id in event_ids]

    team = sequence.get("team")
    passes = sequence.get("passes")

    if not isinstance(team, str) or not team.strip():
        return False

    if type(passes) is not int or passes < 1:
        return False

    # Each sequence must contain its completed passes followed by one finish.
    if len(events) != passes + 1:
        return False

    for event in events[:-1]:
        if event.get("type") != "pass" or event.get("outcome") != "complete":
            return False

    finish_event = events[-1]
    finish_outcomes = {"goal", "scored", "saved", "off_target", "on_target"}

    if (
        finish_event.get("type") not in {"shot", "goal"}
        and finish_event.get("outcome") not in finish_outcomes
    ):
        return False

    # Every event must belong to the reported team and possession.
    if any(event.get("team") != team for event in events):
        return False

    possession_ids = [event.get("possession_id") for event in events]
    if not possession_ids[0] or any(
        possession_id != possession_ids[0]
        for possession_id in possession_ids
    ):
        return False

    # Verify actual chronology. Event IDs do not necessarily indicate order.
    timeline = [
        (event.get("period", 1), event.get("minute"))
        for event in events
    ]

    if any(
        type(period) is not int or type(minute) is not int
        for period, minute in timeline
    ):
        return False

    if timeline != sorted(timeline):
        return False

    # Verify the reported start and finish minutes.
    if sequence.get("start_minute") != events[0].get("minute"):
        return False

    if sequence.get("end_minute") != finish_event.get("minute"):
        return False

    return True


def _expected_narrative(sequence, finish_event, audience):
    """Build the exact expected narrative from recorded event facts."""
    team = sequence["team"]
    passes = sequence["passes"]
    start_minute = sequence["start_minute"]
    end_minute = sequence["end_minute"]
    outcome = finish_event["outcome"]

    finish_label, finish_phrase = _finish_description(finish_event)

    title = (
        f"{team}'s {passes}-pass attack ends with {finish_label}"
    )

    if audience == "fan":
        summary = (
            f"At minute {end_minute}, {team} connected "
            f"{passes} completed passes before {finish_phrase}."
        )

        why_it_matters = (
            "This highlights how a short passing sequence led "
            "to a shot, giving fans a concrete attacking moment "
            "to follow beyond the scoreline."
        )

    elif audience == "analyst":
        summary = (
            f"{team} completed {passes} consecutive passes from "
            f"minute {start_minute} to {end_minute}; the sequence "
            f"culminated when {finish_phrase} "
            f"(recorded outcome: {outcome})."
        )

        why_it_matters = (
            "The event order supports a build-up-to-shot description. "
            "The dataset contains synthetic locations and pressure labels, "
            "but these are not calibrated tracking measurements. Without "
            "a validated shot-quality model, this evidence does not prove "
            "that the passes broke a defensive line or created a "
            "high-quality chance."
        )

    else:
        return None

    limitation = (
        "All event coordinates and pressure labels are synthetic estimates, "
        "not tracking measurements. The current rules do not calculate "
        "validated shot quality or prove tactical causation."
    )

    return {
        "title": title,
        "summary": summary,
        "why_it_matters": why_it_matters,
        "limitation": limitation,
    }


class EventAnalysisAgent:
    """Runs the existing match-analysis engine."""

    name = "Event Analysis Agent"

    def run(self, match, analysis_function):
        return analysis_function(match)


class StorytellingAgent:
    """Creates audience-specific insights from the analysis."""

    name = "Storytelling Agent"

    def run(self, match, report, audience):
        from pitchiq.insights import generate_insights

        return generate_insights(match, report, audience=audience)


class EvidenceVerificationAgent:
    """Checks evidence references, event integrity, and narrative consistency."""

    name = "Evidence Verification Agent"

    def run(self, match, report, insights, audience):
        raw_events = match.get("events", []) if isinstance(match, dict) else []
        raw_sequences = (
            report.get("attacking_sequences", [])
            if isinstance(report, dict)
            else []
        )

        events_are_valid = (
            isinstance(raw_events, list)
            and all(
                isinstance(event, dict)
                and type(event.get("id")) in (int, str)
                for event in raw_events
            )
        )

        sequences_are_valid = (
            isinstance(raw_sequences, list)
            and all(isinstance(sequence, dict) for sequence in raw_sequences)
        )

        insights_are_valid = (
            isinstance(insights, list)
            and all(isinstance(insight, dict) for insight in insights)
        )

        events = raw_events if isinstance(raw_events, list) else []
        sequences = (
            raw_sequences
            if isinstance(raw_sequences, list)
            else []
        )
        insights_list = (
            insights if isinstance(insights, list) else []
        )

        # Invalid event records cannot safely be indexed by ID.
        events_by_id = {}
        for event in events:
            if (
                isinstance(event, dict)
                and type(event.get("id")) in (int, str)
            ):
                events_by_id[event["id"]] = event

        sequences_by_ids = {}
        for sequence in sequences:
            if not isinstance(sequence, dict):
                continue

            sequence_ids = _normalise_ids(sequence.get("event_ids"))
            if sequence_ids is not None:
                sequences_by_ids[sequence_ids] = sequence

        def get_sequence(insight):
            evidence_ids = _normalise_ids(
                insight.get("evidence_event_ids")
            )
            if evidence_ids is None:
                return None

            return sequences_by_ids.get(evidence_ids)

        def all_evidence_exists():
            if not insights_are_valid:
                return False

            return all(
                (ids := _normalise_ids(
                    insight.get("evidence_event_ids")
                )) is not None
                and all(event_id in events_by_id for event_id in ids)
                for insight in insights_list
            )

        def every_insight_maps_to_consistent_sequence():
            if not insights_are_valid or not sequences_are_valid:
                return False

            for insight in insights_list:
                sequence = get_sequence(insight)

                if sequence is None:
                    return False

                if not _sequence_is_consistent(sequence, events_by_id):
                    return False

            return True

        def every_sequence_has_exactly_one_insight():
            if not insights_are_valid or not sequences_are_valid:
                return False

            sequence_keys = [
                _normalise_ids(sequence.get("event_ids"))
                for sequence in sequences
            ]
            insight_keys = [
                _normalise_ids(insight.get("evidence_event_ids"))
                for insight in insights_list
            ]

            if any(key is None for key in sequence_keys + insight_keys):
                return False

            return (
                len(insight_keys) == len(sequence_keys)
                and len(set(sequence_keys)) == len(sequence_keys)
                and len(set(insight_keys)) == len(insight_keys)
                and set(insight_keys) == set(sequence_keys)
            )

        def metadata_matches_recorded_events():
            if not insights_are_valid:
                return False

            for insight in insights_list:
                sequence = get_sequence(insight)

                if sequence is None:
                    return False

                if not _sequence_is_consistent(sequence, events_by_id):
                    return False

                if (
                    insight.get("team") != sequence.get("team")
                    or insight.get("minute") != sequence.get("end_minute")
                ):
                    return False

            return True

        def audience_matches():
            return (
                audience in AUDIENCE_MODES
                and insights_are_valid
                and all(
                    insight.get("audience") == audience
                    for insight in insights_list
                )
            )

        def narrative_is_complete_and_consistent():
            if not insights_are_valid or audience not in AUDIENCE_MODES:
                return False

            required_fields = (
                "title",
                "summary",
                "why_it_matters",
                "limitation",
            )

            for insight in insights_list:
                if not all(
                    isinstance(insight.get(field), str)
                    and bool(insight[field].strip())
                    for field in required_fields
                ):
                    return False

                if insight.get("category") != "attacking_sequence":
                    return False

                sequence = get_sequence(insight)
                if sequence is None:
                    return False

                ids = _normalise_ids(sequence.get("event_ids"))
                if ids is None or ids[-1] not in events_by_id:
                    return False

                expected = _expected_narrative(
                    sequence,
                    events_by_id[ids[-1]],
                    audience,
                )

                if expected is None:
                    return False

                if any(
                    insight.get(field) != expected[field]
                    for field in required_fields
                ):
                    return False

            return True

        check_results = [
            (
                "All evidence IDs exist in the match events",
                events_are_valid and all_evidence_exists(),
            ),
            (
                "Every insight maps to a detected sequence",
                every_insight_maps_to_consistent_sequence(),
            ),
            (
                "Every sequence has exactly one insight",
                every_sequence_has_exactly_one_insight(),
            ),
            (
                "Team and minute metadata match the sequence",
                metadata_matches_recorded_events(),
            ),
            (
                "Insights use the requested audience mode",
                audience_matches(),
            ),
            (
                "All narrative fields are complete",
                narrative_is_complete_and_consistent(),
            ),
        ]

        checks = [
            {"name": name, "passed": bool(passed)}
            for name, passed in check_results
        ]

        errors = [
            check["name"]
            for check in checks
            if not check["passed"]
        ]

        return {
            "passed": not errors,
            "checks_passed": sum(check["passed"] for check in checks),
            "checks_total": len(checks),
            "checks": checks,
            "errors": errors,
        }


class PitchIQOrchestrator:
    """Coordinates specialist agents through shared workflow state."""

    def __init__(self, analysis_function):
        self.analysis_function = analysis_function
        self.analysis_agent = EventAnalysisAgent()
        self.storytelling_agent = StorytellingAgent()
        self.verification_agent = EvidenceVerificationAgent()

    def run(self, match, audience="fan"):
        shared_state = {
            "match_id": match["match_id"],
            "audience": audience,
            "report": None,
            "insights": None,
            "verification": None,
        }

        steps = []
        handoffs = []

        # Stage 1: analyze the match.
        report = self.analysis_agent.run(match, self.analysis_function)
        shared_state["report"] = report

        steps.append({
            "agent": self.analysis_agent.name,
            "status": "completed",
            "detail": (
                f"{len(match['events'])} synthetic events analyzed; "
                f"{len(report['attacking_sequences'])} "
                "attacking sequences detected."
            ),
        })

        handoffs.append({
            "from": self.analysis_agent.name,
            "to": self.storytelling_agent.name,
            "status": "completed",
            "shared_state_fields": ["report", "audience"],
        })

        # Stage 2: generate a personalized narrative.
        insights = self.storytelling_agent.run(
            match,
            shared_state["report"],
            shared_state["audience"],
        )
        shared_state["insights"] = insights

        steps.append({
            "agent": self.storytelling_agent.name,
            "status": "completed",
            "detail": f"{len(insights)} {audience} insight(s) generated.",
        })

        handoffs.append({
            "from": self.storytelling_agent.name,
            "to": self.verification_agent.name,
            "status": "completed",
            "shared_state_fields": [
                "report.attacking_sequences",
                "insights",
                "audience",
            ],
        })

        # Stage 3: verify the evidence before displaying insights.
        verification = self.verification_agent.run(
            match,
            shared_state["report"],
            shared_state["insights"],
            shared_state["audience"],
        )
        shared_state["verification"] = verification

        steps.append({
            "agent": self.verification_agent.name,
            "status": (
                "passed" if verification["passed"] else "rejected"
            ),
            "detail": (
                f"{verification['checks_passed']}/"
                f"{verification['checks_total']} verification checks passed."
            ),
        })

        return {
            "shared_state": shared_state,
            "steps": steps,
            "handoffs": handoffs,
        }
