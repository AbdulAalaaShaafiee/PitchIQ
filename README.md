# PitchIQ | Local-First Football Match Intelligence

PitchIQ is a local-first football match-intelligence prototype. It includes a synthetic demo match and can import supported CSV/JSON event logs to calculate evidence-linked match statistics and selected attacking sequences through an interactive Streamlit dashboard.

PitchIQ combines deterministic match analysis and evidence verification with **optional local AI storytelling** using Gemma 4 through Ollama and Microsoft Agent Framework. It does not require a paid AI API for local inference.

> **Prototype notice:** The bundled demo dataset is synthetic. Uploaded event files are analyzed only from the fields they actually contain; PitchIQ does not currently analyze match video, ingest live feeds, calculate validated xG/goal probabilities, or guarantee calibrated player tracking.

## Features

- **Match analysis:** Calculates the score, shots, passing accuracy, and tackles won from structured event records.
- **CSV/JSON import:** Upload an event-level match file, review source-data warnings, and analyze the imported match without replacing the bundled demo.
- **Attacking-sequence detection:** Uses explicit rules to identify selected completed-pass sequences ending in a shot or goal.
- **Audience-specific insights:** Supports fan-friendly and analyst-focused narratives.
- **Optional local AI storytelling:** Uses the local `gemma4:e2b-it-q4_K_M` model through Ollama and Microsoft Agent Framework to create additional commentary.
- **Deterministic fallback:** AI is opt-in. When local AI is not enabled or usable, PitchIQ retains its deterministic narratives.
- **Evidence verification:** Checks event references, attacking-sequence consistency, team and minute metadata, audience mode, and narrative consistency before insights are trusted by the workflow.
- **Interactive dashboard:** Displays match statistics, team comparisons, an attacking-sequence timeline, match replay, supporting events, agent handoffs, verification results, and a searchable event explorer.
- **Automated tests:** Covers analysis, agent orchestration, verification failure cases, and local-storytelling validation.

## Technology

- Python 3.13 recommended
- Streamlit
- Pandas and Altair
- Microsoft Agent Framework with its Ollama connector
- Ollama with Gemma 4 (`gemma4:e2b-it-q4_K_M`)
- Python `unittest`

## Project structure

```text
PitchIQ/
├── .streamlit/
│   └── config.toml
├── data/
│   └── events.json                 # Synthetic match event dataset
├── pitchiq/
│   ├── __init__.py
│   ├── agents.py                   # Agent orchestration and evidence verification
│   ├── dashboard.py                # Streamlit dashboard
│   ├── insights.py                 # Deterministic audience-specific insights
│   ├── importers.py                 # CSV/JSON event import and normalization
│   ├── local_storytelling.py       # Optional local Gemma commentary and validation
│   └── main.py                     # Data loading, analysis, and CLI
├── tests/
│   ├── __init__.py
│   ├── test_agents.py
│   ├── test_analysis.py
│   ├── test_local_storytelling.py
│   └── test_importers.py             # CSV/JSON import and validation tests
├── requirements.txt
├── README.md
└── .gitignore
```

## Requirements

- Windows and PowerShell (commands below use PowerShell)
- Python 3.13 recommended
- Internet access to install Python packages and download the model
- Ollama for local AI storytelling; the dashboard can run without enabling AI
- Enough disk space and RAM to run the selected local model. Inference performance depends on the machine.

## Install the project

Run these commands from the project root, `C:\Users\USER\Downloads\PitchIQ` in the example below.

Create and activate a virtual environment:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install Python dependencies. The Ollama connector is pinned to a prerelease version, so include `--pre`:

```powershell
python -m pip install --pre -r requirements.txt
```

## Run without local AI

With the virtual environment active and your current directory at the project root, run:

```powershell
python -m streamlit run .\pitchiq\dashboard.py
```

Open the local URL Streamlit prints, normally `http://localhost:8501`.

### Import event-level match data

Use the sidebar's **Upload event log** control to select a `.csv` or `.json` file. A downloadable CSV template is provided in the app. JSON files should contain `match_id`, `home_team`, `away_team`, and an `events` array. CSV files need `minute`, `team`, `type`, and `outcome`; `player`, `id`, `period`, `possession_id`, `phase`, `pressure`, `x`, `y`, `end_x`, `end_y`, `home_team`, `away_team`, and `match_id` are supported optional columns. Common event/column aliases are normalized where unambiguous.

