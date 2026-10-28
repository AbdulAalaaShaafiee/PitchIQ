import unittest

from pitchiq.world_cup_demo import build_world_cup_final_html


class TestWorldCupEmbedFallback(unittest.TestCase):
    def test_manual_fallback_explains_youtube_embed_restriction(self):
        html = build_world_cup_final_html()
        self.assertIn('YouTube allows playback on its site, but blocks embedding here.', html)
        self.assertIn('manual timestamp mode is ready', html.lower())

    def test_timestamp_input_accepts_common_clip_time_formats(self):
        html = build_world_cup_final_html()
        self.assertIn('id="manualVideoTime"', html)
        self.assertIn('MM:SS or seconds', html)
        self.assertIn('function parseManualSeconds()', html)

    def test_embed_error_150_and_101_switch_to_manual_fallback(self):
        html = build_world_cup_final_html()
        self.assertIn('errorCode===101||errorCode===150', html)
        self.assertIn('enableManualFallback(e.data)', html)

    def test_map_and_jump_buttons_support_manual_mode(self):
        html = build_world_cup_final_html()
        self.assertIn('(playerReady||manualMode)', html)
        self.assertIn("if(manualMode){manualTimeNode.value=secLabel(value)", html)
        self.assertIn('PitchIQ cannot control that separate player.', html)

    def test_manual_preview_explains_external_player_cannot_auto_sync(self):
        html = build_world_cup_final_html()
        self.assertIn('browser cannot read its playback clock', html)
        self.assertIn('does not seek or control the separate YouTube tab', html)
        self.assertIn('previewExternalTime', html)


if __name__ == "__main__":
    unittest.main()
