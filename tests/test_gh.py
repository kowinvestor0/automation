"""hub.gh - the pieces that can be tested without a network.

`normalise_repo` is what stands between "I pasted the browser URL" and a 404,
so it is worth pinning down. Nothing in this file makes an HTTP request; the
two error tests deliberately pick the paths that fail before any call is made.
"""
import unittest

from hub import gh
from hub.gh import GitHubError


class NormaliseRepo(unittest.TestCase):

    def test_owner_name_is_already_right(self):
        self.assertEqual(gh.normalise_repo("owner/name"), "owner/name")

    def test_a_browse_url_becomes_owner_name(self):
        self.assertEqual(gh.normalise_repo("https://github.com/owner/name"),
                         "owner/name")

    def test_an_http_url_works_too(self):
        self.assertEqual(gh.normalise_repo("http://github.com/owner/name"),
                         "owner/name")

    def test_a_deep_link_keeps_only_the_repo(self):
        self.assertEqual(
            gh.normalise_repo("https://github.com/owner/name/actions/runs/12345"),
            "owner/name")

    def test_a_clone_url_loses_the_git_suffix(self):
        self.assertEqual(gh.normalise_repo("https://github.com/owner/name.git"),
                         "owner/name")
        self.assertEqual(gh.normalise_repo("owner/name.git"), "owner/name")

    def test_a_trailing_slash_is_dropped(self):
        self.assertEqual(gh.normalise_repo("https://github.com/owner/name/"),
                         "owner/name")
        self.assertEqual(gh.normalise_repo("owner/name/"), "owner/name")
        self.assertEqual(gh.normalise_repo("https://github.com/owner/name.git/"),
                         "owner/name")

    def test_surrounding_whitespace_is_stripped(self):
        self.assertEqual(gh.normalise_repo("  owner/name \n"), "owner/name")

    def test_empty_input_is_empty_output(self):
        for value in ("", "   ", None):
            with self.subTest(value=value):
                self.assertEqual(gh.normalise_repo(value), "")

    def test_a_bare_owner_is_left_as_is_for_the_api_to_reject(self):
        self.assertEqual(gh.normalise_repo("owner"), "owner")


class OfflineGuards(unittest.TestCase):
    """Both of these return before any HTTP call, which is what makes them
    testable - and what keeps the GUI responsive when nothing is configured."""

    def test_recent_runs_without_a_repo_explains_itself(self):
        with self.assertRaises(GitHubError) as caught:
            gh.recent_runs("")
        self.assertIn("No repository configured", str(caught.exception))

    def test_check_token_without_a_repo_asks_for_one(self):
        ok, message = gh.check_token("", "some-token")
        self.assertFalse(ok)
        self.assertIn("repository", message.lower())

    def test_dispatch_without_a_token_says_which_scope_is_needed(self):
        with self.assertRaises(GitHubError) as caught:
            gh.dispatch("owner/name", "videos.yml", "")
        self.assertIn("workflow", str(caught.exception))


class Label(unittest.TestCase):

    def test_the_common_outcomes_have_a_badge(self):
        self.assertIn("success", gh.label({"status": "completed",
                                           "conclusion": "success"}))
        self.assertIn("failed", gh.label({"status": "completed",
                                          "conclusion": "failure"}))
        self.assertIn("cancelled", gh.label({"status": "completed",
                                             "conclusion": "cancelled"}))
        self.assertIn("running", gh.label({"status": "in_progress",
                                           "conclusion": None}))
        self.assertIn("queued", gh.label({"status": "queued", "conclusion": ""}))

    def test_an_unknown_pair_falls_back_to_the_raw_words(self):
        self.assertEqual(gh.label({"status": "completed",
                                   "conclusion": "timed_out"}),
                         "completed timed_out")


class SecretSyncGuards(unittest.TestCase):

    def test_get_public_key_without_token_raises(self):
        with self.assertRaises(GitHubError) as caught:
            gh.get_public_key("owner/name", "")
        self.assertIn("token", str(caught.exception).lower())

    def test_sync_secrets_without_repo_raises(self):
        with self.assertRaises(GitHubError) as caught:
            gh.sync_secrets("", "token", {"KEY": "VAL"})
        self.assertIn("No repository configured", str(caught.exception))

    def test_sync_secrets_without_token_raises(self):
        with self.assertRaises(GitHubError) as caught:
            gh.sync_secrets("owner/name", "", {"KEY": "VAL"})
        self.assertIn("token", str(caught.exception).lower())

    def test_update_file_without_token_raises(self):
        with self.assertRaises(GitHubError) as caught:
            gh.update_file("owner/name", "", "file.json", "{}", "commit")
        self.assertIn("token", str(caught.exception).lower())
