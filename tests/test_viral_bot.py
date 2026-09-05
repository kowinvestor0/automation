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
        self.assertEqual(len(script["scenes"]), 11)
        self.assertIn("hashtags", script)
        # Verify scenes have text and keywords
        for sc in script["scenes"]:
            self.assertIn("text", sc)
            self.assertIn("keywords", sc)
            self.assertIsInstance(sc["keywords"], list)

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
