"""Tests for the viral commentary bot and scraper modules."""
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from hub.scraper import ViralScraper, load_viral_config
from hub.commentary import generate_commentary_script, COMMENTARY_SCHEMA


class TestViralConfig(unittest.TestCase):
    def test_load_default_config(self):
        cfg = load_viral_config(Path("non_existent_config.json"))
        self.assertIn("queries", cfg)
        self.assertIsInstance(cfg["queries"], list)
        self.assertGreater(len(cfg["queries"]), 0)


class TestViralScraper(unittest.TestCase):
    def setUp(self):
        self.scraper = ViralScraper()

    def test_init_sets_cache_dir(self):
        self.assertTrue(self.scraper.cache_dir.exists())

    def test_ydl_opts_configured_correctly(self):
        opts = self.scraper._ydl_opts("test_tmpl", download=False)
        self.assertTrue(opts["extract_flat"])
        self.assertTrue(opts["quiet"])

    @patch.object(ViralScraper, "search_shorts")
    @patch.object(ViralScraper, "download_clip")
    def test_fetch_batch_language_queries(self, mock_dl, mock_search):
        mock_search.return_value = [{"title": "test", "url": "https://youtu.be/123"}]
        mock_dl.return_value = {"id": "123", "title": "test", "video_path": "test.mp4"}

        # Test MX queries
        res_mx = self.scraper.fetch_batch(count=1, language="mx")
        self.assertEqual(len(res_mx), 1)
        # Search query passed to search_shorts should come from queries_mx
        called_q = mock_search.call_args[0][0]
        mx_queries = self.scraper.cfg.get("queries_mx", [])
        self.assertIn(called_q, mx_queries)

    def test_duration_filter_skips_long_video(self):
        with patch("yt_dlp.YoutubeDL") as mock_ydl_cls:
            instance = mock_ydl_cls.return_value.__enter__.return_value
            instance.extract_info.return_value = {
                "id": "too_long",
                "title": "1 Hour Long Video",
                "duration": 3600,
            }
            res = self.scraper.download_clip("https://youtu.be/too_long")
            self.assertIsNone(res)


class TestFactoryIntegration(unittest.TestCase):
    @patch("hub.scraper.ViralScraper.fetch_batch")
    def test_us_fallback_when_no_clip(self, mock_fetch):
        mock_fetch.return_value = []
        from factories.us.main import make_viral_commentary
        res = make_viral_commentary({"voice": "en-US-AndrewMultilingualNeural"})
        self.assertIsNone(res)

    @patch("hub.scraper.ViralScraper.fetch_batch")
    def test_mx_fallback_when_no_clip(self, mock_fetch):
        mock_fetch.return_value = []
        from factories.mx.main import make_viral_commentary
        res = make_viral_commentary({"voice": "es-MX-JorgeNeural"})
        self.assertIsNone(res)


class TestCommentaryScriptGen(unittest.TestCase):
    def test_fallback_template_structure_us(self):
        meta = {
            "title": "Shocking Street Magic Trick",
            "description": "A street magician performs an unbelievable illusion.",
            "duration": 35,
        }
        script = generate_commentary_script(meta, language="us")
        self.assertIn("hook_banner", script)
        self.assertIn("title", script)
        self.assertIn("scenes", script)
        self.assertGreaterEqual(len(script["scenes"]), 5)
        self.assertIn("hashtags", script)
        # Verify scenes have text and keywords
        for sc in script["scenes"]:
            self.assertIn("text", sc)
            self.assertIn("keywords", sc)
            self.assertIsInstance(sc["keywords"], list)

        # For longer videos (> 45s), verify 11 scenes
        meta_long = dict(meta, duration=65)
        script_long = generate_commentary_script(meta_long, language="us")
        self.assertEqual(len(script_long["scenes"]), 11)

    def test_fallback_template_structure_mx(self):
        meta = {
            "title": "Experimento Cientifico Loco",
            "description": "Una reaccion quimica impresionante.",
            "duration": 40,
        }
        script = generate_commentary_script(meta, language="mx")
        self.assertIn("hook_banner", script)
        self.assertIn("title", script)
        self.assertIn("scenes", script)
        self.assertEqual(len(script["scenes"]), 11)
        self.assertIn("hashtags", script)


if __name__ == "__main__":
    unittest.main()
