"""Streamlit page for importing and analysing real historical matches."""
from __future__ import annotations

import inspect
import json
from typing import Any

import pandas as pd
import streamlit as st

from pitchiq.agents import PitchIQOrchestrator
from pitchiq.match_playback import render_match_playback
from pitchiq.statsbomb import (
    MEDIA_PACK_URL,
    REPOSITORY_URL,
    StatsBombDataError,
    analyze_statsbomb_match,
    StatsBombOpenDataAgent,
)

st.set_page_config(page_title="Real-Match Explorer | PitchIQ", page_icon="⚽", layout="wide")

st.title("Real-Match Explorer")
st.caption("Discover selected historical football matches, import their event data, and analyse them with PitchIQ.")
st.markdown(
    "**Data source:** [StatsBomb Open Data](" + REPOSITORY_URL + ")  \n"
    "This is historical open data, not a live-score feed. When publishing or sharing analysis, "
    "credit StatsBomb and use the logo from the [official media pack](" + MEDIA_PACK_URL + ")."
)

with st.sidebar:
    st.markdown("## ⚽ PitchIQ")
    st.caption("REAL MATCH INTELLIGENCE")
    st.link_button("↗ Advanced Mode", "http://127.0.0.1:8765/", width="stretch")
    st.link_button("↗ Main Dashboard", "http://127.0.0.1:8765/basic/", width="stretch")
    st.divider()
    audience_label = st.radio("Analysis audience", ["Analyst", "Fan"], index=0)
    audience = audience_label.casefold()
    refresh = st.button("Refresh online catalogue", use_container_width=True)

agent = StatsBombOpenDataAgent()

@st.cache_data(ttl=1800, show_spinner=False)
def _load_competitions(force_refresh: bool = False) -> list[dict[str, Any]]:
    return agent.list_competitions(refresh=force_refresh)

@st.cache_data(ttl=1800, show_spinner=False)
def _load_matches(competition_id: int, season_id: int, force_refresh: bool = False) -> list[dict[str, Any]]:
    return agent.list_matches(competition_id, season_id, refresh=force_refresh)

if refresh:
    _load_competitions.clear()
    _load_matches.clear()
    st.cache_data.clear()

try:
    competitions = _load_competitions(refresh)
except (StatsBombDataError, ValueError) as exc:
    st.error(f"Could not load the StatsBomb catalogue: {exc}")
    st.info("Check that this computer is online, then choose **Refresh online catalogue**.")
    st.stop()

if not competitions:
    st.warning("No competition/season entries were returned by StatsBomb Open Data.")
    st.stop()

competition_labels = [
    f"{row['competition_name']} — {row['season_name']} ({row['country_name']})"
    for row in competitions
]
selected_label = st.selectbox("Competition and season", competition_labels)
selected_competition = competitions[competition_labels.index(selected_label)]

try:
    matches = _load_matches(
        selected_competition["competition_id"],
        selected_competition["season_id"],
        refresh,
    )
except (StatsBombDataError, ValueError) as exc:
    st.error(f"Could not load matches for this competition/season: {exc}")
    st.stop()

filter_text = st.text_input("Filter by team name", placeholder="For example, Barcelona or Arsenal")
if filter_text.strip():
    lowered = filter_text.strip().casefold()
    matches = [m for m in matches if lowered in m["home_team"].casefold() or lowered in m["away_team"].casefold()]

if not matches:
    st.warning("No matches match that filter in this competition and season.")
    st.stop()


def _score_label(match_row: dict[str, Any]) -> str:
    home_score, away_score = match_row.get("home_score"), match_row.get("away_score")
    if home_score is None or away_score is None:
        score = "score unavailable"
    else:
        score = f"{home_score}–{away_score}"
    date = match_row.get("match_date") or "date unknown"
    return f"{date} | {match_row['home_team']} {score} {match_row['away_team']}"

match_labels = [_score_label(row) for row in matches]
chosen_match_label = st.selectbox("Match", match_labels)
chosen_match = matches[match_labels.index(chosen_match_label)]

with st.expander("What will be imported?", expanded=False):
    st.write(
        "PitchIQ downloads the event JSON for the selected match, maps supported source events into its existing schema, "
        "and sends the result through the current analysis pipeline. StatsBomb coordinates are scaled from 120×80 to "
        "PitchIQ's 105×68 pitch. Unsupported events or outcomes are omitted with a warning rather than re-labelled inaccurately."
    )

