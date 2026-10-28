# PitchIQ Figma-reference UI (additive integration)

This bundle adds a browser-based UI based on the supplied PitchIQ design-board screenshot. It is deliberately additive: it does **not** edit or replace `pitchiq/dashboard.py`, the current data model, the three-agent workflow, or the analysis/verifier code.

## Install into your existing checkout

1. Extract this bundle to its own folder, for example `C:\Users\USER\Downloads\PitchIQ_Figma_Integration_Pack`.
2. Open PowerShell and run the following, adjusting the bundle path if needed:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
Set-Location "$env:USERPROFILE\Downloads\PitchIQ_Figma_Integration_Pack"
.\INSTALL_PITCHIQ_UI.ps1 -ProjectRoot "$env:USERPROFILE\Downloads\PitchIQ"
```

The installer confirms it is pointed at a Git checkout, creates any missing folders, backs up a same-named destination before replacing it, and copies only the added integration files. It does not touch `pitchiq/dashboard.py`, `pitchiq/main.py`, `pitchiq/agents.py`, `pitchiq/insights.py`, `pitchiq/importers.py`, or the existing Streamlit config.

## Launch the new UI

The install script copies these new paths into the existing project:

- `pitchiq/webapp.py`
- `webui/index.html`
- `tests/test_webapp.py`
- `run_pitchiq_ui.ps1`
- `FIGMA_UI_INTEGRATION_README.md`
- `FIGMA_UI_DESIGN_MAPPING.md`

Then, in a separate PowerShell window (the Streamlit dashboard can remain running), run:

```powershell
Set-Location "$env:USERPROFILE\Downloads\PitchIQ"
.\run_pitchiq_ui.ps1
```

Open `http://127.0.0.1:8765`. To stop this new UI, press `Ctrl+C` in that window. The original Streamlit dashboard still runs as before, normally at `http://localhost:8501`.

## What is connected

- `load_match()` for the bundled synthetic demo.
- `analyze_match()` for match statistics and supported event-sequence rules.
- `PitchIQOrchestrator` for Event Analysis, Storytelling, and Evidence Verification agents and the real handoff/check state.
- Evidence-grounded Match Assistant Q&A, served by `/api/assistant`; answers cite existing event IDs and explicitly declines unsupported predictive metrics.
- `parse_uploaded_match()` and the existing CSV template for structured CSV/JSON event uploads.
- Existing optional local Gemma storytelling setting (`PITCHIQ_USE_LOCAL_AI=1`) remains respected when set in the PowerShell process that launches the server.

## Data truthfulness

The provided design includes places for metrics such as possession, xG, pressing intensity, and other provider-derived measures. The current PitchIQ engine does not calculate validated values for those metrics. Those visual slots are retained but show unavailable/not calculated states rather than invented statistics. Missing coordinates remain missing; pitch-event markers and pass paths appear only when source events contain the required coordinates. A player-to-player passing network is not claimed because the current event schema has no receiver identity field.

## Validation

After installing, from the PitchIQ project root with `.venv` activated, run:

```powershell
python -m unittest discover -s tests -v
git diff --check
git status --short
```

The previous 29-test baseline should remain, with five assistant-response tests and two UI coverage tests in this revision (36 total). Run the suite locally to confirm the actual result. Do not commit or push until you have reviewed the result and confirmed the UI works locally.

## Safety and rollback

This bundle adds files only. It does not touch your current Streamlit dashboard or modify the Figma file. The installer saves any same-named files it needs to replace under `%TEMP%\PitchIQ-Figma-UI-backup-*`. To roll back, stop the new server and remove the added paths listed above; restore a backed-up path if the installer reported a collision. Keep the original Streamlit app available as a fallback throughout review.

## Visual fidelity note

The UI follows the supplied composite reference: dark navy shell, compact header, teal active navigation, match strip, compact KPI cards, three-column intelligence workspace, pitch visualization, activity timeline, agent mission-control panel, tactics view, story view, and responsive mobile stacking. The attachment is a composite preview rather than an inspectable Figma layer export, so exact font names, numeric spacing tokens, and every tiny component label cannot be extracted from it; the original Figma document itself is not modified.
