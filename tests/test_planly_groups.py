"""Grouping is the rule that decides what Planly thinks a post *is*.

A Planly schedule group means "one post going out to several channels at once".
Group on publish time alone and eight channels holding eight different videos
land in one group - Planly then treats it as one video fanned out to eight
channels, which is the failure the calendar showed before.

So: group on (publishOn, mediaId), never on publishOn alone.
"""
import unittest

from hub import planly


def entry(channel, media, when, content="", options=None):
    return {
        "channelId": channel,
        "publishOn": when,
        "content": content,
        "media": [{"id": media, "options": {}}],
        "options": options or {},
    }


T1 = "2026-09-01T02:00:00.000Z"
T2 = "2026-09-01T05:00:00.000Z"


class BuildGroups(unittest.TestCase):

    def test_same_time_different_videos_do_not_share_a_group(self):
        groups = planly.build_groups([
            entry("ch1", "media-a", T1),
            entry("ch2", "media-b", T1),
            entry("ch3", "media-c", T1),
        ])
        self.assertEqual(len(groups), 3)
        for group in groups:
            self.assertEqual(len(group["schedules"]), 1)
            self.assertEqual(group["publishOn"], T1)

    def test_same_video_on_many_channels_is_one_group(self):
        groups = planly.build_groups([
            entry("ch1", "media-a", T1),
            entry("ch2", "media-a", T1),
            entry("ch3", "media-a", T1),
        ])
        self.assertEqual(len(groups), 1)
        self.assertEqual(len(groups[0]["schedules"]), 3)
        self.assertEqual({s["channelId"] for s in groups[0]["schedules"]},
                         {"ch1", "ch2", "ch3"})

    def test_the_same_video_at_two_times_is_two_groups(self):
        groups = planly.build_groups([
            entry("ch1", "media-a", T1),
            entry("ch1", "media-a", T2),
        ])
        self.assertEqual(len(groups), 2)
        self.assertEqual({g["publishOn"] for g in groups}, {T1, T2})

    def test_every_schedule_carries_status_one(self):
        # Planly drops an entry with no status; the app that works sends 1.
        groups = planly.build_groups([entry("ch1", "media-a", T1)])
        self.assertEqual(groups[0]["schedules"][0]["status"],
                         planly.STATUS_SCHEDULED)

    def test_tiktok_gets_a_post_type_when_nothing_was_configured(self):
        groups = planly.build_groups([entry("ch1", "media-a", T1)])
        self.assertEqual(groups[0]["schedules"][0]["options"], {"postType": 0})

    def test_configured_options_are_kept(self):
        groups = planly.build_groups(
            [entry("ch1", "media-a", T1, options={"title": "Hello"})])
        self.assertEqual(groups[0]["schedules"][0]["options"], {"title": "Hello"})

    def test_content_and_media_survive_the_fold(self):
        groups = planly.build_groups([entry("ch1", "media-a", T1, content="caption")])
        schedule = groups[0]["schedules"][0]
        self.assertEqual(schedule["content"], "caption")
        self.assertEqual(schedule["media"], [{"id": "media-a", "options": {}}])

    def test_order_is_the_order_the_entries_arrived_in(self):
        groups = planly.build_groups([
            entry("ch1", "media-b", T2),
            entry("ch1", "media-a", T1),
        ])
        self.assertEqual([g["publishOn"] for g in groups], [T2, T1])

    def test_nothing_in_nothing_out(self):
        self.assertEqual(planly.build_groups([]), [])

    def test_the_real_shape_eight_channels_six_slots(self):
        """48 videos over 8 channels: 48 groups of one, never 6 groups of 8."""
        times = [f"2026-09-01T{2 + n:02d}:00:00.000Z" for n in range(6)]
        entries = []
        for slot, when in enumerate(times):
            for channel in range(8):
                entries.append(entry(f"ch{channel}", f"media-{slot}-{channel}", when))

        groups = planly.build_groups(entries)
        self.assertEqual(len(groups), 48)
        self.assertTrue(all(len(g["schedules"]) == 1 for g in groups))
        # Every slot still holds exactly eight posts, one per channel.
        for when in times:
            at_this_time = [g for g in groups if g["publishOn"] == when]
            self.assertEqual(len(at_this_time), 8)


class ResolveTeam(unittest.TestCase):

    def test_a_configured_id_is_used_as_is(self):
        self.assertEqual(planly.resolve_team("key", "team-9"), "team-9")

    def test_no_id_is_an_error_and_says_why(self):
        # Planly has no teams/list endpoint - it answers 404 - so there is
        # nothing to fall back on and guessing would be worse than failing.
        with self.assertRaises(planly.PlanlyError) as caught:
            planly.resolve_team("key", "")
        self.assertIn("team id", str(caught.exception).lower())

    def test_whitespace_only_counts_as_missing(self):
        with self.assertRaises(planly.PlanlyError):
            planly.resolve_team("key", "   ")


class CheckKey(unittest.TestCase):

    def test_a_short_key_is_rejected_before_any_request(self):
        ok, message = planly.check_key("abc", "team-1")
        self.assertFalse(ok)
        self.assertIn("short", message.lower())

    def test_a_missing_team_is_reported_not_guessed(self):
        ok, message = planly.check_key("k" * 43, "")
        self.assertFalse(ok)
        self.assertIn("team", message.lower())


if __name__ == "__main__":
    unittest.main()
