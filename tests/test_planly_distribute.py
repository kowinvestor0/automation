"""hub.planly.distribute - which channel gets which video.

The user posts to 8 channels at the same minute and never wants the same clip
on two of them, so "unique" dealing is a correctness requirement, not a
preference. The last test in this file pins that whole behaviour down.
"""
import unittest

from tests._support import channels, local, publish_cfg, videos
from hub import planly


class Unique(unittest.TestCase):

    def test_six_videos_over_three_channels_deals_two_each(self):
        vids = videos(6)
        dealt = planly.distribute(vids, channels("a", "b", "c"), "unique")

        self.assertEqual(sorted(dealt), ["a", "b", "c"])
        for cid in dealt:
            self.assertEqual(len(dealt[cid]), 2, cid)
            folders = [v["folder"] for v in dealt[cid]]
            self.assertEqual(len(set(folders)), 2, "a channel got the same clip twice")

    def test_no_video_appears_on_more_than_one_channel(self):
        vids = videos(6)
        dealt = planly.distribute(vids, channels("a", "b", "c"), "unique")
        seen = [v["folder"] for items in dealt.values() for v in items]
        self.assertEqual(len(seen), 6)
        self.assertEqual(len(set(seen)), 6)
        self.assertEqual(set(seen), {v["folder"] for v in vids})

    def test_dealing_is_round_robin_so_the_first_posts_differ(self):
        vids = videos(6)
        dealt = planly.distribute(vids, channels("a", "b", "c"), "unique")
        self.assertEqual([v["folder"] for v in dealt["a"]], ["v0", "v3"])
        self.assertEqual([v["folder"] for v in dealt["b"]], ["v1", "v4"])
        self.assertEqual([v["folder"] for v in dealt["c"]], ["v2", "v5"])

    def test_fewer_videos_than_channels_leaves_the_tail_empty(self):
        dealt = planly.distribute(videos(2), channels("a", "b", "c", "d"), "unique")
        self.assertEqual([v["folder"] for v in dealt["a"]], ["v0"])
        self.assertEqual([v["folder"] for v in dealt["b"]], ["v1"])
        self.assertEqual(dealt["c"], [])
        self.assertEqual(dealt["d"], [])

    def test_uneven_split_keeps_every_video(self):
        dealt = planly.distribute(videos(7), channels("a", "b", "c"), "unique")
        self.assertEqual([len(dealt[c]) for c in ("a", "b", "c")], [3, 2, 2])

    def test_is_the_default_mode(self):
        vids = videos(4)
        self.assertEqual(planly.distribute(vids, channels("a", "b")),
                         planly.distribute(vids, channels("a", "b"), "unique"))

    def test_no_videos_gives_every_channel_an_empty_list(self):
        dealt = planly.distribute([], channels("a", "b"), "unique")
        self.assertEqual(dealt, {"a": [], "b": []})


class Mirror(unittest.TestCase):

    def test_every_channel_gets_every_video(self):
        vids = videos(3)
        dealt = planly.distribute(vids, channels("a", "b", "c"), "mirror")
        for cid in ("a", "b", "c"):
            self.assertEqual([v["folder"] for v in dealt[cid]], ["v0", "v1", "v2"])

    def test_each_channel_gets_its_own_list_object(self):
        vids = videos(2)
        dealt = planly.distribute(vids, channels("a", "b"), "mirror")
        dealt["a"].append("extra")
        self.assertEqual(len(dealt["b"]), 2)


class NoChannels(unittest.TestCase):

    def test_returns_an_empty_mapping(self):
        for mode in ("unique", "mirror"):
            with self.subTest(mode=mode):
                self.assertEqual(planly.distribute(videos(3), [], mode), {})


class SameMinuteDifferentVideos(unittest.TestCase):
    """The behaviour the user actually asked for, written down.

    distribute=unique + mode=same_time must give every channel the identical
    timestamp for its Nth post while the video at that timestamp differs per
    channel. This is the exact pair of properties a refactor of either function
    would quietly break, so it is asserted end to end the way hub.publish
    combines them.
    """

    def setUp(self):
        self.cfg = publish_cfg(mode="same_time", distribute="unique")
        self.vids = videos(8)
        self.channels = channels("ch1", "ch2", "ch3", "ch4")
        self.dealt = planly.distribute(self.vids, self.channels,
                                       self.cfg["distribute"])
        per_channel = max(len(v) for v in self.dealt.values())
        self.slots = planly.plan_slots(per_channel, self.cfg, now=local(hour=8))

    def test_first_post_of_every_channel_is_the_same_timestamp(self):
        first = {cid: self.slots[0] for cid in self.dealt}
        self.assertEqual(len(set(first.values())), 1)
        self.assertEqual(set(first.values()), {"2026-08-29T02:00:00.000Z"})

    def test_first_post_of_every_channel_is_a_different_video(self):
        first = [items[0]["folder"] for items in self.dealt.values()]
        self.assertEqual(len(first), 4)
        self.assertEqual(len(set(first)), 4)

    def test_the_whole_calendar_lines_up_in_columns(self):
        # Every row is one minute across all channels; every cell in that row is
        # a different clip; no clip is used twice in the entire grid.
        used = []
        for index, when in enumerate(self.slots):
            row = []
            for cid, items in self.dealt.items():
                self.assertEqual(len(items), len(self.slots))
                row.append(items[index]["folder"])
                # position in the list is the slot index, shared by all channels
                self.assertEqual(self.slots[index], when)
            self.assertEqual(len(set(row)), len(row), f"clip repeated at {when}")
            used.extend(row)
        self.assertEqual(len(used), 8)
        self.assertEqual(len(set(used)), 8)

    def test_channels_are_not_staggered(self):
        # A stagger would show up as more distinct times than slots.
        times = {self.slots[i] for i in range(len(self.slots)) for _ in self.dealt}
        self.assertEqual(len(times), len(self.slots))
        self.assertEqual(self.slots, ["2026-08-29T02:00:00.000Z",
                                      "2026-08-29T05:00:00.000Z"])
