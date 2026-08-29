"""hub.planly.plan_slots - the wall clock the user types turned into UTC.

A bug here is silent: nothing crashes, the post simply appears at the wrong
hour on someone else's calendar. So the expected UTC strings are written out in
full rather than recomputed from the same formula the code uses.
"""
import unittest

from tests._support import local, publish_cfg
from hub import planly
from hub.planly import PlanlyError


class SameTimeMode(unittest.TestCase):

    def test_configured_wall_clock_times_become_utc(self):
        # 09:00 in UTC+7 is 02:00Z; the whole day, spelled out.
        slots = planly.plan_slots(6, publish_cfg(), now=local(hour=8))
        self.assertEqual(slots, [
            "2026-08-29T02:00:00.000Z",
            "2026-08-29T05:00:00.000Z",
            "2026-08-29T08:00:00.000Z",
            "2026-08-29T11:00:00.000Z",
            "2026-08-29T14:00:00.000Z",
            "2026-08-29T16:00:00.000Z",
        ])

    def test_timezone_offset_is_what_moves_the_times(self):
        slots = planly.plan_slots(1, publish_cfg(timezone_offset=0), now=local(hour=1))
        self.assertEqual(slots, ["2026-08-29T09:00:00.000Z"])
        slots = planly.plan_slots(1, publish_cfg(timezone_offset=-5), now=local(hour=1))
        self.assertEqual(slots, ["2026-08-29T14:00:00.000Z"])

    def test_lead_minutes_excludes_a_slot_that_is_too_soon(self):
        # 08:45 local + 30 minutes lead lands past 09:00, so 09:00 is unusable.
        slots = planly.plan_slots(2, publish_cfg(), now=local(hour=8, minute=45))
        self.assertNotIn("2026-08-29T02:00:00.000Z", slots)
        self.assertEqual(slots[0], "2026-08-29T05:00:00.000Z")

    def test_without_lead_the_same_slot_is_usable(self):
        slots = planly.plan_slots(1, publish_cfg(lead_minutes=0),
                                  now=local(hour=8, minute=45))
        self.assertEqual(slots, ["2026-08-29T02:00:00.000Z"])

    def test_lead_minutes_defaults_to_thirty_when_absent(self):
        cfg = publish_cfg()
        del cfg["lead_minutes"]
        slots = planly.plan_slots(1, cfg, now=local(hour=8, minute=45))
        self.assertEqual(slots, ["2026-08-29T05:00:00.000Z"])

    def test_rolls_into_the_following_day_when_the_times_run_out(self):
        slots = planly.plan_slots(8, publish_cfg(), now=local(hour=8))
        self.assertEqual(len(slots), 8)
        self.assertEqual(slots[6], "2026-08-30T02:00:00.000Z")
        self.assertEqual(slots[7], "2026-08-30T05:00:00.000Z")

    def test_slots_are_chronological_and_unique(self):
        slots = planly.plan_slots(20, publish_cfg(), now=local(hour=8))
        self.assertEqual(slots, sorted(slots))
        self.assertEqual(len(set(slots)), 20)

    def test_an_unsorted_times_list_is_still_used_in_order(self):
        cfg = publish_cfg(times=["21:00", "09:00", "15:00"])
        slots = planly.plan_slots(3, cfg, now=local(hour=1))
        self.assertEqual(slots, [
            "2026-08-29T02:00:00.000Z",
            "2026-08-29T08:00:00.000Z",
            "2026-08-29T14:00:00.000Z",
        ])

    def test_taken_slots_are_skipped(self):
        taken = {"2026-08-29T02:00:00.000Z", "2026-08-29T08:00:00.000Z"}
        slots = planly.plan_slots(3, publish_cfg(), now=local(hour=8), taken=taken)
        self.assertEqual(slots, [
            "2026-08-29T05:00:00.000Z",
            "2026-08-29T11:00:00.000Z",
            "2026-08-29T14:00:00.000Z",
        ])
        self.assertFalse(taken & set(slots))

    def test_taken_may_be_any_iterable(self):
        slots = planly.plan_slots(1, publish_cfg(), now=local(hour=8),
                                  taken=["2026-08-29T02:00:00.000Z"])
        self.assertEqual(slots, ["2026-08-29T05:00:00.000Z"])


