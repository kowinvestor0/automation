"""hub.publish - finding what the factory rendered, and handing it to Planly.

Nothing here touches the network: the four functions in hub.planly that would
make an HTTP call are replaced by a recorder, and everything else runs for real.
That is deliberate - the point of these tests is the wiring between collect,
distribute, plan_slots and the entries that get sent, which is where a mistake
would put the wrong clip on the wrong channel at the wrong time.
"""
import datetime as dt
import json
import unittest
from pathlib import Path
from unittest import mock

from tests._support import IsolatedHome, channels, local, make_output, publish_cfg
from hub import planly, publish, state as hub_state


class FakePlanly:
    """Stands in for the four functions that would reach app.planly.com."""

    def __init__(self, channel_list, fail_uploads=()):
        self.channels = channel_list
        self.fail_uploads = set(fail_uploads)
        self.uploads = []
        self.created = []
        self.teams_asked = []
        self.teams_used = []

    def resolve_team(self, key, team_id=""):
        self.teams_asked.append(team_id)
        if not team_id:
            raise planly.PlanlyError("No Planly team id set.")
        return team_id

    def list_channels(self, key, team_id):
        return list(self.channels)

    def upload_media(self, key, team_id, path, log=print):
        folder = Path(path).parent.name
        if folder in self.fail_uploads:
            raise RuntimeError("S3 refused the upload")
        self.uploads.append(folder)
        return f"media-{folder}"

    def create_schedules(self, key, team_id, entries):
        self.teams_used.append(team_id)
        self.created.append(entries)
        return {"data": {"created": len(entries)}}

    def patch(self, test):
        test.enterContext(mock.patch.multiple(
            planly,
            resolve_team=self.resolve_team,
            list_channels=self.list_channels,
            upload_media=self.upload_media,
            create_schedules=self.create_schedules,
        ))
        return self


class FactoryOutput(IsolatedHome):
    """A tempdir shaped like a factory that has just finished rendering."""

    VIDEO_COUNT = 6

    def setUp(self):
        super().setUp()
        self.factory = self.tmp / "factories" / "us"
        self.folders = []
        for i in range(self.VIDEO_COUNT):
            folder = f"20260829-12{i:02d}-us"
            make_output(self.factory, folder, {
                "title": f"Title {i}",
                "description": f"Description {i}",
                "file": "video.mp4",
                "duration_seconds": 30,
            })
            self.folders.append(folder)
        self.log = []

    def collect(self, only_new=False):
        return publish.collect_videos(self.factory, only_new=only_new,
                                      log=self.log.append)


class CollectVideos(FactoryOutput):

    VIDEO_COUNT = 2

    def test_it_finds_the_rendered_videos_with_their_metadata(self):
        found = self.collect()
        self.assertEqual([v["folder"] for v in found], self.folders)
        self.assertEqual(found[0]["title"], "Title 0")
        self.assertEqual(found[0]["path"].name, "video.mp4")
        self.assertTrue(found[0]["path"].is_file())

    def test_folders_come_back_in_name_order(self):
        make_output(self.factory, "20260829-1100-us", {"file": "video.mp4"})
        self.assertEqual([v["folder"] for v in self.collect()][0], "20260829-1100-us")

    def test_an_empty_output_folder_is_not_an_error(self):
        self.assertEqual(publish.collect_videos(self.tmp / "empty",
                                                only_new=False, log=self.log.append),
                         [])

    def test_an_unreadable_meta_json_is_skipped_not_fatal(self):
        make_output(self.factory, "20260829-9999-us", None, raw_meta="{ broken")
        found = self.collect()

        self.assertEqual([v["folder"] for v in found], self.folders)
        self.assertTrue(any("20260829-9999-us" in line and "unreadable" in line
                            for line in self.log))

    def test_a_meta_json_naming_a_missing_file_falls_back_to_any_mp4(self):
        folder = make_output(self.factory, "20260829-8888-us",
                             {"title": "Renamed", "file": "does-not-exist.mp4"},
                             mp4="final_render.mp4")
        found = {v["folder"]: v for v in self.collect()}

        self.assertIn("20260829-8888-us", found)
        self.assertEqual(found["20260829-8888-us"]["path"],
                         folder / "final_render.mp4")

    def test_a_folder_with_no_mp4_at_all_is_skipped(self):
        make_output(self.factory, "20260829-7777-us", {"file": "video.mp4"}, mp4=None)
        found = self.collect()

        self.assertEqual([v["folder"] for v in found], self.folders)
        self.assertTrue(any("no .mp4" in line for line in self.log))

    def test_meta_json_without_a_file_key_assumes_video_mp4(self):
        make_output(self.factory, "20260829-6666-us", {"title": "No file key"})
        found = {v["folder"]: v for v in self.collect()}
        self.assertEqual(found["20260829-6666-us"]["path"].name, "video.mp4")

    def test_only_new_skips_what_was_already_published(self):
        hub_state.remember_videos([self.folders[0]])

        fresh = publish.collect_videos(self.factory, only_new=True,
                                       log=self.log.append)
        self.assertEqual([v["folder"] for v in fresh], [self.folders[1]])

        everything = publish.collect_videos(self.factory, only_new=False,
                                            log=self.log.append)
        self.assertEqual([v["folder"] for v in everything], self.folders)

    def test_nothing_new_left_is_an_empty_list(self):
        hub_state.remember_videos(self.folders)
        self.assertEqual(publish.collect_videos(self.factory, only_new=True,
                                                log=self.log.append), [])

    def test_the_metadata_on_disk_is_not_modified(self):
        found = self.collect()
        found[0]["title"] = "changed in memory"
        on_disk = json.loads(
            (self.factory / "output" / self.folders[0] / "meta.json")
            .read_text(encoding="utf-8"))
        self.assertEqual(on_disk["title"], "Title 0")


