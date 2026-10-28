# PitchIQ Unified Mode (Basic + Advanced)

This additive update puts both existing PitchIQ interfaces behind a single local website address:

- **Advanced Mode**: `http://127.0.0.1:8765/` — the Figma-inspired interface, advanced match screens, and floating AI HUD.
- **Basic Mode**: `http://127.0.0.1:8765/basic/` — the existing Streamlit dashboard.

Both views are local front ends to the same PitchIQ project and existing analysis/agent code. A Tornado reverse proxy sends Advanced UI/API requests to an internal service on `8766`, and Basic Mode HTTP/WebSocket traffic to Streamlit on `8501`. Those internal ports are private implementation details; open only `http://127.0.0.1:8765/` in the browser.

## Install

1. Stop any currently running PitchIQ servers by pressing `Ctrl+C` in their PowerShell windows. The unified launcher manages them together and requires local ports `8501`, `8765`, and `8766` to be free.
2. Extract this ZIP to `Downloads\PitchIQ_Unified_Mode_Update`.
3. In PowerShell run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
Set-Location "$env:USERPROFILE\Downloads\PitchIQ_Unified_Mode_Update"
.\INSTALL_UNIFIED_MODES.ps1 -ProjectRoot "$env:USERPROFILE\Downloads\PitchIQ"
```

The installer backs up files before replacing them. It updates the advanced HTML with a Basic Mode link, adds a small Advanced Mode link inside the Streamlit sidebar, installs the unified proxy module and launcher, and adds tests. It does not change the analysis engine, agent orchestration, importer, or Figma file.

## Run

From the PitchIQ project root:

```powershell
.\run_pitchiq_ui.ps1
```

The launcher uses the project's `.venv` Python automatically when present. It starts the local API, Streamlit, and the unified reverse proxy. Use one browser URL and switch modes with the navigation controls. Press `Ctrl+C` in that one PowerShell window to stop all services.

## Validate

```powershell
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
git diff --check
git status --short
```

The unified-mode update adds six routing/navigation contract tests on top of the current 38-test baseline (expected total: 44). Run them on the target Windows environment before committing. If the current local suite has a different baseline, investigate rather than treating the exact total as guaranteed.

## Notes and limits

- The two interfaces use the same analysis functions and evidence-verification pipeline. UI-specific state (for example, which file is currently selected in a Streamlit session versus uploaded in the Advanced UI) is not automatically merged between browser views in this revision.
- Unsupported xG, possession, calibrated player ratings, or goal probability values remain unavailable rather than fabricated.
- The server binds to loopback by default and is intended for local use. Do not expose it to a public network without adding authentication, CSRF/security review, and deployment-grade server configuration.
- The original Streamlit analysis interface is retained. A small navigation link is added to its sidebar; the advanced screen receives a Basic Mode link. A backup of the sidebar file is created before patching.
