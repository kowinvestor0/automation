"""hub.planly.duration_warning - Planly hides posts longer than a minute.

The warning must never block the run: `max_seconds` is a setting and the user
may have raised it deliberately.
"""
import unittest

from hub import planly


class DurationWarning(unittest.TestCase):

    def test_a_video_over_the_limit_warns(self):
        warning = planly.duration_warning(
            {"title": "Long one", "duration_seconds": 75}, 60)
        self.assertIsNotNone(warning)
        self.assertIn("Long one", warning)
        self.assertIn("75s", warning)
        self.assertIn("60s", warning)

    def test_a_video_under_the_limit_is_silent(self):
        self.assertIsNone(planly.duration_warning({"duration_seconds": 45}, 60))

    def test_exactly_at_the_limit_is_silent(self):
        self.assertIsNone(planly.duration_warning({"duration_seconds": 60}, 60))
        self.assertIsNone(planly.duration_warning({"duration_seconds": 60.0}, 60))

    def test_missing_duration_is_silent(self):
        self.assertIsNone(planly.duration_warning({"title": "No metadata"}, 60))
        self.assertIsNone(planly.duration_warning({"duration_seconds": None}, 60))
        self.assertIsNone(planly.duration_warning({"duration_seconds": 0}, 60))

    def test_no_limit_configured_is_silent(self):
        self.assertIsNone(planly.duration_warning({"duration_seconds": 900}, 0))
        self.assertIsNone(planly.duration_warning({"duration_seconds": 900}, None))

    def test_strings_from_meta_json_are_compared_as_numbers(self):
        self.assertIsNotNone(planly.duration_warning({"duration_seconds": "75"}, "60"))
        self.assertIsNone(planly.duration_warning({"duration_seconds": "45"}, "60"))

    def test_falls_back_to_the_filename_then_to_a_generic_name(self):
        self.assertIn("clip.mp4", planly.duration_warning(
            {"file": "clip.mp4", "duration_seconds": 99}, 60))
        self.assertTrue(planly.duration_warning(
            {"duration_seconds": 99}, 60).startswith("video:"))