class SpreadMode(unittest.TestCase):

    def test_steps_by_gap_minutes_from_the_first_time(self):
        cfg = publish_cfg(mode="spread", gap_minutes=120)
        slots = planly.plan_slots(4, cfg, now=local(hour=8))
        self.assertEqual(slots, [
            "2026-08-29T02:00:00.000Z",   # 09:00 local
            "2026-08-29T04:00:00.000Z",   # 11:00
            "2026-08-29T06:00:00.000Z",   # 13:00
            "2026-08-29T08:00:00.000Z",   # 15:00
        ])

    def test_the_rest_of_the_times_list_is_ignored(self):
        # `times` still holds 12:00, 15:00 ... but only times[0] is a start point.
        cfg = publish_cfg(mode="spread", gap_minutes=50)
        slots = planly.plan_slots(3, cfg, now=local(hour=8))
        self.assertEqual(slots, [
            "2026-08-29T02:00:00.000Z",   # 09:00 local
            "2026-08-29T02:50:00.000Z",   # 09:50
            "2026-08-29T03:40:00.000Z",   # 10:40
        ])
        self.assertIn("12:00", cfg["times"])
        self.assertNotIn("2026-08-29T05:00:00.000Z", slots)

    def test_lead_time_pushes_the_start_forward(self):
        cfg = publish_cfg(mode="spread", gap_minutes=120)
        slots = planly.plan_slots(2, cfg, now=local(hour=12))
        self.assertEqual(slots, [
            "2026-08-29T06:00:00.000Z",   # 13:00 local, first step past now+30m
            "2026-08-29T08:00:00.000Z",
        ])

    def test_taken_slots_are_skipped(self):
        cfg = publish_cfg(mode="spread", gap_minutes=120)
        slots = planly.plan_slots(2, cfg, now=local(hour=8),
                                  taken={"2026-08-29T04:00:00.000Z"})
        self.assertEqual(slots, ["2026-08-29T02:00:00.000Z",
                                 "2026-08-29T06:00:00.000Z"])


class EdgeCases(unittest.TestCase):

    def test_count_zero_returns_nothing(self):
        self.assertEqual(planly.plan_slots(0, publish_cfg(), now=local()), [])
        self.assertEqual(planly.plan_slots(-3, publish_cfg(), now=local()), [])
        cfg = publish_cfg(mode="spread")
        self.assertEqual(planly.plan_slots(0, cfg, now=local()), [])

    def test_empty_times_falls_back_to_nine_am(self):
        for times in ([], [""], None):
            with self.subTest(times=times):
                slots = planly.plan_slots(2, publish_cfg(times=times), now=local(hour=1))
                self.assertEqual(slots, ["2026-08-29T02:00:00.000Z",
                                         "2026-08-30T02:00:00.000Z"])

    def test_missing_times_key_falls_back_to_nine_am(self):
        cfg = publish_cfg()
        del cfg["times"]
        self.assertEqual(planly.plan_slots(1, cfg, now=local(hour=1)),
                         ["2026-08-29T02:00:00.000Z"])

    def test_hour_only_entry_is_read_as_the_top_of_the_hour(self):
        slots = planly.plan_slots(1, publish_cfg(times=["7"]), now=local(hour=1))
        self.assertEqual(slots, ["2026-08-29T00:00:00.000Z"])

    def test_no_free_slot_within_the_horizon_raises(self):
        cfg = publish_cfg(times=["09:00"])          # 1 a day, 120 days of headroom
        with self.assertRaises(PlanlyError) as caught:
            planly.plan_slots(200, cfg, now=local())
        self.assertIn("No free slot", str(caught.exception))

    def test_spread_that_cannot_be_laid_out_raises(self):
        cfg = publish_cfg(mode="spread", gap_minutes=120)
        with self.assertRaises(PlanlyError) as caught:
            planly.plan_slots(20001, cfg, now=local())
        self.assertIn("Could not lay out", str(caught.exception))