class Publish(FactoryOutput):

    def setUp(self):
        super().setUp()
        self.fake = FakePlanly(channels("ch1", "ch2", "ch3")).patch(self)

    def run_publish(self, cfg=None, **over):
        cfg = cfg or publish_cfg(**over)
        return publish.publish(self.collect(), cfg, "planly-key",
                               log=self.log.append, now=local(hour=8))

    def test_each_video_is_uploaded_once_no_matter_how_many_channels(self):
        result = self.run_publish(dry_run=False)
        self.assertEqual(sorted(self.fake.uploads), sorted(self.folders))
        self.assertEqual(result.uploaded, 6)

    def test_it_sends_one_batch_of_entries(self):
        result = self.run_publish(dry_run=False)
        self.assertEqual(len(self.fake.created), 1)
        self.assertEqual(len(self.fake.created[0]), 6)
        self.assertEqual(result.scheduled, 6)
        self.assertFalse(result.errors)

    def test_the_calendar_is_columns_of_one_minute_and_distinct_clips(self):
        # The user's rule, end to end: same minute across channels, and never
        # the same clip on two of them.
        self.run_publish(dry_run=False)
        entries = self.fake.created[0]

        by_time = {}
        for entry in entries:
            by_time.setdefault(entry["publishOn"], []).append(entry)

        self.assertEqual(sorted(by_time), ["2026-08-29T02:00:00.000Z",
                                           "2026-08-29T05:00:00.000Z"])
        for when, row in by_time.items():
            with self.subTest(when=when):
                self.assertEqual(sorted(e["channelId"] for e in row),
                                 ["ch1", "ch2", "ch3"])
                media = [e["media"][0]["id"] for e in row]
                self.assertEqual(len(set(media)), 3)

        everywhere = [e["media"][0]["id"] for e in entries]
        self.assertEqual(len(set(everywhere)), 6)

    def test_entries_carry_the_time_in_the_users_own_clock(self):
        result = self.run_publish(dry_run=False)
        first = result.entries[0]
        self.assertEqual(first["publish_on"], "2026-08-29T02:00:00.000Z")
        self.assertEqual(first["local_time"], "2026-08-29 09:00")

    def test_the_caption_comes_from_the_script(self):
        self.run_publish(dry_run=False)
        contents = {e["content"] for e in self.fake.created[0]}
        self.assertEqual(contents, {f"Description {i}" for i in range(6)})

    def test_booked_slots_are_recorded_so_the_next_run_moves_on(self):
        self.run_publish(dry_run=False)
        self.assertEqual(hub_state.all_taken_slots(),
                         {"2026-08-29T02:00:00.000Z", "2026-08-29T05:00:00.000Z"})
        self.assertEqual(hub_state.seen_videos(), set(self.folders))

    def test_slots_booked_by_an_earlier_run_are_skipped(self):
        hub_state.remember_slots("ch1", ["2026-08-29T02:00:00.000Z"])
        self.run_publish(dry_run=False)
        times = sorted({e["publishOn"] for e in self.fake.created[0]})
        self.assertEqual(times, ["2026-08-29T05:00:00.000Z",
                                 "2026-08-29T08:00:00.000Z"])

    def test_a_dry_run_walks_everything_but_creates_nothing(self):
        result = self.run_publish(dry_run=True)

        self.assertTrue(result.dry_run)
        self.assertEqual(result.scheduled, 6)
        self.assertEqual(result.uploaded, 6)
        self.assertEqual(self.fake.created, [])
        # and it leaves no trace in the state file
        self.assertEqual(hub_state.seen_videos(), set())
        self.assertEqual(hub_state.all_taken_slots(), set())

    def test_mirror_mode_puts_every_video_on_every_channel(self):
        result = self.run_publish(dry_run=False, distribute="mirror")
        self.assertEqual(result.scheduled, 18)
        self.assertEqual(len(self.fake.uploads), 6)       # still one upload each
        times = sorted({e["publishOn"] for e in self.fake.created[0]})
        self.assertEqual(len(times), 6)

    def test_a_long_video_warns_but_is_still_scheduled(self):
        make_output(self.factory, "20260829-1299-us",
                    {"title": "Long", "file": "video.mp4", "duration_seconds": 95})
        result = self.run_publish(dry_run=False)
        self.assertTrue(any("95s is longer than 60s" in w for w in result.warnings))
        self.assertEqual(result.scheduled, 7)

    def test_an_upload_failure_is_reported_and_the_rest_still_go_out(self):
        self.fake.fail_uploads = {self.folders[0]}
        result = self.run_publish(dry_run=False)

        self.assertEqual(result.uploaded, 5)
        self.assertEqual(result.scheduled, 5)
        self.assertTrue(any(self.folders[0] in e for e in result.errors))
        self.assertTrue(any(self.folders[0] in s for s in result.skipped))
        self.assertNotIn(self.folders[0], hub_state.seen_videos())

    def test_every_upload_failing_is_an_error_not_a_crash(self):
        self.fake.fail_uploads = set(self.folders)
        result = self.run_publish(dry_run=False)

        self.assertEqual(result.scheduled, 0)
        self.assertEqual(self.fake.created, [])
        self.assertTrue(any("Nothing could be scheduled" in e for e in result.errors))

    def test_nothing_to_publish_is_a_warning_not_a_failure(self):
        result = publish.publish([], publish_cfg(), "planly-key",
                                 log=self.log.append, now=local())
        self.assertEqual(result.scheduled, 0)
        self.assertFalse(result.errors)
        self.assertTrue(any("Nothing to publish" in w for w in result.warnings))
        self.assertEqual(self.fake.uploads, [])

    def test_a_channel_id_that_is_not_on_the_account_is_called_out(self):
        result = self.run_publish(dry_run=False, channels=["ch1", "ch-gone"])
        self.assertTrue(any("ch-gone" in w for w in result.warnings))
        self.assertEqual({e["channelId"] for e in self.fake.created[0]}, {"ch1"})

    def test_more_channels_than_videos_warns_about_the_idle_ones(self):
        for folder in self.folders[2:]:
            (self.factory / "output" / folder / "meta.json").unlink()
        result = self.run_publish(dry_run=False)
        self.assertTrue(any("nothing left for" in w for w in result.warnings))
        self.assertEqual(result.scheduled, 2)

    def test_no_channels_at_all_is_an_error(self):
        self.fake.channels = []
        result = self.run_publish(dry_run=False)
        self.assertTrue(any("No Planly channels" in e for e in result.errors))
        self.assertEqual(self.fake.uploads, [])

    def test_the_configured_team_is_used_when_there_is_one(self):
        self.run_publish(dry_run=False, team_id="team-77")
        self.assertEqual(self.fake.teams_asked, ["team-77"])


