# PitchIQ Floating AI HUD update

This additive update adds a persistent floating PitchIQ AI assistant overlay to the Figma-inspired local browser UI.

## What it adds
- Floating cyan AI orb and launcher available across Home, Analysis, and Match Stories.
- Expand/collapse panel, close/minimize buttons, Escape-key support, and keyboard focus handling.
- A source-grounded conversation transcript, suggested questions, and a message composer.
- Shared chat history with the existing Home-page assistant.
- The same local `/api/assistant` endpoint and recorded event IDs; no separate invented model output.
- Responsive positioning above mobile bottom navigation, touch-friendly controls, and reduced-motion support.

## Install
Run `INSTALL_FLOATING_AI_HUD.ps1` from this package after extracting it, passing your existing PitchIQ project path. The updater backs up the files it replaces under `%TEMP%` first.

## Validate
From the PitchIQ project root, with `.venv` active:

```powershell
python -m unittest discover -s tests -v
git diff --check
```

The suite target is now 38 tests (36 previous tests plus two HUD static-contract tests). This UI still deliberately declines unsupported xG, possession, pressing intensity, and goal probabilities.

No Figma file or original Streamlit dashboard is modified by this update.
