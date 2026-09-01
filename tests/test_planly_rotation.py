"""Fairness across accounts is a property of the history, not of one run.

A run makes six videos. The account has fifteen channels. Six is all that can be
fed, so the question is not "is this run fair" - it cannot be - but "does every
account get its turn eventually". That only works if the deal remembers where it
stopped, which is what `start` and `next_start` are for.
"""
import unittest

from hub import planly
from tests._support import IsolatedHome

from hub import state as hub_state


def channels(count):
    return [{"id": f"c{i}", "name": f"acc{i:02d}", "social_network": "tiktok"}
            for i in range(count)]


def videos(count, tag="v"):
    return [{"folder": f"{tag}{i}", "title": f"{tag} {i}"} for i in range(count)]


class Rotation(unittest.TestCase):

    def test_the_deal_begins_where_start_says(self):
        dealt = planly.distribute(videos(2), channels(5), start=3)
        self.assertEqual([c for c, items in dealt.items() if items], ["c3", "c4"])

    def test_the_deal_wraps_around_the_end_of_the_list(self):
        dealt = planly.distribute(videos(3), channels(4), start=3)
        self.assertEqual([c for c, items in dealt.items() if items],
                         ["c0", "c1", "c3"])

    def test_start_zero_is_the_old_behaviour(self):
        self.assertEqual(planly.distribute(videos(3), channels(5), start=0),
                         planly.distribute(videos(3), channels(5)))

    def test_next_start_moves_on_by_the_number_of_videos(self):
        self.assertEqual(planly.next_start(0, 6, 15), 6)
        self.assertEqual(planly.next_start(6, 6, 15), 12)

    def test_next_start_wraps(self):
        self.assertEqual(planly.next_start(12, 6, 15), 3)

    def test_next_start_survives_an_empty_channel_list(self):
        self.assertEqual(planly.next_start(4, 6, 0), 0)

    def test_every_account_is_fed_within_a_full_cycle(self):
        """Six videos a run, fifteen channels: nobody is left out for ever."""
        chans = channels(15)
        start = 0
        fed = {c["id"]: 0 for c in chans}
        for run in range(5):
            dealt = planly.distribute(videos(6, f"r{run}"), chans, start=start)
            for cid, items in dealt.items():
                fed[cid] += len(items)
            start = planly.next_start(start, 6, len(chans))

        # 5 runs x 6 videos = 30 videos over 15 channels, dealt evenly.
        self.assertEqual(sum(fed.values()), 30)
        self.assertEqual(set(fed.values()), {2})

    def test_no_video_is_ever_dealt_twice_even_across_the_wrap(self):
        chans = channels(4)
        seen = []
        start = 0
        for run in range(3):
            dealt = planly.distribute(videos(3, f"r{run}"), chans, start=start)
            for items in dealt.values():
                seen += [v["folder"] for v in items]
            start = planly.next_start(start, 3, len(chans))
        self.assertEqual(len(seen), len(set(seen)))

    def test_mirror_ignores_start_entirely(self):
        # Every channel gets every video, so there is no deal to carry forward.
        dealt = planly.distribute(videos(2), channels(3), mode="mirror", start=2)
        self.assertTrue(all(len(items) == 2 for items in dealt.values()))


class RotationIsRemembered(IsolatedHome):

    def test_it_starts_at_zero_on_a_fresh_install(self):
        self.assertEqual(hub_state.channel_start("us"), 0)

    def test_it_round_trips(self):
        hub_state.remember_channel_start("us", 7)
        self.assertEqual(hub_state.channel_start("us"), 7)

    def test_each_route_keeps_its_own_place(self):
        hub_state.remember_channel_start("us", 3)
        hub_state.remember_channel_start("mx", 9)
        self.assertEqual(hub_state.channel_start("us"), 3)
        self.assertEqual(hub_state.channel_start("mx"), 9)

    def test_an_unknown_route_starts_at_zero(self):
        hub_state.remember_channel_start("us", 5)
        self.assertEqual(hub_state.channel_start("mx"), 0)

    def test_rubbish_in_the_file_reads_as_zero_not_a_crash(self):
        hub_state.save({"channel_starts": {"us": "not a number"}})
        self.assertEqual(hub_state.channel_start("us"), 0)

    def test_the_old_flat_key_is_ignored_rather_than_misread(self):
        # Versions before routes stored a bare int under a different name.
        hub_state.save({"channel_start": 6})
        self.assertEqual(hub_state.channel_start("us"), 0)

    def test_a_negative_position_is_clamped(self):
        hub_state.save({"channel_starts": {"us": -4}})
        self.assertEqual(hub_state.channel_start("us"), 0)


if __name__ == "__main__":
    unittest.main()


class NichePlanning(IsolatedHome):
    """Spreading a run across niches, and carrying the position forward."""

    def plan(self, count, niches, name="us"):
        import json
        from pathlib import Path
        directory = self.tmp / name
        directory.mkdir(exist_ok=True)
        (directory / "config.json").write_text(
            json.dumps({"niche_voice": {n: {} for n in niches}}), encoding="utf-8")
        from tools import run_factory
        return run_factory.plan_niches(name, count, Path(directory), {})

    def test_a_run_uses_a_different_niche_for_each_video(self):
        plan = self.plan(3, ["a", "b", "c"])
        self.assertEqual(sorted(plan), ["a", "b", "c"])

    def test_the_next_run_carries_on_where_this_one_stopped(self):
        first = self.plan(2, ["a", "b", "c"])
        second = self.plan(2, ["a", "b", "c"])
        self.assertNotEqual(first[0], second[0])

    def test_more_videos_than_niches_wraps_rather_than_running_out(self):
        plan = self.plan(5, ["a", "b"])
        self.assertEqual(len(plan), 5)
        self.assertEqual(set(plan), {"a", "b"})

    def test_a_factory_with_no_niches_gets_blanks_not_a_crash(self):
        self.assertEqual(self.plan(2, []), ["", ""])
