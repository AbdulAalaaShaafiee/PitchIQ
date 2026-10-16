
"""PitchIQ local dashboard.

Uses the existing deterministic analysis and multi-agent workflow.
All match data is synthetic.
"""

import html

import altair as alt
import pandas as pd
import streamlit as st

from pitchiq.agents import PitchIQOrchestrator
from pitchiq.main import analyze_match, load_match


st.set_page_config(
    page_title="PitchIQ | Match Intelligence",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {
        max-width: 1440px;
        padding-top: 1.8rem;
        padding-bottom: 2.5rem;
    }

    .pitchiq-title {
        font-size: 2.8rem;
        font-weight: 850;
        letter-spacing: -0.06em;
        line-height: 1.1;
        margin-bottom: 0;
    }

    .pitchiq-subtitle {
        color: #738198;
        font-size: 0.9rem;
        letter-spacing: 0.12em;
        margin-top: 0.45rem;
        margin-bottom: 1.2rem;
    }

    .demo-banner {
        background: rgba(40, 120, 90, 0.09);
        border: 1px solid rgba(40, 120, 90, 0.28);
        border-radius: 12px;
        padding: 12px 16px;
        margin: 10px 0 22px 0;
    }

    .team-card {
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 23px 18px;
        text-align: center;
        min-height: 115px;
        background: var(--secondary-background-color);
    }

    .team-name {
        font-size: 1.3rem;
        font-weight: 750;
        overflow-wrap: anywhere;
    }

    .team-label {
        color: #738198;
        font-size: 0.72rem;
        letter-spacing: 0.12em;
        margin-bottom: 7px;
    }

    .score-card {
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 17px 10px;
        text-align: center;
        min-height: 115px;
        background: var(--secondary-background-color);
    }

    .score-value {
        font-size: 2.35rem;
        font-weight: 850;
        letter-spacing: 0.06em;
        line-height: 1.2;
    }

    .score-caption {
        color: #738198;
        font-size: 0.72rem;
        letter-spacing: 0.12em;
        margin-top: 5px;
    }

    div[data-testid="stMetric"] {
        background: var(--secondary-background-color);
        border: 1px solid var(--border-color);
        border-radius: 13px;
        padding: 14px 16px;
    }

    .section-note {
        color: #738198;
        font-size: 0.88rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Sidebar controls
with st.sidebar:
    st.markdown("## ⚽ PitchIQ")
    st.caption("SYNTHETIC MATCH INTELLIGENCE")

    st.divider()

    audience_label = st.radio(
        "Insight audience",
        options=["Fan", "Analyst"],
        index=0,
        help=(
            "Fan mode uses accessible language. Analyst mode "
            "provides more technical explanations and limitations."
        ),
    )
    audience = audience_label.lower()

    st.divider()

    st.markdown("**Demo information**")
    st.info(
        "This demo uses a locally stored synthetic football match. "
        "It does not require a paid AI API."
    )


# Load the existing dataset and run the original workflow.
try:
    match = load_match()

    orchestrator = PitchIQOrchestrator(analyze_match)
    result = orchestrator.run(match, audience)

    report = result["shared_state"]["report"]
    insights = result["shared_state"]["insights"]
    verification = result["shared_state"]["verification"]

except (OSError, ValueError, KeyError, TypeError) as error:
    st.error(f"PitchIQ could not process the match: {error}")
    st.stop()


home = report["home_team"]
away = report["away_team"]
stats = report["stats"]
score = report["score"]

events_by_id = {
    event["id"]: event
    for event in match["events"]
}


def finish_label(event):
    """Describe the recorded shot outcome without adding assumptions."""
    outcome = event.get("outcome")

    labels = {
        "goal": "Goal",
        "scored": "Goal",
        "saved": "Saved shot",
        "off_target": "Off-target shot",
        "on_target": "Shot on target",
    }

    return labels.get(outcome, event.get("type", "Event").title())


def evidence_table(event_ids):
    """Create a table showing exactly which events support a sequence."""
    rows = []

    for event_id in event_ids:
        event = events_by_id.get(event_id)

        if event is None:
            continue

        location = event.get("location") or {}

        rows.append({
            "Event ID": event["id"],
            "Minute": f"{event['minute']}'",
            "Period": event.get("period"),
            "Team": event["team"],
            "Player": event["player"],
            "Event type": event["type"],
            "Outcome": event["outcome"],
            "Pressure": event.get("pressure"),
            "Possession": event.get("possession_id"),
            "X (synthetic)": location.get("x"),
            "Y (synthetic)": location.get("y"),
        })

    return pd.DataFrame(rows)


# Header
st.markdown(
    '<div class="pitchiq-title">PITCHIQ</div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="pitchiq-subtitle">'
    'MULTI-AGENT MATCH INTELLIGENCE'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="demo-banner">
        <strong>DEMO MODE — SYNTHETIC DATA</strong><br>
        Match events, coordinates and pressure labels are fabricated
        for demonstration purposes, not collected from a real match.
    </div>
    """,
    unsafe_allow_html=True,
)


# Scoreboard
home_col, score_col, away_col = st.columns([2, 1, 2])

with home_col:
    st.markdown(
        f"""
        <div class="team-card">
            <div class="team-label">HOME TEAM</div>
            <div class="team-name">{html.escape(home)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with score_col:
    st.markdown(
        f"""
        <div class="score-card">
            <div class="team-label">FULL TIME</div>
            <div class="score-value">{score[home]} – {score[away]}</div>
            <div class="score-caption">FINAL SCORE</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with away_col:
    st.markdown(
        f"""
        <div class="team-card">
            <div class="team-label">AWAY TEAM</div>
            <div class="team-name">{html.escape(away)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Top-level comparison metrics
st.markdown("### Match at a glance")

metric_cols = st.columns(4)

metric_cols[0].metric(
    f"{home} shots",
    stats[home]["shots"],
)

metric_cols[1].metric(
    f"{away} shots",
    stats[away]["shots"],
)

home_accuracy = stats[home]["pass_accuracy_pct"]
away_accuracy = stats[away]["pass_accuracy_pct"]

metric_cols[2].metric(
    f"{home} pass accuracy",
    f"{home_accuracy}%" if home_accuracy is not None else "N/A",
)

metric_cols[3].metric(
    f"{away} pass accuracy",
    f"{away_accuracy}%" if away_accuracy is not None else "N/A",
)


# Main dashboard sections
overview_tab, insights_tab, workflow_tab, events_tab = st.tabs([
    "📊 Match overview",
    "💡 Insights & evidence",
    "🧠 Agent workflow",
    "🔎 Event explorer",
])


# MATCH OVERVIEW
with overview_tab:
    st.subheader("Team comparison")

    comparison_rows = [
        {
            "Statistic": "Goals",
            home: score[home],
            away: score[away],
        },
        {
            "Statistic": "Shots",
            home: stats[home]["shots"],
            away: stats[away]["shots"],
        },
        {
            "Statistic": "Passes attempted",
            home: stats[home]["passes_attempted"],
            away: stats[away]["passes_attempted"],
        },
        {
            "Statistic": "Passes completed",
            home: stats[home]["passes_completed"],
            away: stats[away]["passes_completed"],
        },
        {
            "Statistic": "Pass accuracy",
            home: (
                f"{home_accuracy}%"
                if home_accuracy is not None else "N/A"
            ),
            away: (
                f"{away_accuracy}%"
                if away_accuracy is not None else "N/A"
            ),
        },
        {
            "Statistic": "Tackles won",
            home: stats[home]["tackles_won"],
            away: stats[away]["tackles_won"],
        },
    ]

    st.dataframe(
        pd.DataFrame(comparison_rows),
        hide_index=True,
        width="stretch"
    )

    # Visual team comparison
    st.subheader("Visual team comparison")

    shots_col, accuracy_col = st.columns(2)

    with shots_col:
        st.markdown("**Shots by team**")
        shots_df = pd.DataFrame(
            {
                "Shots": [
                    stats[home]["shots"],
                    stats[away]["shots"],
                ]
            },
            index=[home, away],
        )
        st.bar_chart(shots_df)

    with accuracy_col:
        st.markdown("**Pass accuracy by team**")
        accuracy_df = pd.DataFrame(
            {
                "Pass accuracy (%)": [
                    (
                        stats[home]["pass_accuracy_pct"]
                        if stats[home]["pass_accuracy_pct"] is not None
                        else 0
                    ),
                    (
                        stats[away]["pass_accuracy_pct"]
                        if stats[away]["pass_accuracy_pct"] is not None
                        else 0
                    ),
                ]
            },
            index=[home, away],
        )
        st.bar_chart(accuracy_df)
        st.caption(
            "A displayed 0% means no passes were completed successfully; "
            "check the comparison table for N/A where no passes were attempted."
        )

    st.markdown("**Completed vs incomplete passes**")
    pass_distribution = pd.DataFrame(
        {
            "Completed": [
                stats[home]["passes_completed"],
                stats[away]["passes_completed"],
            ],
            "Incomplete": [
                (
                    stats[home]["passes_attempted"]
                    - stats[home]["passes_completed"]
                ),
                (
                    stats[away]["passes_attempted"]
                    - stats[away]["passes_completed"]
                ),
            ],
        },
        index=[home, away],
    )
    st.bar_chart(pass_distribution, stack=True)

    # Timeline of detected attacks
    st.subheader("Attacking sequence timeline")
    st.caption(
        "Each line spans the first pass through the finishing event. "
        "The marker identifies the recorded finish. All data is synthetic."
    )

    timeline_rows = []

    for sequence in report["attacking_sequences"]:
        finish_event = events_by_id.get(sequence["event_ids"][-1], {})

        timeline_rows.append(
            {
                "Team": sequence["team"],
                "Start minute": sequence["start_minute"],
                "End minute": sequence["end_minute"],
                "Sequence": (
                    f"{sequence['team']} · "
                    f"{sequence['start_minute']}–"
                    f"{sequence['end_minute']}' · "
                    f"{finish_label(finish_event)}"
                ),
                "Finish": finish_label(finish_event),
                "Passes": sequence["passes"],
                "Evidence": ", ".join(
                    map(str, sequence["event_ids"])
                ),
            }
        )

    if timeline_rows:
        timeline_df = pd.DataFrame(timeline_rows)

        timeline_y = alt.Y(
            "Sequence:N",
            sort=alt.SortField(
                field="Start minute",
                order="ascending",
            ),
            title=None,
        )

        timeline_tooltips = [
            alt.Tooltip("Team:N", title="Team"),
            alt.Tooltip("Start minute:Q", title="Start minute"),
            alt.Tooltip("End minute:Q", title="Finish minute"),
            alt.Tooltip("Finish:N", title="Recorded finish"),
            alt.Tooltip("Passes:Q", title="Completed passes"),
            alt.Tooltip("Evidence:N", title="Event IDs"),
        ]

        sequence_lines = alt.Chart(timeline_df).mark_rule(
            strokeWidth=7,
            strokeCap="round",
        ).encode(
            x=alt.X(
                "Start minute:Q",
                scale=alt.Scale(domain=[0, 90]),
                axis=alt.Axis(tickCount=10),
                title="Match minute",
            ),
            x2="End minute:Q",
            y=timeline_y,
            color=alt.Color("Team:N", title="Team"),
            tooltip=timeline_tooltips,
        )

        finish_markers = alt.Chart(timeline_df).mark_point(
            filled=True,
            size=140,
            stroke="white",
            strokeWidth=1,
        ).encode(
            x=alt.X(
                "End minute:Q",
                scale=alt.Scale(domain=[0, 90]),
                title="Match minute",
            ),
            y=alt.Y(
                "Sequence:N",
                sort=alt.SortField(
                    field="Start minute",
                    order="ascending",
                ),
                title=None,
            ),
            color=alt.Color("Team:N", title="Team"),
            tooltip=timeline_tooltips,
        )

        timeline_chart = (
            (sequence_lines + finish_markers)
            .properties(height=max(150, 55 * len(timeline_df)))
            .configure_view(stroke=None)
        )

        st.altair_chart(
            timeline_chart,
            width="stretch"
        )
    else:
        st.info("No attacking sequences are available to plot.")

    st.subheader("Detected attacking sequences")
    st.caption(
        "The current transparent rule looks for at least two consecutive "
        "completed passes followed by a shot or goal within three minutes. "
        "It is a demonstration rule, not a validated tactical model."
    )

    sequences = report["attacking_sequences"]

    if not sequences:
        st.info("No attacking sequences matched the current detection rule.")

    for sequence in sequences:
        event_ids = sequence["event_ids"]
        last_event = events_by_id.get(event_ids[-1], {})
        outcome_text = finish_label(last_event)

        with st.container(border=True):
            left, right = st.columns([4, 1])

            with left:
                st.markdown(
                    f"**{sequence['team']} · "
                    f"{sequence['start_minute']}'–"
                    f"{sequence['end_minute']}'**"
                )
                st.write(
                    f"{sequence['passes']} completed passes followed "
                    f"by {outcome_text.lower()}."
                )
                st.caption(
                    "Supporting event IDs: "
                    + ", ".join(map(str, event_ids))
                )

            with right:
                st.metric("Completed passes", sequence["passes"])


# INSIGHTS & EVIDENCE
with insights_tab:
    st.subheader(f"{audience_label} insights")

    if not verification["passed"]:
        st.error(
            "Evidence verification failed. Insights are withheld "
            "because one or more integrity checks did not pass."
        )
        st.write("Issues detected:", verification["errors"])

    elif not insights:
        st.info("No insights are available for this match.")

    else:
        st.success(
            "Evidence verification passed. "
            f"{verification['checks_passed']}/"
            f"{verification['checks_total']} checks passed."
        )

        for insight in insights:
            with st.container(border=True):
                st.markdown(f"#### {insight['title']}")

                st.caption(
                    f"Team: {insight['team']} · "
                    f"Minute: {insight['minute']}' · "
                    f"Audience: {insight['audience'].title()}"
                )

                st.write(insight["summary"])

                st.markdown("**Why it matters**")
                st.write(insight["why_it_matters"])

                st.caption(
                    "Supporting event IDs: "
                    + ", ".join(
                        map(str, insight["evidence_event_ids"])
                    )
                )

                with st.expander("Inspect supporting events"):
                    event_df = evidence_table(
                        insight["evidence_event_ids"]
                    )

                    st.dataframe(
                        event_df,
                        hide_index=True,
                        width="stretch"
                    )

                with st.expander("Data limitations"):
                    st.write(insight["limitation"])


# AGENT WORKFLOW
with workflow_tab:
    st.subheader("Multi-agent execution")

    st.caption(
        "These are deterministic Python agents coordinated through "
        "a local workflow. They are not LLM-powered agents yet."
    )

    for index, step in enumerate(result["steps"], start=1):
        with st.container(border=True):
            status = step["status"].upper()
            icon = "✅" if status in {"COMPLETED", "PASSED"} else "❌"

            st.markdown(
                f"**{index}. {step['agent']}** · {icon} {status}"
            )
            st.write(step["detail"])

    st.subheader("Agent handoffs")

    for handoff in result["handoffs"]:
        st.markdown(
            f"**{handoff['from']}** → **{handoff['to']}**"
        )
        st.caption(
            "Shared state: "
            + ", ".join(handoff["shared_state_fields"])
        )

    st.subheader("Evidence verification")

    if verification["passed"]:
        st.success(
            f"PASSED — {verification['checks_passed']}/"
            f"{verification['checks_total']} checks"
        )
    else:
        st.error(
            f"FAILED — {verification['checks_passed']}/"
            f"{verification['checks_total']} checks"
        )

    for check in verification["checks"]:
        marker = "✅" if check["passed"] else "❌"
        st.write(f"{marker} {check['name']}")


# EVENT EXPLORER
with events_tab:
    st.subheader("Synthetic event explorer")

    all_event_rows = []

    for event in sorted(
        match["events"],
        key=lambda item: (
            item["period"],
            item["minute"],
            item["id"],
        ),
    ):
        location = event.get("location") or {}

        all_event_rows.append({
            "Event ID": event["id"],
            "Minute": event["minute"],
            "Period": event["period"],
            "Team": event["team"],
            "Player": event["player"],
            "Type": event["type"],
            "Outcome": event["outcome"],
            "Possession": event.get("possession_id"),
            "Phase": event.get("phase"),
            "Pressure": event.get("pressure"),
            "X (synthetic)": location.get("x"),
            "Y (synthetic)": location.get("y"),
        })

    all_events_df = pd.DataFrame(all_event_rows)

    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        selected_team = st.selectbox(
            "Filter by team",
            ["All teams", home, away],
        )

    with filter_col2:
        event_types = [
            "All types",
            *sorted(all_events_df["Type"].unique().tolist()),
        ]

        selected_type = st.selectbox(
            "Filter by event type",
            event_types,
        )

    search_query = st.text_input(
        "Search by player or event ID",
        placeholder="For example: Player H3 or 3",
    )

    filtered_events = all_events_df.copy()

    if selected_team != "All teams":
        filtered_events = filtered_events[
            filtered_events["Team"] == selected_team
        ]

    if selected_type != "All types":
        filtered_events = filtered_events[
            filtered_events["Type"] == selected_type
        ]

    if search_query.strip():
        search_mask = (
            filtered_events["Player"].astype(str).str.contains(
                search_query, case=False, regex=False
            )
            | filtered_events["Event ID"].astype(str).str.contains(
                search_query, case=False, regex=False
            )
        )

        filtered_events = filtered_events[search_mask]

    st.caption(
        f"Showing {len(filtered_events)} of "
        f"{len(all_events_df)} events."
    )

    st.dataframe(
        filtered_events,
        hide_index=True,
        width="stretch"
    )


st.divider()

st.caption(
    "PitchIQ · Local demonstration · Synthetic match data · "
    "No validated shot-quality model or tracking-based tactical claims."
)
