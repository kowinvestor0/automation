"""The drop folders: one per account, and the folder name is the routing.

Nothing about the factories needs this. It exists so a person can put their own
clip into a folder named after an account and have it post there, which is the
one instruction that survives being given on a phone.
"""
import time
import unittest

from hub import library, publish
from hub import state as hub_state
from tests._support import IsolatedHome, channels, local, publish_cfg
from tests.test_publish import FakePlanly

OLD = time.time() - 3600          # old enough to count as finished copying


class Folders(IsolatedHome):

    def setUp(self):
        super().setUp()
        self.root = self.tmp / "dang-bai"
        self.channels = channels("a", "b")

    def test_one_folder_per_account_plus_a_done_folder(self):
        made = library.ensure_folders(self.root, self.channels)
        self.assertEqual(sorted(made), ["A", "B"])
        for name in ("A", "B"):
            self.assertTrue((self.root / name).is_dir())
            self.assertTrue((self.root / name / library.DONE_DIR).is_dir())

    def test_running_it_again_makes_nothing_new(self):
        library.ensure_folders(self.root, self.channels)
        self.assertEqual(library.ensure_folders(self.root, self.channels), [])

    def test_an_existing_folder_is_left_alone(self):
        (self.root / "A").mkdir(parents=True)
        (self.root / "A" / "keep.mp4").write_bytes(b"x")
        library.ensure_folders(self.root, self.channels)
        self.assertTrue((self.root / "A" / "keep.mp4").exists())


class Scanning(IsolatedHome):

    def setUp(self):
        super().setUp()
        self.root = self.tmp / "dang-bai"
        self.channels = channels("a", "b")
        library.ensure_folders(self.root, self.channels)

    def drop(self, folder, name, age=OLD):
        path = self.root / folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"video")
        import os
        os.utime(path, (age, age))
        return path

    def test_a_video_is_found_under_its_account(self):
        self.drop("A", "clip.mp4")
        waiting, unknown = library.scan(self.root, self.channels, log=lambda *_: None)
        self.assertEqual(list(waiting), ["a"])
        self.assertEqual(waiting["a"][0].name, "clip.mp4")
        self.assertEqual(unknown, [])

    def test_the_folder_name_is_matched_case_insensitively(self):
        (self.root / "aBc").mkdir(exist_ok=True)
        self.drop("a", "clip.mp4")
        waiting, _ = library.scan(self.root, channels("A"), log=lambda *_: None)
        self.assertEqual(list(waiting), ["A"])

    def test_non_videos_are_ignored(self):
        self.drop("A", "notes.txt")
        waiting, _ = library.scan(self.root, self.channels, log=lambda *_: None)
        self.assertEqual(waiting, {})

    def test_a_file_still_being_copied_is_left_for_next_time(self):
        self.drop("A", "half.mp4", age=time.time())
        waiting, _ = library.scan(self.root, self.channels, log=lambda *_: None)
        self.assertEqual(waiting, {})

    def test_the_done_folder_is_not_rescanned(self):
        self.drop(f"A/{library.DONE_DIR}", "already.mp4")
        waiting, _ = library.scan(self.root, self.channels, log=lambda *_: None)
        self.assertEqual(waiting, {})

    def test_an_unmatched_folder_with_videos_is_reported(self):
        self.drop("SomeoneElse", "clip.mp4")
        _, unknown = library.scan(self.root, self.channels, log=lambda *_: None)
        self.assertEqual(unknown, ["SomeoneElse"])

    def test_an_unmatched_folder_with_nothing_in_it_is_not_reported(self):
        # The root may sit beside unrelated folders; naming them all would bury
        # the one report that matters.
        (self.root / "Random source material").mkdir()
        _, unknown = library.scan(self.root, self.channels, log=lambda *_: None)
        self.assertEqual(unknown, [])

    def test_a_missing_root_is_empty_not_an_error(self):
        self.assertEqual(library.scan(self.tmp / "nope", self.channels), ({}, []))


class PostingFromFolders(IsolatedHome):

    def setUp(self):
        super().setUp()
        self.root = self.tmp / "dang-bai"
        self.channels = channels("a", "b", "c")
        library.ensure_folders(self.root, self.channels)
        self.fake = FakePlanly(self.channels).patch(self)
        self.log = []

    def drop(self, folder, name):
        import os
        path = self.root / folder / name
        path.write_bytes(b"video")
        os.utime(path, (OLD, OLD))
        return path

    def videos(self):
        waiting, _ = library.scan(self.root, self.channels, log=lambda *_: None)
        return library.unposted(library.as_videos(waiting, self.channels))

    def test_each_video_goes_to_the_account_whose_folder_it_was_in(self):
        self.drop("A", "one.mp4")
        self.drop("C", "two.mp4")
        result = publish.publish(self.videos(), publish_cfg(dry_run=False),
                                 "planly-key", log=self.log.append, now=local(hour=8))
        landed = {e["video"]: e["channel_id"] for e in result.entries}
        self.assertEqual(landed["one"], "a")
        self.assertEqual(landed["two"], "c")

    def test_the_rotation_is_not_touched_because_nothing_was_dealt(self):
        self.drop("A", "one.mp4")
        publish.publish(self.videos(), publish_cfg(dry_run=False), "planly-key",
                        log=self.log.append, now=local(hour=8))
        self.assertEqual(hub_state.channel_start("default"), 0)

    def test_idle_accounts_are_not_warned_about(self):
        # Two accounts having nothing to post is normal here - only the folders
        # with files in them were ever meant to post.
        self.drop("A", "one.mp4")
        result = publish.publish(self.videos(), publish_cfg(dry_run=False),
                                 "planly-key", log=self.log.append, now=local(hour=8))
        self.assertFalse(any("none this round" in w for w in result.warnings))

    def test_a_posted_file_moves_into_the_done_folder(self):
        path = self.drop("A", "one.mp4")
        videos = self.videos()
        library.mark_done(videos[0], log=lambda *_: None)
        self.assertFalse(path.exists())
        self.assertTrue((self.root / "A" / library.DONE_DIR / "one.mp4").exists())

    def test_a_posted_file_is_not_offered_again(self):
        self.drop("A", "one.mp4")
        library.mark_done(self.videos()[0], move=False, log=lambda *_: None)
        self.assertEqual(self.videos(), [])

    def test_a_name_clash_in_the_done_folder_does_not_lose_a_file(self):
        (self.root / "A" / library.DONE_DIR / "one.mp4").write_bytes(b"older")
        self.drop("A", "one.mp4")
        library.mark_done(self.videos()[0], log=lambda *_: None)
        kept = list((self.root / "A" / library.DONE_DIR).glob("*.mp4"))
        self.assertEqual(len(kept), 2)

    def test_the_title_is_made_readable_from_the_filename(self):
        self.drop("A", "my_great-clip.mp4")
        self.assertEqual(self.videos()[0]["title"], "my great clip")


if __name__ == "__main__":
    unittest.main()
