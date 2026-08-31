"""hub.status - the three surfaces the user reads from a phone.

The classification is the load-bearing bit: "partial" has to mean some of the
factories worked, because that is the difference between "look at it tonight"
and "look at it now".
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from tests._support import IsolatedHome
from hub import status


def run(factory="us", videos=2, scheduled=4, state="ok", **over):
    entry = {
        "factory": factory,
        "label": factory.upper(),
        "status": state,
        "videos": videos,
        "scheduled": scheduled,
        "seconds": 12.4,
        "titles": [f"{factory} title {i}" for i in range(3)],
        "calendar": [("2026-08-29 09:00", f"{factory} clip {i}") for i in range(3)],
        "warnings": [],
        "errors": [],
    }
    entry.update(over)
    return entry


class Build(IsolatedHome):

    def test_no_runs_is_idle(self):
        payload = status.build([])
        self.assertEqual(payload["status"], "idle")
        self.assertEqual(payload["videos"], 0)
        self.assertEqual(payload["scheduled"], 0)

    def test_every_run_ok_is_ok(self):
        payload = status.build([run("us"), run("mx")])
        self.assertEqual(payload["status"], "ok")

    def test_one_failure_out_of_two_is_partial(self):
        payload = status.build([run("us"), run("mx", state="failed")])
        self.assertEqual(payload["status"], "partial")

    def test_every_run_failed_is_failed(self):
        payload = status.build([run("us", state="failed"), run("mx", state="failed")])
        self.assertEqual(payload["status"], "failed")

    def test_a_single_failed_run_is_failed_not_partial(self):
        self.assertEqual(status.build([run("us", state="failed")])["status"], "failed")

    def test_a_run_with_an_unknown_state_does_not_count_as_a_failure(self):
        payload = status.build([run("us", state="ok"), run("mx", state="skipped")])
        self.assertEqual(payload["status"], "ok")

    def test_counts_are_summed_across_factories(self):
        payload = status.build([run("us", videos=3, scheduled=6),
                                run("mx", videos=2, scheduled=4)])
        self.assertEqual(payload["videos"], 5)
        self.assertEqual(payload["scheduled"], 10)
        self.assertEqual(len(payload["runs"]), 2)

    def test_a_run_missing_its_counters_does_not_break_the_sum(self):
        payload = status.build([{"factory": "us", "status": "ok"}])
        self.assertEqual(payload["videos"], 0)
        self.assertEqual(payload["status"], "ok")

    def test_extra_fields_are_merged_in(self):
        payload = status.build([run()], {"trigger": "schedule", "videos": 99})
        self.assertEqual(payload["trigger"], "schedule")
        self.assertEqual(payload["videos"], 99)

    def test_the_run_url_is_empty_off_github(self):
        payload = status.build([run()])
        self.assertEqual(payload["run_url"], "")
        self.assertEqual(payload["run_number"], "")

    def test_the_run_url_is_built_from_the_actions_environment(self):
        os.environ["GITHUB_SERVER_URL"] = "https://github.com"
        os.environ["GITHUB_REPOSITORY"] = "owner/name"
        os.environ["GITHUB_RUN_ID"] = "12345"
        os.environ["GITHUB_RUN_NUMBER"] = "7"
        payload = status.build([run()])
        self.assertEqual(payload["run_url"],
                         "https://github.com/owner/name/actions/runs/12345")
        self.assertEqual(payload["run_number"], "7")


class Write(IsolatedHome):

    def test_it_writes_both_files(self):
        payload = status.build([run("us"), run("mx", state="failed",
                                               errors=["render died"])])
        text = status.write(payload, self.tmp)

        md = (self.tmp / "STATUS.md").read_text(encoding="utf-8")
        self.assertEqual(md, text)
        self.assertIn("PARTIAL", md)
        self.assertIn("Videos rendered", md)
        self.assertIn("us title 0", md)
        self.assertIn("render died", md)
        self.assertTrue(md.endswith("\n"))

        data = json.loads((self.tmp / "status.json").read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "partial")
        self.assertEqual(data["videos"], payload["videos"])
        self.assertEqual(len(data["runs"]), 2)

    def test_a_dry_run_says_so(self):
        payload = status.build([run("us", dry_run=True)])
        self.assertIn("dry run", status.write(payload, self.tmp))

    def test_it_appends_to_the_github_step_summary_when_there_is_one(self):
        summary = self.tmp / "summary.md"
        summary.write_text("earlier step\n", encoding="utf-8")
        os.environ["GITHUB_STEP_SUMMARY"] = str(summary)

        text = status.write(status.build([run()]), self.tmp)
        written = summary.read_text(encoding="utf-8")
        self.assertTrue(written.startswith("earlier step\n"))
        self.assertIn(text, written)

    def test_an_unwritable_step_summary_is_not_fatal(self):
        os.environ["GITHUB_STEP_SUMMARY"] = str(self.tmp / "nope" / "summary.md")
        status.write(status.build([run()]), self.tmp)
        self.assertTrue((self.tmp / "STATUS.md").is_file())

    def test_an_idle_payload_still_produces_a_page(self):
        status.write(status.build([]), self.tmp)
        self.assertIn("IDLE", (self.tmp / "STATUS.md").read_text(encoding="utf-8"))


class Short(IsolatedHome):

    LIMIT = 4096          # Telegram's hard cap on a message

    def test_it_names_the_status_and_the_counts(self):
        payload = status.build([run("us", videos=3), run("mx", videos=2)])
        text = status.short(payload)
        self.assertIn(status.BADGE["ok"], text)
        self.assertIn("5 video(s), 8 scheduled", text)
        self.assertIn("US: 3 made", text)
        self.assertIn("MX: 2 made", text)

    def test_the_first_error_of_a_run_is_included(self):
        payload = status.build([run("mx", state="failed",
                                    errors=["ffmpeg exited with 1", "and again"])])
        text = status.short(payload)
        self.assertIn("ffmpeg exited with 1", text)
        self.assertNotIn("and again", text)

    def test_a_long_error_is_truncated(self):
        payload = status.build([run("mx", state="failed", errors=["x" * 500])])
        self.assertLess(len(status.short(payload)), 300)

    def test_a_big_run_still_fits_in_one_telegram_message(self):
        runs = []
        for i in range(8):
            runs.append(run(
                factory=f"factory-{i}",
                videos=30,
                scheduled=180,
                titles=[f"A fairly long generated video title number {n}"
                        for n in range(60)],
                calendar=[(f"2026-08-29 {n % 24:02d}:00", f"clip {n}")
                          for n in range(180)],
                warnings=[f"warning number {n} " + "w" * 120 for n in range(20)],
                errors=[f"error number {n} " + "e" * 300 for n in range(10)],
                state="failed" if i % 2 else "ok",
            ))
        os.environ["GITHUB_SERVER_URL"] = "https://github.com"
        os.environ["GITHUB_REPOSITORY"] = "owner/name"
        os.environ["GITHUB_RUN_ID"] = "12345"
        payload = status.build(runs)

        text = status.short(payload)
        self.assertLess(len(text), self.LIMIT)
        self.assertIn("240 video(s)", text)
        self.assertIn(payload["run_url"], text)
        # The long form is the one that carries the detail.
        self.assertGreater(len(status.write(payload, self.tmp)), self.LIMIT)

    def test_the_run_link_is_the_last_line_when_there_is_one(self):
        os.environ["GITHUB_SERVER_URL"] = "https://github.com"
        os.environ["GITHUB_REPOSITORY"] = "owner/name"
        os.environ["GITHUB_RUN_ID"] = "9"
        payload = status.build([run()])
        self.assertTrue(status.short(payload).endswith(payload["run_url"]))


class MaskingForAPublicRepo(unittest.TestCase):
    """STATUS.md is committed, and the repo has to be public for the minutes."""

    def payload(self):
        run = {
            "factory": "us", "label": "US", "videos": 1, "scheduled": 2,
            "seconds": 12, "titles": ["A clip"], "status": "ok", "errors": [],
            "warnings": ["outdoorboyso got nothing this round"],
            "channel_names": ["outdoorboysl", "outdoorboyso", "outdoorboysoo"],
            "calendar": [("09:00", "A clip -> outdoorboysl (tiktok)"),
                         ("09:00", "B clip -> outdoorboysoo (tiktok)")],
        }
        return status.build([run]), run["channel_names"]

    def test_no_account_name_survives_into_the_written_files(self):
        payload, names = self.payload()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            status.write(payload, root, names=names)
            blob = ((root / "STATUS.md").read_text(encoding="utf-8")
                    + (root / "status.json").read_text(encoding="utf-8"))
        for name in names:
            self.assertNotIn(name, blob)

    def test_the_calendar_tuples_are_scrubbed_too(self):
        # They are tuples, not lists, and a scrubber that only walked lists let
        # every account name straight through.
        payload, names = self.payload()
        masked = status.mask(payload, names)
        self.assertNotIn("outdoorboysl", masked["runs"][0]["calendar"][0][1])

    def test_warnings_are_scrubbed(self):
        payload, names = self.payload()
        masked = status.mask(payload, names)
        self.assertNotIn("outdoorboyso", masked["runs"][0]["warnings"][0])

    def test_an_account_name_inside_another_is_not_half_replaced(self):
        payload, names = self.payload()
        masked = status.mask(payload, names)
        line = masked["runs"][0]["calendar"][1][1]
        self.assertIn(status.alias("outdoorboysoo"), line)
        self.assertNotIn(status.alias("outdoorboyso") + "o", line)

    def test_the_alias_is_the_same_every_run(self):
        self.assertEqual(status.alias("outdoorboysl"), status.alias("outdoorboysl"))

    def test_different_accounts_get_different_aliases(self):
        self.assertNotEqual(status.alias("outdoorboysl"), status.alias("outdoorboysm"))

    def test_the_original_payload_is_untouched_so_telegram_keeps_real_names(self):
        payload, names = self.payload()
        status.mask(payload, names)
        self.assertIn("outdoorboysl", payload["runs"][0]["calendar"][0][1])

    def test_nothing_to_mask_is_a_no_op(self):
        payload, _ = self.payload()
        self.assertEqual(status.mask(payload, []), payload)