if st.button("Import match and analyse", type="primary", use_container_width=True):
    with st.spinner("Downloading source events, validating the import, and running PitchIQ analysis..."):
        try:
            imported = agent.import_match(
                chosen_match["match_id"],
                selected_competition["competition_id"],
                selected_competition["season_id"],
            )
            report = analyze_statsbomb_match(imported)
            agent_result: Any = None
            agent_error: str | None = None
            # Use the existing orchestration code, adapting only to its declared
            # method signature; do not guess positional argument order.
            orchestrator = PitchIQOrchestrator(analyze_statsbomb_match)
            method = next((
                getattr(orchestrator, name, None)
                for name in ("run", "analyze", "execute")
                if callable(getattr(orchestrator, name, None))
            ), None)
            if method is None:
                agent_error = "The existing orchestrator exposes no run/analyze/execute method. The deterministic analysis is still available below."
            else:
                try:
                    signature = inspect.signature(method)
                    parameters = signature.parameters
                    kwargs: dict[str, Any] = {}
                    if "audience" in parameters:
                        kwargs["audience"] = audience
                    elif "mode" in parameters:
                        kwargs["mode"] = audience
                    agent_result = method(imported, **kwargs)
                except Exception as exc:  # keep the deterministic report available if a language agent fails
                    agent_error = f"Agent narrative was unavailable: {type(exc).__name__}: {exc}"
            st.session_state["pitchiq_statsbomb_result"] = {
                "match": imported,
                "report": report,
                "agent_result": agent_result,
                "agent_error": agent_error,
                "audience": audience,
            }
        except (StatsBombDataError, ValueError, KeyError, TypeError) as exc:
            st.error(f"The match could not be imported or analysed: {exc}")
        except Exception as exc:
            st.error(f"PitchIQ could not complete this analysis ({type(exc).__name__}): {exc}")

