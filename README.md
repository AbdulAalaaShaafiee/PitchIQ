# PitchIQ | Synthetic Match Intelligence

PitchIQ is a local-first football match intelligence prototype
that turns synthetic match events into explainable statistics
and audience-specific narratives.

## Current Features

- Validates synthetic football event data.
- Calculates scores, shots, passing accuracy, and tackles won.
- Detects simple attacking sequences using explicit rules.
- Generates fan-friendly and analyst-focused narratives.
- Connects three deterministic specialist agents through shared state.
- Verifies event references, sequence mappings, and narrative metadata.
- Includes automated tests for analysis and orchestration.

## Project Structure

- `data/events.json` — synthetic demonstration match.
- `pitchiq/main.py` — event validation, analysis, and command-line interface.
- `pitchiq/insights.py` — personalized insight generation.
- `pitchiq/agents.py` — agent orchestration and evidence verification.
- `tests/` — automated tests.

## Requirements

- Python 3.13 or a compatible Python 3 version.
- PowerShell on Windows.

## Setup

Create a virtual environment:

```powershell
python -m venv .venv