
"""Generate personalized, evidence-backed football insights."""

AUDIENCE_MODES = {"fan", "analyst"}


def describe_finish(event):
    """Describe the outcome recorded in a shot or goal event."""
    player = event["player"]
    outcome = event["outcome"]

    if event["type"] == "goal" or outcome in {"goal", "scored"}:
        return "a goal", f"{player} scored a goal"

    if outcome == "saved":
        return "a saved shot", f"{player} had a shot saved"

    if outcome == "off_target":
        return "an off-target shot", f"{player} sent a shot off target"

    if outcome == "on_target":
        return "an on-target shot", f"{player} put a shot on target"

    return "a shot", f"{player} attempted a shot"


def generate_insights(match, report, audience="fan"):
    """
    Convert detected attacking sequences into personalized insights.

    Every insight contains supporting event IDs and a limitation.
    This is deterministic narrative generation, not an AI model.
    """
    if audience not in AUDIENCE_MODES:
        raise ValueError(
            f"Unsupported audience: {audience}. "
            f"Choose one of {sorted(AUDIENCE_MODES)}."
        )

    events_by_id = {
        event["id"]: event
        for event in match["events"]
    }

    insights = []

    for number, sequence in enumerate(
        report["attacking_sequences"], start=1
    ):
        evidence_ids = sequence["event_ids"]

        if not evidence_ids:
            raise ValueError("An attacking sequence has no evidence.")

        if any(event_id not in events_by_id for event_id in evidence_ids):
            raise ValueError(
                "An attacking sequence references an unknown event."
            )

        start_event = events_by_id[evidence_ids[0]]
        finish_event = events_by_id[evidence_ids[-1]]

        team = sequence["team"]
        passes = sequence["passes"]
        start_minute = sequence["start_minute"]
        end_minute = sequence["end_minute"]

        finish_label, finish_phrase = describe_finish(finish_event)

        same_possession_evidence = sequence.get("evidence_basis") == "same_possession"
        title = (
            f"{team}'s {passes}-pass possession ends with {finish_label}"
            if same_possession_evidence
            else f"{team}'s {passes}-pass attack ends with {finish_label}"
        )

        if audience == "fan":
            if same_possession_evidence:
                summary = (
                    f"At minute {end_minute}, {team} recorded {passes} completed "
                    f"passes in the same possession before {finish_phrase}."
                )
                why_it_matters = (
                    "This highlights recorded passing activity before a shot within "
                    "one possession. It does not establish that all intervening actions "
                    "were passes or that the passes created a high-quality chance."
                )
            else:
                summary = (
                    f"At minute {end_minute}, {team} connected "
                    f"{passes} completed passes before {finish_phrase}."
                )
                why_it_matters = (
                    "This highlights how a short passing sequence led "
                    "to a shot, giving fans a concrete attacking moment "
                    "to follow beyond the scoreline."
                )
        else:
            if same_possession_evidence:
                summary = (
                    f"{team} recorded {passes} completed passes in the same "
                    f"possession from minute {start_minute} to {end_minute}, "
                    f"before {finish_phrase} (recorded outcome: {finish_event['outcome']})."
                )
                why_it_matters = (
                    "The source records these completed passes and the finish in one "
                    "possession. It does not establish that the passes were consecutive "
                    "actions, that they broke a defensive line, or that the shot was high quality."
                )
            else:
                summary = (
                    f"{team} completed {passes} consecutive passes from "
                    f"minute {start_minute} to {end_minute}; the sequence "
                    f"culminated when {finish_phrase} "
                    f"(recorded outcome: {finish_event['outcome']})."
                )
                why_it_matters = (
                    "The event order supports a build-up-to-shot description. "
                    "The reliability of location and pressure context depends on "
                    "the supplied source data. Without a validated shot-quality "
                    "model, this evidence does not prove that the passes broke a "
                    "defensive line or created a high-quality chance."
                )

        insights.append({
            "id": f"attack-{number:03d}",
            "category": "attacking_sequence",
            "audience": audience,
            "team": team,
            "minute": end_minute,
            "title": title,
            "summary": summary,
            "why_it_matters": why_it_matters,
            "evidence_event_ids": list(evidence_ids),

            "limitation": (
                "PitchIQ does not independently validate tracking coordinates or "
                "pressure labels. The current rules do not calculate validated "
                "shot quality or prove tactical causation."
            ),

        })

    return insights