class RunForFactory(FactoryOutput):

    VIDEO_COUNT = 3

    def setUp(self):
        super().setUp()
        self.fake = FakePlanly(channels("ch1", "ch2", "ch3")).patch(self)

    def test_publishing_switched_off_does_nothing(self):
        result = publish.run_for_factory(self.factory, publish_cfg(enabled=False),
                                         log=self.log.append)
        self.assertTrue(any("Publishing is off" in w for w in result.warnings))
        self.assertEqual(self.fake.uploads, [])

    def test_no_planly_key_is_an_error_before_any_call(self):
        result = publish.run_for_factory(self.factory, publish_cfg(enabled=True),
                                         log=self.log.append)
        self.assertTrue(any("PLANLY_API_KEY" in e for e in result.errors))
        self.assertEqual(self.fake.uploads, [])

    def test_a_normal_dry_run_reports_what_it_would_do(self):
        import os
        os.environ["PLANLY_API_KEY"] = "planly-key"
        result = publish.run_for_factory(self.factory,
                                         publish_cfg(enabled=True, dry_run=True),
                                         log=self.log.append, only_new=False)
        self.assertEqual(result.scheduled, 3)
        self.assertEqual(result.uploaded, 3)
        self.assertEqual(self.fake.created, [])
        self.assertFalse(result.errors)

    def test_a_planly_error_is_turned_into_a_message(self):
        import os
        os.environ["PLANLY_API_KEY"] = "planly-key"
        with mock.patch.object(planly, "list_channels",
                               side_effect=planly.PlanlyError("rate limit hit")):
            result = publish.run_for_factory(self.factory,
                                             publish_cfg(enabled=True),
                                             log=self.log.append, only_new=False)
        self.assertEqual(result.errors, ["rate limit hit"])

    def test_an_unexpected_error_is_caught_too(self):
        import os
        os.environ["PLANLY_API_KEY"] = "planly-key"
        with mock.patch.object(planly, "list_channels",
                               side_effect=ValueError("something odd")):
            result = publish.run_for_factory(self.factory,
                                             publish_cfg(enabled=True),
                                             log=self.log.append, only_new=False)
        self.assertTrue(any("ValueError" in e for e in result.errors))


