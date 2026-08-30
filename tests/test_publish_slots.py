"""Slot booking is per channel, not global.

Two channels posting different videos at 09:00 is the normal case here - it is
the whole point of same_time mode. So a slot is only spent for the channel that
used it. Treating it as spent everywhere makes each run start later than the
last, and after one day's worth of runs everything lands tomorrow.
"""
from unittest import mock

from hub import planly, publish
from hub import state as hub_state
from tests._support import channels, local, publish_cfg
from tests.test_publish import FactoryOutput, FakePlanly


class SlotsAreBookedPerChannel(FactoryOutput):

    def setUp(self):
        super().setUp()
        self.fake = FakePlanly(channels("ch1", "ch2", "ch3")).patch(self)

    def run_one(self, folder, start):
        """Publish a single video, as if one run had made exactly one."""
        videos = [v for v in self.collect() if v["folder"] == folder]
        with mock.patch.object(hub_state, "channel_start", return_value=start):
            return publish.publish(videos, publish_cfg(dry_run=False),
                                   "planly-key", log=self.log.append,
                                   now=local(hour=8))

    def test_a_second_channel_reuses_the_first_slot(self):
        first = self.run_one(self.folders[0], start=0)
        second = self.run_one(self.folders[1], start=1)

        self.assertEqual(first.entries[0]["channel_id"], "ch1")
        self.assertEqual(second.entries[0]["channel_id"], "ch2")
        # Different channels, different videos, same minute.
        self.assertEqual(first.entries[0]["publish_on"],
                         second.entries[0]["publish_on"])

    def test_the_same_channel_moves_to_the_next_slot(self):
        first = self.run_one(self.folders[0], start=0)
        second = self.run_one(self.folders[1], start=0)

        self.assertEqual(first.entries[0]["channel_id"], "ch1")
        self.assertEqual(second.entries[0]["channel_id"], "ch1")
        self.assertNotEqual(first.entries[0]["publish_on"],
                            second.entries[0]["publish_on"])

    def test_slots_stay_in_order_for_one_channel(self):
        first = self.run_one(self.folders[0], start=0)
        second = self.run_one(self.folders[1], start=0)
        self.assertLess(first.entries[0]["publish_on"],
                        second.entries[0]["publish_on"])

    def test_a_slot_is_only_remembered_for_the_channel_that_used_it(self):
        self.run_one(self.folders[0], start=0)
        used = hub_state.taken_slots("ch1")
        self.assertEqual(len(used), 1)
        self.assertEqual(hub_state.taken_slots("ch2"), set())

    def test_a_dry_run_books_nothing(self):
        videos = [v for v in self.collect() if v["folder"] == self.folders[0]]
        publish.publish(videos, publish_cfg(dry_run=True), "planly-key",
                        log=self.log.append, now=local(hour=8))
        self.assertEqual(hub_state.taken_slots("ch1"), set())


class TheRotationIsPersisted(FactoryOutput):

    def setUp(self):
        super().setUp()
        self.fake = FakePlanly(channels("ch1", "ch2", "ch3")).patch(self)

    def test_a_real_publish_moves_the_pointer_on(self):
        videos = self.collect()[:2]
        publish.publish(videos, publish_cfg(dry_run=False), "planly-key",
                        log=self.log.append, now=local(hour=8))
        self.assertEqual(hub_state.channel_start("default"),
                         planly.next_start(0, 2, 3))

    def test_a_dry_run_leaves_the_pointer_alone(self):
        publish.publish(self.collect()[:2], publish_cfg(dry_run=True),
                        "planly-key", log=self.log.append, now=local(hour=8))
        self.assertEqual(hub_state.channel_start("default"), 0)

    def test_mirror_does_not_move_the_pointer(self):
        # Everyone gets everything, so there is no place in a deal to resume.
        publish.publish(self.collect()[:2],
                        publish_cfg(dry_run=False, distribute="mirror"),
                        "planly-key", log=self.log.append, now=local(hour=8))
        self.assertEqual(hub_state.channel_start("default"), 0)
