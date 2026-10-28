import unittest

from pitchiq.world_cup_demo import (
    FINAL_VIDEO_ID,
    FINAL_VIDEO_URL,
    FIFA_REPORT_URL,
    build_world_cup_final_html,
    get_key_moments,
    parse_youtube_video_id,
)


class TestWorldCupFinalDemo(unittest.TestCase):
    def test_official_video_link_is_recognized(self):
        self.assertEqual(parse_youtube_video_id(FINAL_VIDEO_URL), FINAL_VIDEO_ID)
        self.assertEqual(parse_youtube_video_id("https://youtu.be/6HaHNYjnghE"), FINAL_VIDEO_ID)
        self.assertEqual(parse_youtube_video_id("https://example.com/watch?v=6HaHNYjnghE"), None)

    def test_curated_moments_are_source_grounded(self):
        moments = get_key_moments()
        self.assertEqual(len(moments), 3)
        self.assertIn("FIFA's final report", moments[0]["explanation"])
        self.assertIn("106th minute", moments[1]["explanation"])
        self.assertIn("1–0", moments[2]["explanation"])

    def test_video_moments_are_explicitly_manually_mapped(self):
        html = build_world_cup_final_html()
        self.assertIn("Map current video time", html)
        self.assertIn("highlights video", html.lower())
        self.assertIn("Match minutes are kept separate from video seconds", html)
        self.assertIn("STORAGE_KEY", html)

    def test_player_uses_official_youtube_iframe_api(self):
        html = build_world_cup_final_html()
        self.assertIn("https://www.youtube.com/iframe_api", html)
        self.assertIn(FINAL_VIDEO_ID, html)
        self.assertIn("getCurrentTime()", html)
        self.assertIn("seekTo(value,true)", html)

    def test_fifa_report_link_is_present(self):
        html = build_world_cup_final_html()
        self.assertIn(FIFA_REPORT_URL, html)
        self.assertIn("This highlights timeline is not a complete event-by-event feed", html)


if __name__ == "__main__":
    unittest.main()
