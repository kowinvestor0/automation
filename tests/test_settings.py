"""hub.settings - the deep merge that keeps old settings files loading, and the
env-first rule that lets the same code run on GitHub Actions and on a PC.

Every test here runs against a tempdir. The first test asserts that isolation
rather than assuming it: a bug in it would mean the suite rewrites the real API
keys in the user's profile.
"""
import json
import os
import unittest

from tests._support import IsolatedHome
from hub import paths, settings


class Isolation(IsolatedHome):

    def test_the_data_dir_is_the_tempdir_not_the_real_profile(self):
        self.assertEqual(paths.data_dir(), self.tmp)
        self.assertEqual(settings.path().parent, self.tmp)
        self.assertEqual(settings.path().name, "settings.json")
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            self.assertNotIn(appdata.lower(), str(settings.path()).lower())

    def test_saving_writes_only_inside_the_tempdir(self):
        written = settings.save(settings.DEFAULTS)
        self.assertTrue(str(written).startswith(str(self.tmp)))
        self.assertEqual([p.name for p in self.tmp.iterdir()], ["settings.json"])


class Load(IsolatedHome):

    def test_missing_file_gives_the_defaults(self):
        cfg = settings.load()
        self.assertEqual(cfg["publish"]["times"], settings.DEFAULTS["publish"]["times"])
        self.assertEqual(cfg["publish"]["mode"], "same_time")
        self.assertEqual(cfg["publish"]["distribute"], "unique")
        self.assertFalse(cfg["publish"]["enabled"])

    def test_a_partial_file_is_deep_merged_over_the_defaults(self):
        # What an older version of the app would have written: a publish block
        # with none of the keys added since.
        settings.path().write_text(json.dumps({
            "publish": {"enabled": True, "team_id": "team-1"},
            "run": {"us": {"count": 9}},
        }), encoding="utf-8")

        cfg = settings.load()
        self.assertTrue(cfg["publish"]["enabled"])
        self.assertEqual(cfg["publish"]["team_id"], "team-1")
        # untouched keys survive from DEFAULTS instead of vanishing
        self.assertEqual(cfg["publish"]["times"], settings.DEFAULTS["publish"]["times"])
        self.assertEqual(cfg["publish"]["timezone_offset"], 7)
        self.assertEqual(cfg["publish"]["max_seconds"], 60)
        self.assertEqual(cfg["run"]["us"]["count"], 9)
        self.assertEqual(cfg["run"]["us"]["niche"], "")
        self.assertTrue(cfg["run"]["us"]["enabled"])
        self.assertEqual(cfg["run"]["mx"], settings.DEFAULTS["run"]["mx"])
        self.assertEqual(sorted(cfg["keys"]), sorted(settings.SECRET_NAMES))

    def test_the_merge_does_not_mutate_defaults(self):
        settings.path().write_text(json.dumps({"publish": {"times": ["06:00"]}}),
                                   encoding="utf-8")
        cfg = settings.load()
        cfg["publish"]["times"].append("23:59")
        self.assertEqual(settings.DEFAULTS["publish"]["times"],
                         ["09:00", "12:00", "15:00", "18:00", "21:00", "23:00"])
        self.assertEqual(settings.load()["publish"]["times"], ["06:00"])

    def test_unknown_keys_in_the_file_are_kept(self):
        settings.path().write_text(json.dumps({"publish": {"future_option": 1}}),
                                   encoding="utf-8")
        self.assertEqual(settings.load()["publish"]["future_option"], 1)

    def test_a_corrupt_file_falls_back_to_the_defaults(self):
        settings.path().write_text("{ not json", encoding="utf-8")
        self.assertEqual(settings.load()["publish"]["mode"], "same_time")

    def test_a_file_with_a_bom_still_loads(self):
        settings.path().write_text(json.dumps({"publish": {"gap_minutes": 45}}),
                                   encoding="utf-8-sig")
        self.assertEqual(settings.load()["publish"]["gap_minutes"], 45)

    def test_a_blank_workspace_is_filled_in(self):
        cfg = settings.load()
        self.assertTrue(cfg["workspace"])
        self.assertEqual(cfg["workspace"], str(paths.default_workspace()))

    def test_a_configured_workspace_is_left_alone(self):
        settings.save({"workspace": "D:/videos"})
        self.assertEqual(settings.load()["workspace"], "D:/videos")


