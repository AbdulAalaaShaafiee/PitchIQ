# Figma reference → PitchIQ functionality map

This documents how the provided screenshot's visible screens are represented in the additive web UI. These screens are implemented as application views rather than separate hard-coded demo pages; their content comes from the current PitchIQ match and agents.

| Visible design frame | UI implementation | Existing PitchIQ source |
|---|---|---|
| AI-powered match intelligence | Home: match strip, top metric cards, Match Storyteller, Explainable Tactics pitch, Agent Mission Control, timeline, team comparison and player event counts | `load_match`, `analyze_match`, `PitchIQOrchestrator`, `generate_insights` |
| Explainable tactics | Analysis: selectable event/shot/pass view, replay slider, spatial pitch, source-coverage summary, passing flow, team comparison, player event counts and evidence checklist | Match events, coordinates, team stats, `report.attacking_sequences`, `verification.checks` |
| Every match has a story | Match Stories: event activity timeline, evidence-backed narratives, recorded-goal moments, supporting event IDs and narrative-agent state | `insights`, `report`, `match.events`, agent steps/handoffs |
| Mobile mockups | Responsive single-column layout, reduced top navigation, compact score/KPIs, touch-friendly cards and fixed mobile navigation | Same live analysis payload, no second or divergent mobile dataset |
| Component/token board | The colors, borders, compact uppercase labels, panel cards, buttons, badges, metric tiles, status states, event markers and typography hierarchy are applied as shared CSS tokens/components | Shared design styles across the three application views |

## Existing behavior kept intact

- The original Streamlit dashboard remains at `pitchiq/dashboard.py` and continues to be runnable.
- The three current agents and both handoffs run through `PitchIQOrchestrator`; results shown in the new UI are not hard-coded.
- The CSV and JSON imports use `parse_uploaded_match`; the existing CSV template is served by the UI.
- The existing verification result is rendered, including failing checks if any occur.
- Local Gemma storytelling continues to follow the existing `PITCHIQ_USE_LOCAL_AI` environment setting and validation/fallback logic.
- The exported JSON report includes the actual match events, analysis report, insights, verification checks, agent steps and handoffs.

## Unavailable metrics remain visibly unavailable

Possession, expected goals (xG), and calibrated pressing intensity occupy their designed KPI positions on Home/Match Stories, but are labeled `N/A` because the current engine does not calculate them from the current event schema. The Analysis view foregrounds supported statistics. This preserves the visual hierarchy without presenting invented statistics as facts.

The spatial passing diagram is based on recorded pass start/end coordinates. Because the current schema does not include pass-receiver identities, it is not described as a verified player-to-player network. Missing coordinates remain missing.

## Fidelity boundary

The supplied attachment is a composite view of multiple Figma frames and a component board, not a structured Figma export with editable layer coordinates, text styles, and assets. This implementation follows the visible composition and shared visual language; exact font-token values, original component names, and pixel-level geometry must be confirmed against the Figma file itself when layer inspection/export is available. No edits are made to the user's Figma file.


## Completeness revision

- Added a functional, event-grounded assistant composer, suggested questions, server endpoint, and event-ID evidence chips.
- Added the Next goal probability panel in the reference position. The predictive value is explicitly `N/A`; the chart below it reports actual shot/goal event activity, not probability.
- Added a structured “Why the outcome matters” evidence panel using the real detected sequence and finish event.
- Reworked Analysis to a left scope rail, central spatial pitch, and right probability/evidence stack; retained passing network, team comparison, player intelligence, and verification below.
- Expanded player intelligence into event-derived shots, passes, tackles won, goals, and total event counts. No ratings are inferred.
- Reworked Match Stories into a full-width event rhythm, live narrative, pitch replay, recorded breakthrough, “One moment. Three connected decisions” evidence chain, agent state, and event explorer.