class Captions(unittest.TestCase):

    def test_the_description_is_preferred(self):
        text = publish.caption_for({"title": "T", "description": "D"}, {}, {})
        self.assertEqual(text, "D")

    def test_it_falls_back_to_the_title(self):
        self.assertEqual(publish.caption_for({"title": "T"}, {}, {}), "T")

    def test_it_is_empty_when_there_is_neither(self):
        self.assertEqual(publish.caption_for({}, {}, {}), "")

    def test_it_is_cut_to_the_caption_limit(self):
        long = {"description": "x" * 3000}
        self.assertEqual(len(publish.caption_for(long, {}, {})), 2100)
        self.assertEqual(len(publish.caption_for(long, {}, {"caption_limit": 150})), 150)


class ChannelOptions(unittest.TestCase):

    def test_youtube_always_gets_a_title(self):
        options = publish.options_for({"title": "A clip"},
                                      {"id": "c1", "social_network": "youtube"}, {})
        self.assertEqual(options["title"], "A clip")

    def test_other_networks_get_nothing_by_default(self):
        self.assertEqual(publish.options_for({"title": "A clip"},
                                             {"id": "c1", "social_network": "tiktok"},
                                             {}), {})

    def test_a_per_channel_override_wins_over_the_network_one(self):
        cfg = {"channel_options": {"c1": {"privacy": "public"},
                                   "youtube": {"privacy": "private"}}}
        options = publish.options_for({"title": "A clip"},
                                      {"id": "c1", "social_network": "youtube"}, cfg)
        self.assertEqual(options["privacy"], "public")
        self.assertEqual(options["title"], "A clip")

    def test_a_configured_youtube_title_is_not_overwritten(self):
        cfg = {"channel_options": {"youtube": {"title": "Fixed"}}}
        options = publish.options_for({"title": "A clip"},
                                      {"id": "c1", "social_network": "YouTube"}, cfg)
        self.assertEqual(options["title"], "Fixed")

    def test_the_configuration_is_not_mutated(self):
        cfg = {"channel_options": {"youtube": {}}}
        publish.options_for({"title": "A clip"},
                            {"id": "c1", "social_network": "youtube"}, cfg)
        self.assertEqual(cfg["channel_options"]["youtube"], {})


class LocalTime(unittest.TestCase):

    def test_utc_is_turned_back_into_the_users_clock(self):
        self.assertEqual(
            publish._local("2026-08-29T02:00:00.000Z", {"timezone_offset": 7}),
            "2026-08-29 09:00")

    def test_it_crosses_midnight_correctly(self):
        self.assertEqual(
            publish._local("2026-08-29T18:30:00.000Z", {"timezone_offset": 7}),
            "2026-08-30 01:30")

    def test_no_offset_means_utc(self):
        self.assertEqual(publish._local("2026-08-29T02:00:00.000Z", {}),
                         "2026-08-29 02:00")

    def test_something_unparseable_comes_back_unchanged(self):
        self.assertEqual(publish._local("tomorrow-ish", {"timezone_offset": 7}),
                         "tomorrow-ish")


class ResultRecord(unittest.TestCase):

    def test_it_summarises_itself_for_the_status_page(self):
        result = publish.PublishResult()
        result.dry_run = False
        result.uploaded = 2
        result.entries.append({"channel": "CH1", "video": "Title 0"})
        result.warnings.append("a warning")

        data = result.as_dict()
        self.assertEqual(data["scheduled"], 1)
        self.assertEqual(data["uploaded"], 2)
        self.assertFalse(data["dry_run"])
        self.assertEqual(data["warnings"], ["a warning"])
        self.assertEqual(data["errors"], [])

    def test_a_fresh_result_is_empty_and_dry(self):
        result = publish.PublishResult()
        self.assertEqual(result.scheduled, 0)
        self.assertTrue(result.dry_run)


if __name__ == "__main__":
    unittest.main()
