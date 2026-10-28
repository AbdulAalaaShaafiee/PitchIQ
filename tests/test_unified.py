"""Contract tests for the single-origin Basic/Advanced PitchIQ router."""
from pathlib import Path
import unittest

from pitchiq.unified import (
    ADVANCED_PORT,
    BASIC_PORT,
    basic_mode_shell,
    BASIC_PREFIX,
    UNIFIED_PORT,
    make_application,
    upstream_url,
    upstream_websocket_url,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class TestPitchIQUnifiedModes(unittest.TestCase):
    def test_basic_and_advanced_route_to_the_expected_services(self):
        self.assertEqual(
            upstream_url("basic", "/basic/_stcore/health?x=1"),
            f"http://127.0.0.1:{BASIC_PORT}/basic/_stcore/health?x=1",
        )
        self.assertEqual(
            upstream_url("advanced", "/api/demo"),
            f"http://127.0.0.1:{ADVANCED_PORT}/api/demo",
        )
        with self.assertRaises(ValueError):
            upstream_url("other", "/")

    def test_streamlit_websocket_keeps_basic_prefix(self):
        self.assertEqual(
            upstream_websocket_url("/basic/_stcore/stream?session=1"),
            f"ws://127.0.0.1:{BASIC_PORT}/basic/_stcore/stream?session=1",
        )
        with self.assertRaises(ValueError):
            upstream_websocket_url("/not-basic/_stcore/stream")

    def test_websocket_route_is_registered_before_basic_http_proxy(self):
        app = make_application()
        rules = [rule.matcher.regex.pattern for rule in app.wildcard_router.rules]
        ws_index = next(i for i, rule in enumerate(rules) if "_stcore/stream" in rule)
        basic_index = next(i for i, rule in enumerate(rules) if "basic" in rule and "stcore" not in rule)
        self.assertLess(ws_index, basic_index)
        self.assertEqual(UNIFIED_PORT, 8765)
        self.assertTrue(any("__unified/health" in rule for rule in rules))

    def test_basic_mode_shell_uses_direct_streamlit_for_websocket(self):
        shell = basic_mode_shell()
        self.assertIn(f'src="http://127.0.0.1:{BASIC_PORT}/basic/?embed=true"', shell)
        self.assertIn('href="/"', shell)
        self.assertIn('title="PitchIQ Basic Mode — Streamlit dashboard"', shell)

    def test_advanced_ui_has_basic_mode_switch_and_floating_hud(self):
        html = (PROJECT_ROOT / "webui" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/basic/"', html)
        self.assertIn('title="Switch to Basic Mode (Streamlit)"', html)
        self.assertIn('id="floatingAiHud"', html)
        self.assertIn('id="hudLauncher"', html)

    def test_basic_sidebar_has_advanced_mode_switch(self):
        dashboard = (PROJECT_ROOT / "pitchiq" / "dashboard.py").read_text(encoding="utf-8")
        self.assertIn('st.link_button("↗ Advanced Mode", "http://127.0.0.1:8765/"', dashboard)

    def test_launcher_uses_the_unified_entrypoint(self):
        launcher = (PROJECT_ROOT / "run_pitchiq_ui.ps1").read_text(encoding="utf-8")
        self.assertIn("-m pitchiq.unified", launcher)


if __name__ == "__main__":
    unittest.main()
