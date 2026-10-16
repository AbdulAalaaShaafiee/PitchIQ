# PitchIQ | Synthetic Match Intelligence

PitchIQ is a local-first football match intelligence prototype that converts synthetic match events into statistics, attacking-sequence insights, and evidence-linked narratives.

It demonstrates how specialist software agents can work together to analyze match events, communicate findings for different audiences, and verify generated insights before displaying them.

> **Prototype notice:** This project currently uses synthetic demonstration data and deterministic Python agents. It does not yet use LLM-powered agents or real match-tracking data.

## Features

- **Match analysis:** Calculates scores, shots, passing accuracy, and tackles won.
- **Attacking-sequence detection:** Identifies selected passing sequences that lead to a shot or goal using explicit rules.
- **Audience-specific insights:** Generates fan-friendly and analyst-focused narratives.
- **Multi-agent workflow:** Coordinates event analysis, storytelling, and evidence verification.
- **Evidence verification:** Checks event references, sequence consistency, team and minute metadata, audience mode, and narrative consistency.
- **Interactive dashboard:** Displays match statistics, comparison charts, an attacking-sequence timeline, supporting evidence, agent handoffs, and event records.
- **Event explorer:** Filters synthetic events by team and event type and searches by player or event ID.
- **Automated tests:** Covers match analysis, agent orchestration, and evidence-verification failure cases.

## Technology

- Python 3.13
- Streamlit
- Pandas
- Altair
- Python `unittest`

The application runs locally and does not require a paid AI API.

## Project Structure

```text
PitchIQ/
├── data/
│   └── events.json          # Synthetic match dataset
├── pitchiq/
│   ├── __init__.py
│   ├── agents.py            # Agent orchestration and verification
│   ├── dashboard.py         # Streamlit web dashboard
│   ├── insights.py          # Audience-specific insight generation
│   └── main.py              # Validation, analysis, and CLI
├── tests/
│   ├── __init__.py
│   ├── test_agents.py       # Agent and verifier tests
│   └── test_analysis.py     # Match-analysis tests
├── requirements.txt
├── README.md
└── .gitignore
```

## Requirements

- Windows with PowerShell, or another environment that supports Python.
- Python 3.13 recommended.
- Internet access for initial package installation.

## Installation

Open a terminal in the project root.

Create a virtual environment:

```powershell
py -3.13 -m venv .venv
```

Activate it in PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run the Dashboard

From the project root, with the virtual environment activated:

```powershell
python -m streamlit run pitchiq/dashboard.py
```

Streamlit will display a local URL in the terminal, normally:

```text
http://localhost:8501
```

Open that address in your browser.

The dashboard includes:

- Match overview and team statistics.
- Visual comparisons and an attacking-sequence timeline.
- Fan and analyst insights.
- Supporting event records and evidence IDs.
- Agent execution and verification results.
- A searchable and filterable event explorer.

## Run the Command-Line Application

Fan-friendly insights:

```powershell
python -m pitchiq.main --audience fan
```

Analyst-focused insights:

```powershell
python -m pitchiq.main --audience analyst
```

## Run the Tests

Execute the complete automated test suite:

```powershell
python -m unittest discover -s tests -v
```

The current development baseline is **17 passing tests**. Run the suite after code changes to confirm the application still behaves as expected.

## How the Agent Workflow Works

### 1. Event Analysis Agent

Runs the existing deterministic match-analysis engine and identifies attacking sequences that match the configured rules.

### 2. Storytelling Agent

Converts detected sequences into fan-friendly or analyst-focused narratives with supporting event IDs and stated limitations.

### 3. Evidence Verification Agent

Checks that insights reference the detected sequences and that event records, metadata, and expected narrative content are consistent.

Insights should be withheld when evidence verification fails.

## Current Limitations

- All match events are synthetic and do not represent a verified real-world fixture.
- The three agents are deterministic Python components, not LLM-powered agents.
- Attacking-sequence detection uses transparent demonstration rules, not a validated tactical model.
- Synthetic coordinates and pressure labels are not calibrated player-tracking measurements.
- The project does not currently calculate validated expected goals or prove tactical causation.
- Passing verification confirms consistency with the current rules and templates; it does not establish that the synthetic dataset reflects real football.
- The application is a prototype and is not intended for live coaching, betting, scouting, or other consequential decisions.

## Development Philosophy

PitchIQ emphasizes local development, explainable rules, traceable evidence, explicit limitations, and automated tests. Future improvements should preserve these principles while expanding the analytical capabilities and user experience.

## License

No license has been declared yet. Add a license before distributing the project for reuse.
