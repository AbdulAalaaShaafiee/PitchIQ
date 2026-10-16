
"""Local multi-agent orchestration for PitchIQ.

These are deterministic specialist agents, not LLM-powered agents yet.
"""

from pitchiq.insights import generate_insights


class EventAnalysisAgent:
    """Runs the existing match-analysis engine."""

    name = "Event Analysis Agent"

    def run(self, match, analysis_function):
        return analysis_function(match)


class StorytellingAgent:
    """Creates audience-specific insights from the analysis."""

    name = "Storytelling Agent"

    def run(self, match, report, audience):
        return generate_insights(
            match,
            report,
            audience=audience,
        )


class EvidenceVerificationAgent:
    """Checks evidence references and insight metadata."""

    name = "Evidence Verification Agent"

    def run(self, match, report, insights, audience):
        events_by_id = {
            event["id"]: event
            for event in match.get("events", [])
        }

        sequences = report.get("attacking_sequences", [])

        sequences_by_ids = {
            tuple(sequence.get("event_ids", [])): sequence
            for sequence in sequences
        }

        def get_sequence(insight):
            evidence_ids = insight.get("evidence_event_ids", [])

            if not isinstance(evidence_ids, list):
                return None

            return sequences_by_ids.get(tuple(evidence_ids))

        all_evidence_exists = all(
            isinstance(insight.get("evidence_event_ids"), list)
            and bool(insight["evidence_event_ids"])
            and all(
                event_id in events_by_id
                for event_id in insight["evidence_event_ids"]
            )
            for insight in insights
        )

        every_insight_maps_to_sequence = all(
            get_sequence(insight) is not None
            for insight in insights
        )

        each_sequence_has_one_insight = (
            len(insights) == len(sequences)
            and len({
                tuple(insight.get("evidence_event_ids", []))
                for insight in insights
                if isinstance(insight.get("evidence_event_ids"), list)
            }) == len(insights)
            and {
                tuple(insight.get("evidence_event_ids", []))
                for insight in insights
                if isinstance(insight.get("evidence_event_ids"), list)
            } == set(sequences_by_ids)
        )

        metadata_matches = all(
            get_sequence(insight) is not None
            and insight.get("team") == get_sequence(insight)["team"]
            and insight.get("minute") == get_sequence(insight)["end_minute"]
            for insight in insights
        )

        audience_matches = all(
            insight.get("audience") == audience
            for insight in insights
        )

        narrative_is_complete = all(
            all(
                isinstance(insight.get(field), str)
                and bool(insight[field].strip())
                for field in ("title", "summary", "why_it_matters")
            )
            for insight in insights
        )

        check_results = [
            (
                "All evidence IDs exist in the match events",
                all_evidence_exists,
            ),
            (
                "Every insight maps to a detected sequence",
                every_insight_maps_to_sequence,
            ),
            (
                "Every sequence has exactly one insight",
                each_sequence_has_one_insight,
            ),
            (
                "Team and minute metadata match the sequence",
                metadata_matches,
            ),
            (
                "Insights use the requested audience mode",
                audience_matches,
            ),
            (
                "All narrative fields are complete",
                narrative_is_complete,
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
            "checks_passed": sum(
                check["passed"] for check in checks
            ),
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
        report = self.analysis_agent.run(
            match,
            self.analysis_function,
        )
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
            "shared_state_fields": [
                "report",
                "audience",
            ],
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
            "detail": (
                f"{len(insights)} {audience} insight(s) generated."
            ),
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
