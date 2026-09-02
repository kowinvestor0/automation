"""Which stream of videos posts to which accounts.

Fifteen TikTok accounts, two factories, and several niches inside each. Without
routing they all share one pool, so a Spanish video lands on an English channel
purely by where the deal happened to stop. A route pins a source to a set of
accounts; anything unrouted keeps the old account-wide behaviour.
"""
import unittest
from unittest import mock

from hub import publish
from hub import state as hub_state
from tests._support import channels, local, publish_cfg
from tests.test_publish import FactoryOutput, FakePlanly


class RouteLookup(unittest.TestCase):

    def cfg(self, **over):
        return publish_cfg(**over)

    def test_no_routes_falls_back_to_the_account_wide_list(self):
        ids, route = publish.route_for(self.cfg(channels=["a", "b"]), "us", "humor")
        self.assertEqual(ids, ["a", "b"])
        self.assertEqual(route, "default")

    def test_a_factory_route_wins_over_the_fallback(self):
        cfg = self.cfg(channels=["a"], routes={"us": ["b", "c"]})
        self.assertEqual(publish.route_for(cfg, "us"), (["b", "c"], "us"))

    def test_the_other_factory_still_falls_back(self):
        cfg = self.cfg(channels=["a"], routes={"us": ["b"]})
        self.assertEqual(publish.route_for(cfg, "mx"), (["a"], "default"))

    def test_a_niche_route_beats_its_factory_route(self):
        cfg = self.cfg(routes={"us": ["b"], "us:humor": ["z"]})
        self.assertEqual(publish.route_for(cfg, "us", "humor"), (["z"], "us:humor"))

    def test_a_different_niche_uses_the_factory_route(self):
        cfg = self.cfg(routes={"us": ["b"], "us:humor": ["z"]})
        self.assertEqual(publish.route_for(cfg, "us", "facts"), (["b"], "us"))

    def test_an_empty_route_is_treated_as_unset(self):
        # An empty list is what a half-filled form leaves behind; posting
        # nowhere is never what someone meant by it.
        cfg = self.cfg(channels=["a"], routes={"us": []})
        self.assertEqual(publish.route_for(cfg, "us"), (["a"], "default"))

    def test_no_factory_named_means_the_fallback(self):
        cfg = self.cfg(channels=["a"], routes={"us": ["b"]})
        self.assertEqual(publish.route_for(cfg), (["a"], "default"))

    def test_the_returned_list_is_a_copy(self):
        routes = {"us": ["b"]}
        ids, _ = publish.route_for(self.cfg(routes=routes), "us")
        ids.append("mutated")
        self.assertEqual(routes["us"], ["b"])


