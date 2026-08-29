"""hub.state - the memory that survives a wiped CI runner.

Two things matter here. Booked slots must stay deduped and sorted, because the
next run subtracts them from the calendar; and a damaged file must read as
"nothing known yet" rather than take the whole run down with it.
"""
import datetime as dt
import unittest

from tests._support import IsolatedHome
from hub import state


def iso(day, hour):
    return f"2026-08-{day:02d}T{hour:02d}:00:00.000Z"


class Isolation(IsolatedHome):

    def test_the_state_file_lives_in_the_tempdir(self):
        self.assertEqual(state.path().parent, self.tmp)
        self.assertEqual(state.path().name, "state.json")

    def test_no_file_means_nothing_known_yet(self):
        self.assertEqual(state.load(), {})
        self.assertEqual(state.taken_slots("ch-a"), set())
        self.assertEqual(state.all_taken_slots(), set())
        self.assertEqual(state.seen_videos(), set())


class Corruption(IsolatedHome):

    def test_a_corrupt_file_loads_as_empty(self):
        state.path().write_text("}{ garbage", encoding="utf-8")
        self.assertEqual(state.load(), {})
        self.assertEqual(state.taken_slots("ch-a"), set())
        self.assertEqual(state.seen_videos(), set())

    def test_a_file_holding_the_wrong_shape_loads_as_empty(self):
        state.path().write_text('["not", "a", "mapping"]', encoding="utf-8")
        self.assertEqual(state.load(), {})

    def test_an_empty_file_loads_as_empty(self):
        state.path().write_text("", encoding="utf-8")
        self.assertEqual(state.load(), {})


class RememberSlots(IsolatedHome):

    def test_slots_are_deduped_and_sorted(self):
        state.remember_slots("ch-a", [iso(30, 5), iso(29, 2), iso(30, 5), iso(29, 8)])
        self.assertEqual(sorted(state.taken_slots("ch-a")),
                         [iso(29, 2), iso(29, 8), iso(30, 5)])
        stored = state.load()["planly_taken"]["ch-a"]
        self.assertEqual(stored, [iso(29, 2), iso(29, 8), iso(30, 5)])

    def test_a_second_call_adds_to_the_same_channel(self):
        state.remember_slots("ch-a", [iso(29, 2)])
        state.remember_slots("ch-a", [iso(29, 5), iso(29, 2)])
        self.assertEqual(state.load()["planly_taken"]["ch-a"], [iso(29, 2), iso(29, 5)])

    def test_channels_are_kept_apart_but_pooled_by_all_taken_slots(self):
        state.remember_slots("ch-a", [iso(29, 2)])
        state.remember_slots("ch-b", [iso(29, 5)])
        self.assertEqual(state.taken_slots("ch-a"), {iso(29, 2)})
        self.assertEqual(state.taken_slots("ch-b"), {iso(29, 5)})
        self.assertEqual(state.all_taken_slots(), {iso(29, 2), iso(29, 5)})

    def test_a_passed_state_is_edited_in_memory_and_not_written(self):
        st = {}
        state.remember_slots("ch-a", [iso(29, 2)], state=st)
        self.assertEqual(st["planly_taken"]["ch-a"], [iso(29, 2)])
        self.assertFalse(state.path().exists())

    def test_the_history_is_capped_keeping_the_newest(self):
        many = [f"2027-{m:02d}-{d:02d}T{h:02d}:00:00.000Z"
                for m in range(1, 13) for d in range(1, 29) for h in (2, 5, 8)]
        self.assertGreater(len(many), state.MAX_SLOTS_PER_CHANNEL)
        state.remember_slots("ch-a", many)
        kept = state.load()["planly_taken"]["ch-a"]
        self.assertEqual(len(kept), state.MAX_SLOTS_PER_CHANNEL)
        self.assertEqual(kept[-1], many[-1])
        self.assertEqual(kept, sorted(kept))


class ForgetPastSlots(IsolatedHome):

    def setUp(self):
        super().setUp()
        state.remember_slots("ch-a", [iso(28, 2), iso(29, 2), iso(30, 2)])
        state.remember_slots("ch-b", [iso(28, 23)])
        self.now = dt.datetime(2026, 8, 29, 12, 0, tzinfo=dt.timezone.utc)

    def test_only_slots_in_the_past_are_dropped(self):
        state.forget_past_slots(now=self.now)
        booked = state.load()["planly_taken"]
        self.assertEqual(booked["ch-a"], [iso(30, 2)])
        self.assertEqual(booked["ch-b"], [])

    def test_a_future_slot_is_kept_even_on_the_same_day(self):
        state.remember_slots("ch-a", [iso(29, 16)])
        state.forget_past_slots(now=self.now)
        self.assertIn(iso(29, 16), state.taken_slots("ch-a"))

    def test_nothing_is_dropped_when_every_slot_is_ahead(self):
        state.forget_past_slots(
            now=dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc))
        self.assertEqual(len(state.load()["planly_taken"]["ch-a"]), 3)

    def test_it_survives_an_empty_state(self):
        state.path().unlink()
        self.assertEqual(state.forget_past_slots(now=self.now), {})


class SeenVideos(IsolatedHome):

    def test_remembered_names_come_back(self):
        state.remember_videos(["20260829-1200-us", "20260829-1201-us"])
        self.assertEqual(state.seen_videos(),
                         {"20260829-1200-us", "20260829-1201-us"})

    def test_a_second_call_appends(self):
        state.remember_videos(["a"])
        state.remember_videos(["b"])
        self.assertEqual(state.seen_videos(), {"a", "b"})

    def test_nothing_remembered_is_an_empty_set(self):
        state.remember_videos([])
        self.assertEqual(state.seen_videos(), set())

    def test_the_list_is_capped(self):
        cap = state.MAX_HISTORY * 4
        state.remember_videos([f"v{i}" for i in range(cap + 50)])
        published = state.load()["published"]
        self.assertEqual(len(published), cap)
        self.assertEqual(published[-1], f"v{cap + 49}")


class RunHistory(IsolatedHome):

    def test_runs_accumulate_and_the_last_one_is_easy_to_read(self):
        state.record_run({"factory": "us", "videos": 3})
        state.record_run({"factory": "mx", "videos": 2})
        st = state.load()
        self.assertEqual(len(st["runs"]), 2)
        self.assertEqual(st["last_run"], {"factory": "mx", "videos": 2})

    def test_the_history_is_capped(self):
        st = {}
        for i in range(state.MAX_HISTORY + 10):
            state.record_run({"n": i}, state=st)   # in memory: 410 disk writes is
        state.save(st)                             # not what is under test here
        self.assertEqual(len(st["runs"]), state.MAX_HISTORY)
        self.assertEqual(st["runs"][-1], {"n": state.MAX_HISTORY + 9})


class Persistence(IsolatedHome):

    def test_save_and_load_round_trip(self):
        state.save({"planly_taken": {"ch-a": [iso(29, 2)]}, "published": ["v0"]})
        st = state.load()
        self.assertEqual(st["planly_taken"]["ch-a"], [iso(29, 2)])
        self.assertEqual(st["published"], ["v0"])

    def test_no_temp_file_is_left_behind(self):
        state.save({"a": 1})
        self.assertEqual([p.name for p in self.tmp.glob("*.tmp")], [])