result = st.session_state.get("pitchiq_statsbomb_result")
if result:
    match = result["match"]
    report = result["report"]
    meta = match.get("_pitchiq_import", {})
    st.divider()
    st.header(f"{match['home_team']} vs {match['away_team']}")
    st.caption(
        f"{meta.get('competition', 'StatsBomb Open Data')} · {meta.get('season', 'Season not supplied')} · "
        f"{meta.get('match_date', 'Date not supplied')} · Source match ID {meta.get('statsbomb_match_id', 'not supplied')}"
    )

    source_home, source_away = meta.get("source_home_score"), meta.get("source_away_score")
    report_score = report.get("score", {}) if isinstance(report, dict) else {}
    if source_home is not None and source_away is not None:
        try:
            source_home, source_away = int(source_home), int(source_away)
            derived_home = int(report_score.get(match["home_team"], 0))
            derived_away = int(report_score.get(match["away_team"], 0))
            st.subheader("Source result and event-derived score")
            c1, c2 = st.columns(2)
            c1.metric("Published source score", f"{source_home}–{source_away}")
            c2.metric("Score from imported goal events", f"{derived_home}–{derived_away}")
            if (source_home, source_away) != (derived_home, derived_away):
                st.warning(
                    "The imported event subset does not reproduce the published score. "
                    "Review the event-coverage warnings before relying on the score-derived analysis."
                )
        except (TypeError, ValueError):
            st.info("The published score was not available in a usable numeric form.")
    else:
        st.info("StatsBomb did not provide a source score for this record; the dashboard will not invent one.")

    st.subheader("Team statistics")
    stats = report.get("stats", {}) if isinstance(report, dict) else {}
    if isinstance(stats, dict) and stats:
        st.dataframe(pd.DataFrame.from_dict(stats, orient="index").rename_axis("Team"), use_container_width=True)
    else:
        st.info("PitchIQ did not return a team-statistics table for this match.")

    st.subheader("Match playback + synchronized event explanations")
    st.caption(
        "Use a video you are authorized to view. StatsBomb supplies the event timeline, not the match footage. "
        "The explanation card updates in the embedded player as playback reaches each source timestamp."
    )
    timeline_events = meta.get("event_timeline", []) if isinstance(meta, dict) else []
    render_match_playback(
        timeline_events,
        match_label=(
            f"{match.get('home_team', 'Home team')} vs {match.get('away_team', 'Away team')} · "
            f"{meta.get('match_date', 'date not supplied')}"
        ),
    )

    sequences = report.get("attacking_sequences", []) if isinstance(report, dict) else []
    st.subheader("Evidence-backed attacking sequences")
    st.caption(
        "Each sequence is a rule-based event pattern, not a validated tactical model. "
        "Expand a sequence to inspect the recorded event evidence."
    )
    event_lookup = {
        event.get("id"): event
        for event in match.get("events", [])
        if isinstance(event, dict) and event.get("id") is not None
    }
    if sequences:
        for index, sequence in enumerate(sequences, start=1):
            if not isinstance(sequence, dict):
                continue
            team = sequence.get("team") or sequence.get("team_name") or "Team not supplied"
            start_minute = sequence.get("start_minute")
            end_minute = sequence.get("end_minute", start_minute)
            passes = sequence.get("passes", "—")
            event_ids = sequence.get("event_ids", [])
            evidence_basis = sequence.get("evidence_basis")
            minute_label = (
                f"{start_minute}′" if start_minute == end_minute
                else f"{start_minute}′–{end_minute}′"
            )
            finish_event = event_lookup.get(event_ids[-1]) if isinstance(event_ids, list) and event_ids else None
            finish_outcome = str((finish_event or {}).get("outcome", ""))
            finish_type = str((finish_event or {}).get("type", sequence.get("finish", "shot")))
            finish_labels = {
                "goal": "Goal", "scored": "Goal", "saved": "Saved shot",
                "off_target": "Off-target shot", "on_target": "On-target shot",
                "complete": "Completed pass", "incomplete": "Incomplete pass",
            }
            finish_label = finish_labels.get(finish_outcome, finish_type.replace("_", " ").title())
            finish_player = (finish_event or {}).get("player")
            finish_description = f"{finish_player} · {finish_label}" if finish_player and finish_label else finish_label

            with st.container(border=True):
                heading, minute_col, passes_col = st.columns([3, 1, 1])
                heading.markdown(f"#### {index}. {team}")
                heading.write(f"Recorded finish: {finish_description}")
                minute_col.metric("Minute", minute_label)
                passes_col.metric("Completed passes", passes)
                if evidence_basis == "same_possession":
                    st.caption(
                        "Evidence method: completed passes recorded in the same possession before the finish. "
                        "Other actions may have occurred between passes."
                    )
                evidence_ids_text = ", ".join(str(value) for value in event_ids) if isinstance(event_ids, list) else "Not supplied"
                st.caption(f"PitchIQ event IDs: {evidence_ids_text or 'Not supplied'}")
                with st.expander(f"Inspect event evidence · Sequence {index}", expanded=False):
                    evidence_rows = []
                    if isinstance(event_ids, list):
                        for event_id in event_ids:
                            event = event_lookup.get(event_id)
                            if not event:
                                continue
                            location = event.get("location")
                            end_location = event.get("end_location")
                            evidence_rows.append({
                                "PitchIQ ID": event.get("id"),
                                "Source ID": event.get("source_event_id", "—"),
                                "Minute": event.get("minute", "—"),
                                "Period": event.get("period", "—"),
                                "Team": event.get("team", "—"),
                                "Player": event.get("player", "Not supplied"),
                                "Event": str(event.get("type", "—")).replace("_", " ").title(),
                                "Outcome": str(event.get("outcome", "—")).replace("_", " ").title(),
                                "Start location": (
                                    f"({location.get('x')}, {location.get('y')})"
                                    if isinstance(location, dict) else "Not supplied"
                                ),
                                "End location": (
                                    f"({end_location.get('x')}, {end_location.get('y')})"
                                    if isinstance(end_location, dict) else "Not supplied"
                                ),
                            })
                    if evidence_rows:
                        st.dataframe(pd.DataFrame(evidence_rows), use_container_width=True, hide_index=True)
                    else:
                        st.info("The selected evidence events could not be found in the imported match.")
    else:
        st.info(
            "No attacking sequences met PitchIQ's evidence requirements for this event subset. "
            "This is not proof that no attacks occurred."
        )

    warnings = meta.get("warnings", [])
    st.subheader("Import quality and limitations")
    st.write(
        f"Source events: **{meta.get('source_event_count', meta.get('event_count', 'unknown'))}** · "
        f"Imported events: **{meta.get('imported_event_count', meta.get('event_count', 'unknown'))}** · "
        f"Skipped events: **{meta.get('skipped_event_count', 0)}**"
    )
    for warning in warnings:
        st.warning(warning)
    st.caption(
        "Tactical phase labels, pressure intensity, possession context, and other unsupported metrics are not inferred when absent. "
        "xG, next-goal probability, and other predictive metrics are not created by this importer."
    )

    st.subheader(f"{result['audience'].title()}-mode agent analysis")
    agent_output = result.get("agent_result")
    agent_error = result.get("agent_error")
    if isinstance(agent_output, dict):
        shared_state = agent_output.get("shared_state", {})
        insights = shared_state.get("insights", []) if isinstance(shared_state, dict) else []
        verification = shared_state.get("verification", {}) if isinstance(shared_state, dict) else {}
        steps = agent_output.get("steps", [])

        if isinstance(verification, dict) and verification:
            passed = bool(verification.get("passed"))
            checks_passed = verification.get("checks_passed", 0)
            checks_total = verification.get("checks_total", 0)
            if passed:
                st.success(f"Evidence verification passed · {checks_passed}/{checks_total} checks")
            else:
                st.error(f"Evidence verification failed · {checks_passed}/{checks_total} checks. Insight narratives are withheld.")
            with st.expander("Review evidence-verification checks", expanded=not passed):
                for check in verification.get("checks", []):
                    if not isinstance(check, dict):
                        continue
                    mark = "✅" if check.get("passed") else "❌"
                    st.markdown(f"{mark} {check.get('name', 'Unnamed check')}")
                for error in verification.get("errors", []):
                    st.warning(str(error))

        if steps:
            st.markdown("**Agent workflow**")
            step_columns = st.columns(min(3, len(steps)))
            for index, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue
                with step_columns[index % len(step_columns)]:
                    st.markdown(f"**{step.get('agent', 'Agent')}**")
                    status = str(step.get("status", "unknown")).lower()
                    detail = str(step.get("detail", ""))
                    if status in {"passed", "completed", "success"}:
                        st.success(status.title())
                    elif status in {"rejected", "failed", "error"}:
                        st.error(status.title())
                    else:
                        st.info(status.title())
                    if detail:
                        st.caption(detail)

        if isinstance(verification, dict) and verification.get("passed") and isinstance(insights, list) and insights:
            st.markdown("**Verified insights**")
            for item in insights:
                if not isinstance(item, dict):
                    continue
                team = item.get("team")
                minute = item.get("minute")
                with st.container(border=True):
                    st.markdown(f"#### {item.get('title', 'Match insight')}")
                    metadata = [str(value) for value in (team, f"Minute {minute}" if minute is not None else None) if value]
                    if metadata:
                        st.caption(" · ".join(metadata))
                    if item.get("summary"):
                        st.write(item["summary"])
                    if item.get("why_it_matters"):
                        st.markdown("**Why it matters**")
                        st.write(item["why_it_matters"])
                    evidence_ids = item.get("evidence_event_ids", [])
                    if isinstance(evidence_ids, list):
                        st.caption("Evidence event IDs: " + (", ".join(str(value) for value in evidence_ids) or "Not supplied"))
                    commentary = item.get("ai_commentary")
                    if commentary:
                        st.info(f"Optional local-AI wording: {commentary}")
                    if item.get("limitation"):
                        with st.expander("Data and interpretation limits", expanded=False):
                            st.write(item["limitation"])
        elif isinstance(verification, dict) and not verification.get("passed"):
            st.warning("PitchIQ did not display insights because the evidence-verification stage did not pass.")
        elif not insights:
            st.info("The agents completed, but no supported insights were generated for this match. This does not mean no notable events occurred.")
        else:
            st.info("The agent output did not include a complete evidence-verification result, so the insight narratives are not displayed.")
    elif isinstance(agent_output, str) and agent_output.strip():
        st.markdown(agent_output)
    elif agent_error:
        st.info(str(agent_error))
        st.caption("The deterministic match report above remains available independently of the narrative agent.")
    else:
        st.info("No agent narrative was returned for this import. The deterministic match report remains available above.")

    st.markdown(
        f"**Source:** [StatsBomb Open Data — event file]({meta.get('source_event_url', REPOSITORY_URL)}) · "
        f"[Competition match list]({meta.get('source_matches_url', REPOSITORY_URL)})"
    )
