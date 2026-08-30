"""Posting immediately, and the Duet/Stitch switches that make long videos work.

Two rules from the platforms, neither of them ours to argue with:

  * Planly publishes right away when a schedule carries no publishOn at all.
  * TikTok refuses a video longer than about a minute while Duet or Stitch are
    still enabled. The post does not fail loudly - it simply never appears.
"""
import unittest

from hub import planly, publish
from hub import state as hub_state
from tests._support import channels, local, publish_cfg
from tests.test_publish import FactoryOutput, FakePlanly

TIKTOK = {"id": "t1", "name": "acc", "social_network": "tiktok_business"}
YOUTUBE = {"id": "y1", "name": "tube", "social_network": "youtube"}


def video(seconds=None, title="A video"):
    out = {"title": title, "folder": "f1"}
    if seconds is not None:
        out["duration_seconds"] = seconds
    return out


class DuetAndStitch(unittest.TestCase):

    def opts(self, seconds, **post):
        cfg = publish_cfg(post_options={"duet": "auto", "stitch": "auto",
                                        "auto_disable_over_seconds": 60, **post})
        return publish.options_for(video(seconds), TIKTOK, cfg)

    def test_a_long_video_gets_both_switched_off(self):
        options = self.opts(75)
        self.assertTrue(options["disableDuet"])
        self.assertTrue(options["disableStitch"])

    def test_a_short_video_leaves_them_alone(self):
        options = self.opts(40)
        self.assertNotIn("disableDuet", options)
        self.assertNotIn("disableStitch", options)

    def test_exactly_at_the_limit_is_still_allowed(self):
        self.assertNotIn("disableDuet", self.opts(60))

    def test_one_second_over_is_not(self):
        self.assertIn("disableDuet", self.opts(61))

    def test_an_unknown_duration_switches_them_off(self):
        # Guessing wrong costs the whole post one way and only the duet feature
        # the other, so the safe guess is the one that keeps the post.
        options = self.opts(None)
        self.assertTrue(options["disableDuet"])
        self.assertTrue(options["disableStitch"])

    def test_allow_overrides_the_length_check(self):
        self.assertNotIn("disableDuet", self.opts(120, duet="allow"))

    def test_disable_overrides_it_the_other_way(self):
        self.assertTrue(self.opts(10, duet="disable")["disableDuet"])

    def test_the_limit_is_configurable(self):
        options = self.opts(75, auto_disable_over_seconds=90)
        self.assertNotIn("disableDuet", options)

    def test_tiktok_always_gets_a_post_type(self):
        self.assertEqual(self.opts(40)["postType"], 0)

    def test_comments_are_left_on_unless_asked(self):
        self.assertNotIn("disableComment", self.opts(75))
        self.assertTrue(self.opts(75, comment="disable")["disableComment"])

    def test_youtube_is_untouched_by_any_of_it(self):
        cfg = publish_cfg()
        options = publish.options_for(video(120), YOUTUBE, cfg)
        self.assertNotIn("disableDuet", options)
        self.assertIn("title", options)

    def test_a_per_channel_override_wins(self):
        cfg = publish_cfg(channel_options={"t1": {"disableDuet": False}})
        self.assertIs(publish.options_for(video(120), TIKTOK, cfg)["disableDuet"],
                      False)


class BuildGroupsWithoutATime(unittest.TestCase):

    def entry(self, channel, media, when=None):
        out = {"channelId": channel, "content": "",
               "media": [{"id": media, "options": {}}], "options": {}}
        if when:
            out["publishOn"] = when
        return out

    def test_no_time_means_the_field_is_absent_not_null(self):
        groups = planly.build_groups([self.entry("c1", "m1")])
        self.assertNotIn("publishOn", groups[0])

    def test_two_videos_posted_now_stay_in_separate_groups(self):
        groups = planly.build_groups([self.entry("c1", "m1"),
                                      self.entry("c2", "m2")])
        self.assertEqual(len(groups), 2)

    def test_the_same_video_to_two_channels_now_is_one_group(self):
        groups = planly.build_groups([self.entry("c1", "m1"),
                                      self.entry("c2", "m1")])
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["schedules"]), 2)

    def test_a_scheduled_entry_still_carries_its_time(self):
        when = "2026-09-01T02:00:00.000Z"
        groups = planly.build_groups([self.entry("c1", "m1", when)])
        self.assertEqual(groups[0]["publishOn"], when)


class PostingNow(FactoryOutput):

    def setUp(self):
        super().setUp()
        self.fake = FakePlanly(channels("c1", "c2", "c3")).patch(self)

    def run_now(self, **over):
        return publish.publish(self.collect(), publish_cfg(dry_run=False,
                                                           when="now", **over),
                               "planly-key", log=self.log.append, now=local(hour=8))

    def test_nothing_carries_a_publish_time(self):
        result = self.run_now()
        self.assertTrue(all(e["publish_on"] is None for e in result.entries))

    def test_the_report_says_so_in_plain_words(self):
        self.assertTrue(all(e["local_time"] == "ngay bay gio"
                            for e in self.run_now().entries))

    def test_no_slot_is_booked_because_none_was_used(self):
        self.run_now()
        self.assertEqual(hub_state.all_taken_slots(), set())

    def test_the_rotation_still_moves_so_accounts_take_turns(self):
        self.run_now()
        self.assertEqual(hub_state.channel_start("default"),
                         planly.next_start(0, len(self.folders), 3))

    def test_what_reaches_planly_has_no_publish_on(self):
        self.run_now()
        sent = self.fake.created[-1]
        self.assertTrue(all("publishOn" not in entry for entry in sent))

    def test_slots_mode_still_schedules(self):
        result = publish.publish(self.collect(),
                                 publish_cfg(dry_run=False, when="slots"),
                                 "planly-key", log=self.log.append,
                                 now=local(hour=8))
        self.assertTrue(all(e["publish_on"] for e in result.entries))
        self.assertNotEqual(hub_state.all_taken_slots(), set())

    def test_the_default_is_posting_now(self):
        from hub import settings
        self.assertEqual(settings.DEFAULTS["publish"]["when"], "now")


if __name__ == "__main__":
    unittest.main()
