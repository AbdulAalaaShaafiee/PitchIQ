# PitchIQ Real-Match Explorer — StatsBomb Open Data

This add-on creates a **Real-Match Explorer** Streamlit page, plus a deterministic StatsBomb Open Data discovery/import module. It does not replace PitchIQ's current agents, event schema, or analysis engine.

## What it does

1. Loads the public competition/season catalogue from the official Hudl StatsBomb Open Data repository.
2. Lets the user filter selected historical matches by team.
3. Downloads the selected match's event JSON and converts supported actions into the existing `parse_uploaded_match` format.
4. Scales StatsBomb event coordinates from 120×80 to PitchIQ's 105×68 pitch.
5. Passes the imported match into `analyze_match` and attempts to invoke the existing `PitchIQOrchestrator` for fan/analyst narrative.
6. Displays the source result alongside the score calculated from imported goal events and warns if they differ.
7. Shows which events were skipped and preserves source IDs through the existing importer's evidence-reference handling.

## Important scope limits

- StatsBomb Open Data is a selection of historical competitions/seasons, not a complete catalogue of all matches and not a live data feed.
- The converter only imports event/outcome pairs that the current PitchIQ schema can represent. Unsupported records are skipped with warnings rather than being mislabeled.
- StatsBomb's boolean `under_pressure` field is not converted into PitchIQ's low/medium/high pressure label.
- No missing event coordinates, possession IDs, tactical phases, expected goals (xG), player ratings, or predictions are invented.
- Source result and event-derived score are displayed separately so incomplete event coverage cannot silently masquerade as a confirmed score.
- The current code fetches JSON from GitHub raw content and uses an in-process cache. Internet access is required.

## Data attribution

StatsBomb's Open Data repository states that published/shared research, analysis, or insights based on its data should identify StatsBomb as the source and use the logo available from the official media pack.

- Open data repository: https://github.com/hudl/open-data
- Attribution/logo media pack: https://statsbomb.com/media-pack/

## Files added

- `pitchiq/statsbomb.py`
- `pitchiq/pages/2_Real_Match_Explorer.py`
- `tests/test_statsbomb.py`

No new Python dependencies are required.
