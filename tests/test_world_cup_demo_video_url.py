import inspect
import unittest

from pitchiq.world_cup_demo import (
    FINAL_VIDEO_ID,
    build_world_cup_final_html,
    parse_youtube_video_id,
    render_world_cup_final_demo,
)


class TestWorldCupDemoYouTubeInput(unittest.TestCase):
    def test_accepts_common_youtube_link_formats(self):
        video_id = "dQw4w9WgXcQ"
        urls = [
            f"https://www.youtube.com/watch?v={video_id}",
            f"https://youtu.be/{video_id}?t=42",
            f"https://www.youtube.com/shorts/{video_id}",
            f"https://www.youtube.com/live/{video_id}",
            f"https://www.youtube.com/embed/{video_id}",
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(parse_youtube_video_id(url), video_id)

    def test_rejects_non_youtube_or_malformed_urls(self):
        self.assertIsNone(parse_youtube_video_id("https://example.com/watch?v=dQw4w9WgXcQ"))
        self.assertIsNone(parse_youtube_video_id("https://youtube.com/watch?v=short"))
        self.assertIsNone(parse_youtube_video_id("not a url"))
        self.assertIsNone(parse_youtube_video_id(""))

    def test_custom_video_id_is_used_by_player(self):
        custom_id = "dQw4w9WgXcQ"
        html = build_world_cup_final_html(custom_id)
        self.assertIn(f'const VIDEO_ID = "{custom_id}";', html)
        self.assertIn("https://www.youtube.com/watch?v='+VIDEO_ID", html)

    def test_video_mappings_are_isolated_per_video(self):
        html = build_world_cup_final_html("dQw4w9WgXcQ")
        self.assertIn("'pitchiq-world-cup-2026-final-moment-offsets-v1-' + VIDEO_ID", html)

    def test_page_exposes_url_input_and_explains_embed_restrictions(self):
        page_source = inspect.getsource(render_world_cup_final_demo)
        self.assertIn('"YouTube video link"', page_source)
        self.assertIn('"Load YouTube video"', page_source)
        self.assertIn("parse_youtube_video_id(entered_url)", page_source)
        self.assertIn("cannot override that restriction", page_source)
        self.assertIn("For another ", page_source)


if __name__ == "__main__":
    unittest.main()
