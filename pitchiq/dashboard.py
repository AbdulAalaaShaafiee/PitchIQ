
"""PitchIQ local dashboard.

Uses the existing deterministic analysis and multi-agent workflow.
All match data is synthetic.
"""

import html
import math

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
    :root {
        --pq-ink: #14243a;
        --pq-muted: #60758e;
        --pq-green: #10b981;
        --pq-blue: #168bda;
        --pq-amber: #f5a623;
        --pq-border: #dce8f3;
    }

    .stApp {
        background: linear-gradient(
            145deg,
            #f2f9ff 0%,
            #f7fff9 55%,
            #ffffff 100%
        );
        color: var(--pq-ink);
    }

.block-container {
    max-width: 1500px;
    padding-top: 1.6rem;
    padding-bottom: 3rem;
}

.pitchiq-title {
    font-size: 3rem;
    font-weight: 900;
    letter-spacing: -0.065em;
    line-height: 1.08;
    color: #102a43;
    margin-bottom: 0;
}

.pitchiq-subtitle {
    color: var(--pq-muted);
    font-size: 0.85rem;
    font-weight: 750;
    letter-spacing: 0.14em;
    margin: 0.5rem 0 1.4rem;
}

.demo-banner {
    background: linear-gradient(105deg, #d9f9ec, #e5f3ff);
    border: 1px solid #c7eadf;
    border-radius: 16px;
    padding: 15px 19px;
    margin: 12px 0 24px;
    color: #174d48;
}

.team-card,
.score-card {
    min-height: 124px;
    border: 1px solid var(--pq-border);
    border-radius: 20px;
    padding: 22px 16px;
    text-align: center;
    box-shadow: 0 7px 24px rgba(31, 77, 112, 0.07);
    transition: transform 160ms ease, box-shadow 160ms ease;
}

.team-card {
    background: linear-gradient(150deg, #ffffff, #e9fbf3);
}

.score-card {
    background: linear-gradient(135deg, #0f9f76, #168bda);
    color: #ffffff;
    border-color: transparent;
}

.team-card:hover,
.score-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 28px rgba(31, 77, 112, 0.13);
}

.team-name {
    font-size: 1.25rem;
    font-weight: 850;
    overflow-wrap: anywhere;
    color: #14243a;
}

.team-label,
.score-caption {
    font-size: 0.72rem;
    font-weight: 750;
    letter-spacing: 0.12em;
    margin-bottom: 8px;
}

.team-label {
    color: #60758e;
}

.score-value {
    font-size: 2.45rem;
    font-weight: 900;
    letter-spacing: 0.04em;
    line-height: 1.15;
}

.score-caption {
    margin-top: 6px;
    color: rgba(255, 255, 255, 0.9);
}

div[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid var(--pq-border);
    border-radius: 16px;
    padding: 15px 17px;
    box-shadow: 0 5px 20px rgba(31, 77, 112, 0.05);
}

div[data-testid="stMetricLabel"] {
    color: var(--pq-muted);
    font-weight: 650;
}

[data-testid="stTabs"] button[aria-selected="true"] {
    background: #dcf8eb;
    color: #087751;
    border-radius: 12px 12px 0 0;
    font-weight: 800;
}

[data-testid="stTabs"] button {
    transition: background 140ms ease, color 140ms ease;
}

.stButton > button {
    border: 1px solid #c9e6db;
    border-radius: 12px;
    min-height: 42px;
    font-weight: 750;
    transition: transform 140ms ease, box-shadow 140ms ease;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 7px 16px rgba(22, 139, 218, 0.12);
    border-color: #10b981;
    color: #087751;
}

[data-testid="stExpander"] {
    background: #ffffff;
    border: 1px solid var(--pq-border);
    border-radius: 14px;
}

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    border-radius: 12px;
    overflow: hidden;
}

.section-note {
    color: var(--pq-muted);
    font-size: 0.9rem;
}

@media (max-width: 800px) {
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .pitchiq-title {
        font-size: 2.35rem;
    }

    .team-name {
        font-size: 1rem;
    }
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
replay_tab, overview_tab, insights_tab, workflow_tab, events_tab = st.tabs([
    "🎮 Match replay",
    "📊 Match overview",
    "💡 Insights & evidence",
    "🧠 Agent workflow",
    "🔎 Event explorer",
])


# INTERACTIVE MATCH REPLAY
with replay_tab:
    st.subheader("Interactive match replay")
    st.caption(
        "Explore the synthetic match event by event. "
        "Score, statistics, pitch markers and insights update with the replay."
    )

    replay_events = sorted(
        match["events"],
        key=lambda event: (
            event.get("period", 1),
            event["minute"],
            event["id"],
        ),
    )
    total = len(replay_events)

    if "replay_cursor" not in st.session_state:
        st.session_state["replay_cursor"] = total

    st.session_state["replay_cursor"] = min(
        max(0, int(st.session_state["replay_cursor"])),
        total,
    )

    def replay_previous():
        st.session_state["replay_cursor"] = max(
            0, st.session_state["replay_cursor"] - 1
        )

    def replay_next():
        st.session_state["replay_cursor"] = min(
            total, st.session_state["replay_cursor"] + 1
        )

    key_moments = {}
    for index, event in enumerate(replay_events, start=1):
        if event["type"] in {"shot", "goal"}:
            label = (
                f"{event['minute']}' · {event['team']} · "
                f"{finish_label(event)} · Event {event['id']}"
            )
            key_moments[label] = index

    controls = st.columns([1, 1, 2, 1])

    with controls[0]:
        st.button(
            "◀ Previous",
            key="replay_previous_button",
            on_click=replay_previous,
            disabled=st.session_state["replay_cursor"] == 0,
            width="stretch",
        )

    with controls[1]:
        st.button(
            "Next ▶",
            key="replay_next_button",
            on_click=replay_next,
            disabled=st.session_state["replay_cursor"] >= total,
            width="stretch",
        )

    with controls[2]:
        if key_moments:
            selected_moment = st.selectbox(
                "Jump to moment",
                list(key_moments.keys()),
                key="replay_jump_choice",
            )
        else:
            selected_moment = None
            st.caption("No shots or goals available.")

    with controls[3]:
        if st.button(
            "Jump",
            key="replay_jump_button",
            type="primary",
            disabled=selected_moment is None,
            width="stretch",
        ):
            st.session_state["replay_cursor"] = key_moments[
                selected_moment
            ]

    cursor = st.slider(
        "Replay position",
        min_value=0,
        max_value=total,
        step=1,
        key="replay_cursor",
        help="Move backward or forward through the match events.",
    )

    revealed = replay_events[:cursor]
    current = revealed[-1] if revealed else None

    st.progress(
        cursor / max(total, 1),
        text=f"{cursor} of {total} events revealed",
    )

    # Run the existing analysis and agents on the revealed portion only.
    replay_match = {**match, "events": revealed}
    replay_result = PitchIQOrchestrator(analyze_match).run(
        replay_match,
        audience,
    )

    replay_report = replay_result["shared_state"]["report"]
    replay_insights = replay_result["shared_state"]["insights"]
    replay_verification = replay_result["shared_state"]["verification"]

    replay_score = replay_report["score"]
    replay_stats = replay_report["stats"]

    score_cols = st.columns([1, 0.8, 1])
    score_cols[0].metric(home, replay_score[home])
    score_cols[1].metric("Events revealed", f"{cursor}/{total}")
    score_cols[2].metric(away, replay_score[away])

    stats_cols = st.columns(4)
    home_accuracy = replay_stats[home]["pass_accuracy_pct"]
    away_accuracy = replay_stats[away]["pass_accuracy_pct"]

    stats_cols[0].metric("Home shots", replay_stats[home]["shots"])
    stats_cols[1].metric("Away shots", replay_stats[away]["shots"])
    stats_cols[2].metric(
        "Home pass accuracy",
        f"{home_accuracy}%" if home_accuracy is not None else "N/A",
    )
    stats_cols[3].metric(
        "Away pass accuracy",
        f"{away_accuracy}%" if away_accuracy is not None else "N/A",
    )

    if current:
        st.markdown(
            f"**Current event: {current['minute']}' · "
            f"{current['team']} · {current['player']}**"
        )
        st.write(
            f"{current['type'].replace('_', ' ').title()} — "
            f"{current['outcome'].replace('_', ' ')}"
        )
    else:
        st.info("Kickoff: no events have been revealed.")

    # Draw a pitch using the synthetic event coordinates.
    st.markdown("### Event pitch")
    st.caption(
        "The pitch positions are synthetic demonstration coordinates, "
        "not real player-tracking measurements."
    )

    pitch_col, detail_col = st.columns([1.4, 1])

    with pitch_col:
        pitch_segments = {
            "boundary": [
                (0, 0), (105, 0), (105, 68), (0, 68), (0, 0)
            ],
            "halfway": [(52.5, 0), (52.5, 68)],
            "left_box": [
                (0, 13.84), (16.5, 13.84), (16.5, 54.16),
                (0, 54.16), (0, 13.84)
            ],
            "right_box": [
                (88.5, 13.84), (105, 13.84), (105, 54.16),
                (88.5, 54.16), (88.5, 13.84)
            ],
            "centre_circle": [
                (
                    52.5 + 9.15 * math.cos(math.radians(degree)),
                    34 + 9.15 * math.sin(math.radians(degree)),
                )
                for degree in range(0, 361, 10)
            ],
        }

        line_rows = []
        for segment, points in pitch_segments.items():
            for order, (x, y) in enumerate(points):
                line_rows.append({
                    "segment": segment,
                    "order": order,
                    "x": x,
                    "y": y,
                })

        line_df = pd.DataFrame(line_rows)

        field_background = alt.Chart(
            pd.DataFrame([{"x": 0, "x2": 105, "y": 0, "y2": 68}])
        ).mark_rect(
            color="#dff4e5",
            stroke="#a3cbb0",
        ).encode(
            x=alt.X("x:Q", scale=alt.Scale(domain=[0, 105]), axis=None),
            x2="x2:Q",
            y=alt.Y("y:Q", scale=alt.Scale(domain=[68, 0]), axis=None),
            y2="y2:Q",
        )

        field_lines = alt.Chart(line_df).mark_line(
            color="#ffffff",
            strokeWidth=2,
        ).encode(
            x=alt.X("x:Q", scale=alt.Scale(domain=[0, 105]), axis=None),
            y=alt.Y("y:Q", scale=alt.Scale(domain=[68, 0]), axis=None),
            detail="segment:N",
            order="order:Q",
        )

        pitch_chart = field_background + field_lines
        recent_rows = []

        for event in revealed[-12:]:
            point = event.get("location") or {}
            if {"x", "y"}.issubset(point):
                recent_rows.append({
                    "id": event["id"],
                    "minute": event["minute"],
                    "team": event["team"],
                    "player": event["player"],
                    "type": event["type"],
                    "outcome": event["outcome"],
                    "x": point["x"],
                    "y": point["y"],
                })

        team_scale = alt.Scale(
            domain=[home, away],
            range=["#0da878", "#168bda"],
        )

        tooltip = [
            alt.Tooltip("id:Q", title="Event ID"),
            alt.Tooltip("minute:Q", title="Minute"),
            alt.Tooltip("team:N", title="Team"),
            alt.Tooltip("player:N", title="Player"),
            alt.Tooltip("type:N", title="Event"),
            alt.Tooltip("outcome:N", title="Outcome"),
        ]

        if recent_rows:
            recent_df = pd.DataFrame(recent_rows)
            history_df = recent_df[
                recent_df["id"] != (
                    current["id"] if current else -1
                )
            ]

            if not history_df.empty:
                history_points = alt.Chart(history_df).mark_circle(
                    size=100,
                    stroke="white",
                    strokeWidth=1,
                ).encode(
                    x=alt.X(
                        "x:Q",
                        scale=alt.Scale(domain=[0, 105]),
                        axis=None,
                    ),
                    y=alt.Y(
                        "y:Q",
                        scale=alt.Scale(domain=[68, 0]),
                        axis=None,
                    ),
                    color=alt.Color("team:N", scale=team_scale),
                    tooltip=tooltip,
                )
                pitch_chart = pitch_chart + history_points

            if current and current["id"] in recent_df["id"].values:
                current_df = recent_df[
                    recent_df["id"] == current["id"]
                ]

                current_point = alt.Chart(current_df).mark_point(
                    shape="star",
                    size=280,
                    filled=True,
                    color="#f59e0b",
                    stroke="white",
                    strokeWidth=1,
                ).encode(
                    x=alt.X(
                        "x:Q",
                        scale=alt.Scale(domain=[0, 105]),
                        axis=None,
                    ),
                    y=alt.Y(
                        "y:Q",
                        scale=alt.Scale(domain=[68, 0]),
                        axis=None,
                    ),
                    tooltip=tooltip,
                )
                pitch_chart = pitch_chart + current_point

        st.altair_chart(
            pitch_chart.properties(height=330),
            width="stretch",
        )

    with detail_col:
        st.markdown("### Event details")

        if current:
            st.write(f"**Player:** {current['player']}")
            st.write(f"**Team:** {current['team']}")
            st.write(f"**Event:** {current['type']}")
            st.write(f"**Outcome:** {current['outcome']}")
            st.write(f"**Pressure label:** {current['pressure']}")
            st.write(f"**Possession:** {current['possession_id']}")
            st.caption(
                "Pressure and possession data are synthetic."
            )
        else:
            st.write("Move to the first event to inspect its details.")

        st.markdown("### Agent status")

        for step in replay_result["steps"]:
            marker = (
                "✅"
                if step["status"] in {"completed", "passed"}
                else "❌"
            )
            st.write(f"{marker} **{step['agent']}**")
            st.caption(step["status"].title())

    st.markdown("### Event timeline")

    timeline_rows = []
    for index, event in enumerate(replay_events, start=1):
        if index < cursor:
            state = "Revealed"
        elif index == cursor and cursor > 0:
            state = "Current"
        else:
            state = "Upcoming"

        offset = ((index % 3) - 1) * 0.12
        timeline_rows.append({
            "Minute": event["minute"],
            "Plot minute": max(
                0,
                min(90, event["minute"] + offset),
            ),
            "Team": event["team"],
            "Player": event["player"],
            "Event ID": event["id"],
            "Type": event["type"],
            "Outcome": event["outcome"],
            "State": state,
        })

    timeline_df = pd.DataFrame(timeline_rows)

    if not timeline_df.empty:
        timeline_chart = alt.Chart(timeline_df).mark_circle(
            size=100,
            filled=True,
        ).encode(
            x=alt.X(
                "Plot minute:Q",
                scale=alt.Scale(domain=[0, 90]),
                axis=alt.Axis(title="Match minute", tickCount=10),
            ),
            y=alt.Y("Team:N", sort=[home, away], title=None),
            color=alt.Color(
                "State:N",
                scale=alt.Scale(
                    domain=["Revealed", "Current", "Upcoming"],
                    range=["#10a878", "#f59e0b", "#cbd5e1"],
                ),
            ),
            tooltip=[
                alt.Tooltip("Minute:Q"),
                alt.Tooltip("Event ID:Q"),
                alt.Tooltip("Team:N"),
                alt.Tooltip("Player:N"),
                alt.Tooltip("Type:N"),
                alt.Tooltip("Outcome:N"),
                alt.Tooltip("State:N"),
            ],
        ).properties(height=140)

        st.altair_chart(timeline_chart, width="stretch")

    st.markdown("### Insights at this replay position")

    if not replay_verification["passed"]:
        st.error("Replay evidence verification failed.")
        st.write(replay_verification["errors"])
    elif replay_insights:
        st.success(
            f"Evidence verification passed: "
            f"{replay_verification['checks_passed']}/"
            f"{replay_verification['checks_total']} checks."
        )

        for insight in replay_insights:
            with st.container(border=True):
                st.markdown(f"**{insight['title']}**")
                st.write(insight["summary"])
                st.caption(
                    "Evidence event IDs: "
                    + ", ".join(
                        map(str, insight["evidence_event_ids"])
                    )
                )

                with st.expander("Why it matters and limitations"):
                    st.write(insight["why_it_matters"])
                    st.write(insight["limitation"])
    else:
        st.info(
            "No qualifying attacking sequence has been completed yet. "
            "Advance the replay to discover one."
        )

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