Event types and outcomes must map to PitchIQ's supported vocabulary (`pass`, `shot`, `goal`, `tackle`, `carry`, `interception`, `recovery`, `clearance`, `foul`, `pressure`, `duel` and their supported outcomes). Pitch coordinates, when supplied, must use a 105 × 68 scale. Missing values are left unspecified: without consistent possession IDs, PitchIQ withholds possession-based attacking-sequence claims; without coordinates, it does not plot event markers. If home/away labels are absent, the app infers orientation from first appearance and warns you to verify it.

This import path handles structured **event logs**, not match videos or arbitrary screenshot/stat-summary files. Its outputs depend on the source's completeness and vocabulary; it does not infer missing tracking data or calculate xG/goal probabilities.

Local AI is opt-in. If `PITCHIQ_USE_LOCAL_AI` is not set to `1`, PitchIQ uses its deterministic narrative path by default.

## Enable local Gemma 4 storytelling

### 1. Install and verify Ollama

Install Ollama for your operating system from the official website: <https://ollama.com/download>.

Make sure Ollama is running. In PowerShell, check that the CLI is available:

```powershell
ollama --version
```

### 2. Download the configured model

```powershell
ollama pull gemma4:e2b-it-q4_K_M
ollama list
```

The model should appear in the output of `ollama list` when the pull completes.

### 3. Enable local AI and launch the dashboard

In the **same PowerShell window** where you launch Streamlit, activate `.venv`, move to the project root, set the environment variable, and start the app:

```powershell
Set-Location "C:\Users\USER\Downloads\PitchIQ"
.\.venv\Scripts\Activate.ps1
$env:PITCHIQ_USE_LOCAL_AI = "1"
python -m streamlit run .\pitchiq\dashboard.py
```

The environment variable applies to that PowerShell session. If you open a new terminal, set it again before launching the app. To return to deterministic mode in the current session, run:

```powershell
Remove-Item Env:PITCHIQ_USE_LOCAL_AI -ErrorAction SilentlyContinue
```

### Local AI behavior and safeguards

- The match-analysis engine remains deterministic; Gemma is used for optional storytelling, not to calculate the score or match statistics.
- The existing evidence-backed narrative fields and event IDs remain available separately from generated commentary.
- Generated commentary is subjected to the local storytelling validation rules; the code includes checks intended to reject unsupported numeric claims.
- If local AI is disabled or commentary cannot be used, the deterministic narrative path remains the fallback.
- Model output is not guaranteed to be factually correct merely because the model runs locally. Review AI commentary, and rely on the recorded events and verification results for the demonstrator's structured facts.

## Run the command-line application

Fan-friendly insights:

```powershell
python -m pitchiq.main --audience fan
```

Analyst-focused insights:

```powershell
python -m pitchiq.main --audience analyst
```

## Run the tests

From the project root, with `.venv` activated:

```powershell
python -m unittest discover -s tests -v
```

The current verified development baseline is **25 passing tests**. Run the suite after code changes.

## Agent workflow

### 1. Event Analysis Agent

Runs the deterministic match-analysis engine and identifies attacking sequences that match the configured rules.

### 2. Storytelling Agent

Produces fan-friendly or analyst-focused content. By default it uses the deterministic narrative generator. When `PITCHIQ_USE_LOCAL_AI=1`, the optional local Gemma storytelling path can add commentary, subject to the configured validation and fallback behavior.

### 3. Evidence Verification Agent

Checks evidence IDs, sequence consistency, event chronology, metadata, requested audience, and deterministic narrative consistency. The demo workflow reports the check results; insights should not be relied on when verification fails.

## Current limitations

- The match events are synthetic and do not represent a verified real-world fixture.
- The prototype does not ingest live match feeds or calibrated player tracking.
- Attacking-sequence detection uses transparent demonstration rules, not a validated tactical model.
- Synthetic coordinates and pressure labels are not calibrated tracking measurements.
- The project does not calculate validated expected goals/goal probabilities, analyze raw match video, or prove tactical causation.
- Passing verification confirms consistency with the current rules and data; it does not prove that synthetic events reflect real football.
- Local model responses can vary and may be slow on hardware with limited memory. AI commentary is supplementary to the recorded facts, not a replacement for them.
- This prototype is not intended for consequential coaching, betting, scouting, or other high-stakes decisions.

## Development principles

PitchIQ emphasizes local execution, explainable rules, traceable evidence, explicit limitations, and automated tests. Improvements should preserve those principles while expanding the analytical capabilities and user experience.

## License

No license has been declared yet. Add a license before distributing the project for reuse.