class RoutedPublishing(FactoryOutput):

    def setUp(self):
        super().setUp()
        self.fake = FakePlanly(channels("us1", "us2", "mx1", "mx2")).patch(self)

    def run_for(self, factory, folder, **over):
        videos = [v for v in self.collect() if v["folder"] == folder]
        cfg = publish_cfg(dry_run=False, routes={
            "us": ["us1", "us2"], "mx": ["mx1", "mx2"]}, **over)
        return publish.publish(videos, cfg, "planly-key", log=self.log.append,
                               now=local(hour=8), factory=factory)

    def test_english_videos_only_reach_english_accounts(self):
        result = self.run_for("us", self.folders[0])
        self.assertTrue(all(e["channel_id"] in ("us1", "us2")
                            for e in result.entries))
        self.assertEqual(result.route, "us")

    def test_spanish_videos_only_reach_spanish_accounts(self):
        result = self.run_for("mx", self.folders[0])
        self.assertTrue(all(e["channel_id"] in ("mx1", "mx2")
                            for e in result.entries))
        self.assertEqual(result.route, "mx")

    def test_each_route_keeps_its_own_place_in_its_own_list(self):
        # us posts once, which moves only the us pointer. mx must still start
        # at the top of its own list rather than being dragged along.
        self.run_for("us", self.folders[0])
        self.assertEqual(hub_state.channel_start("us"), 1)
        self.assertEqual(hub_state.channel_start("mx"), 0)

        result = self.run_for("mx", self.folders[1])
        self.assertEqual(result.entries[0]["channel_id"], "mx1")

    def test_a_route_naming_an_unknown_channel_warns_but_still_posts(self):
        videos = [v for v in self.collect() if v["folder"] == self.folders[0]]
        cfg = publish_cfg(dry_run=False, routes={"us": ["us1", "ghost"]})
        result = publish.publish(videos, cfg, "planly-key", log=self.log.append,
                                 now=local(hour=8), factory="us")
        self.assertTrue(any("ghost" in w for w in result.warnings))
        self.assertEqual(result.entries[0]["channel_id"], "us1")

    def test_a_route_whose_channels_have_all_gone_is_an_error(self):
        videos = [v for v in self.collect() if v["folder"] == self.folders[0]]
        cfg = publish_cfg(dry_run=False, routes={"us": ["ghost"]})
        result = publish.publish(videos, cfg, "planly-key", log=self.log.append,
                                 now=local(hour=8), factory="us")
        self.assertEqual(result.scheduled, 0)
        self.assertTrue(any("no channel to post to" in e for e in result.errors))

    def test_the_route_name_reaches_the_run_record(self):
        result = self.run_for("us", self.folders[0])
        self.assertEqual(result.as_dict()["route"], "us")

    def test_an_unrouted_factory_still_posts_account_wide(self):
        videos = [v for v in self.collect() if v["folder"] == self.folders[0]]
        cfg = publish_cfg(dry_run=False, routes={"us": ["us1"]})
        result = publish.publish(videos, cfg, "planly-key", log=self.log.append,
                                 now=local(hour=8), factory="mx")
        self.assertEqual(result.route, "default")
        self.assertEqual(result.scheduled, 1)

    def test_run_for_factory_passes_the_factory_through(self):
        # run_for_factory bails before publishing when there is no key, so the
        # isolated home needs one before the call can be observed at all.
        with mock.patch.object(publish, "secret", return_value="k" * 40):
            with mock.patch.object(publish, "publish") as spy:
                publish.run_for_factory(
                    self.factory, publish_cfg(enabled=True),
                    log=self.log.append, factory="us", niche="humor")
        self.assertEqual(spy.call_args.kwargs["factory"], "us")
        self.assertEqual(spy.call_args.kwargs["niche"], "humor")




class RepeatedTopicsAreHeldBack(FactoryOutput):
    """The bank recycles in under two days at full volume; a repeat must wait."""

    def setUp(self):
        super().setUp()
        self.fake = FakePlanly(channels("a", "b", "c")).patch(self)

    def videos(self, *topic_ids):
        return [{"folder": f"f{i}", "title": f"v{i}", "topic_id": t,
                 "path": self.factory / "output" / "x.mp4"}
                for i, t in enumerate(topic_ids)]

    def test_a_topic_posted_recently_is_held(self):
        hub_state.remember_topics(["seen-one"])
        keep, held = publish.drop_repeats(self.videos("seen-one", "fresh"), 14,
                                          log=lambda *_: None)
        self.assertEqual([v["topic_id"] for v in keep], ["fresh"])
        self.assertEqual([v["topic_id"] for v in held], ["seen-one"])

    def test_an_old_enough_topic_comes_back(self):
        import datetime as dt
        long_ago = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=40)
        hub_state.remember_topics(["old-one"], now=long_ago)
        keep, held = publish.drop_repeats(self.videos("old-one"), 14,
                                          log=lambda *_: None)
        self.assertEqual(len(keep), 1)
        self.assertEqual(held, [])

    def test_a_video_with_no_topic_id_is_never_held(self):
        keep, held = publish.drop_repeats(self.videos(""), 14, log=lambda *_: None)
        self.assertEqual(len(keep), 1)
        self.assertEqual(held, [])

    def test_zero_days_switches_the_guard_off(self):
        hub_state.remember_topics(["seen-one"])
        keep, _ = publish.drop_repeats(self.videos("seen-one"), 0,
                                       log=lambda *_: None)
        self.assertEqual(len(keep), 1)

    def test_only_topics_that_actually_posted_are_recorded(self):
        self.assertEqual(hub_state.recent_topics(14), set())

if __name__ == "__main__":
    unittest.main()