class SaveRoundTrip(IsolatedHome):

    def test_save_then_load_returns_what_was_saved(self):
        cfg = settings.load()
        cfg["publish"]["enabled"] = True
        cfg["publish"]["times"] = ["07:30", "19:45"]
        cfg["publish"]["channels"] = ["ch-a", "ch-b"]
        cfg["keys"]["PLANLY_API_KEY"] = "planly-secret"
        cfg["github"]["repo"] = "owner/name"
        settings.save(cfg)

        again = settings.load()
        self.assertEqual(again, cfg)
        self.assertTrue(again["publish"]["enabled"])
        self.assertEqual(again["publish"]["times"], ["07:30", "19:45"])
        self.assertEqual(again["keys"]["PLANLY_API_KEY"], "planly-secret")

    def test_save_leaves_no_temp_file_behind(self):
        settings.save(settings.load())
        self.assertEqual([p.name for p in self.tmp.glob("*.tmp")], [])

    def test_save_creates_the_directory(self):
        nested = self.tmp / "deep" / "er"
        os.environ["HUB_DATA_DIR"] = str(nested)
        settings.save({"workspace": "x"})
        self.assertTrue((nested / "settings.json").is_file())


class Secret(IsolatedHome):

    def test_the_environment_wins_over_the_file(self):
        settings.save({"keys": {"PLANLY_API_KEY": "from-file"}})
        os.environ["PLANLY_API_KEY"] = "from-env"
        self.assertEqual(settings.secret("PLANLY_API_KEY"), "from-env")

    def test_the_file_is_used_when_the_environment_is_empty(self):
        settings.save({"keys": {"PLANLY_API_KEY": "from-file"}})
        self.assertEqual(settings.secret("PLANLY_API_KEY"), "from-file")

    def test_a_blank_environment_variable_does_not_shadow_the_file(self):
        settings.save({"keys": {"PLANLY_API_KEY": "from-file"}})
        os.environ["PLANLY_API_KEY"] = "   "
        self.assertEqual(settings.secret("PLANLY_API_KEY"), "from-file")

    def test_a_placeholder_in_the_environment_falls_through_to_the_file(self):
        settings.save({"keys": {"PLANLY_API_KEY": "from-file"}})
        for junk in ("...", "xxx", "your-key-here", "CHANGEME", "None"):
            with self.subTest(junk=junk):
                os.environ["PLANLY_API_KEY"] = junk
                self.assertEqual(settings.secret("PLANLY_API_KEY"), "from-file")

    def test_a_placeholder_in_the_file_counts_as_empty(self):
        for junk in ("...", "xxx", "your-key-here", "changeme", "null"):
            with self.subTest(junk=junk):
                settings.save({"keys": {"PLANLY_API_KEY": junk}})
                self.assertEqual(settings.secret("PLANLY_API_KEY"), "")

    def test_surrounding_whitespace_is_stripped(self):
        os.environ["GEMINI_API_KEY"] = "  spaced  "
        self.assertEqual(settings.secret("GEMINI_API_KEY"), "spaced")

    def test_an_unset_key_is_an_empty_string(self):
        self.assertEqual(settings.secret("TELEGRAM_BOT_TOKEN"), "")

    def test_a_passed_cfg_is_used_instead_of_re_reading_the_file(self):
        settings.save({"keys": {"PEXELS_API_KEY": "on-disk"}})
        cfg = {"keys": {"PEXELS_API_KEY": "in-memory"}}
        self.assertEqual(settings.secret("PEXELS_API_KEY", cfg), "in-memory")


class ExportAndMissing(IsolatedHome):

    def test_export_env_pushes_stored_keys_into_the_environment(self):
        cfg = settings.load()
        cfg["keys"]["PEXELS_API_KEY"] = "pexels-1"
        cfg["keys"]["GEMINI_API_KEY"] = "gemini-1"
        exported = settings.export_env(cfg)

        self.assertEqual(sorted(exported), ["GEMINI_API_KEY", "PEXELS_API_KEY"])
        self.assertEqual(os.environ["PEXELS_API_KEY"], "pexels-1")
        self.assertNotIn("PLANLY_API_KEY", os.environ)

    def test_missing_keys_explains_what_is_degraded(self):
        problems = settings.missing_keys(settings.load())
        self.assertTrue(any("GEMINI" in p for p in problems))
        self.assertTrue(any("PEXELS" in p for p in problems))

    def test_publishing_without_a_planly_key_is_called_out(self):
        cfg = settings.load()
        cfg["publish"]["enabled"] = True
        self.assertTrue(any("PLANLY_API_KEY" in p for p in settings.missing_keys(cfg)))

        cfg["keys"]["PLANLY_API_KEY"] = "planly-1"
        self.assertFalse(any("PLANLY_API_KEY" in p for p in settings.missing_keys(cfg)))

    def test_a_key_in_the_environment_satisfies_the_check(self):
        os.environ["GEMINI_API_KEY"] = "gemini-1"
        os.environ["PEXELS_API_KEY"] = "pexels-1"
        self.assertEqual(settings.missing_keys(settings.load()), [])
