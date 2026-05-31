import unittest

from windows_git_ref_guard.core import (
    DEFAULT_INVALID_CHARS,
    GitCommandError,
    branch_name_from_head_ref,
    build_negative_refspec,
    find_windows_incompatible_branches,
    guard_repository,
    plan_fetch_refspec_updates,
)


class WindowsGitRefGuardTests(unittest.TestCase):
    def test_branch_name_from_head_ref_keeps_slashes_and_unicode(self):
        ref = "refs/heads/2025feature/mantis-0021568-edm程式優化，將CSS-Code移出<div>"

        branch = branch_name_from_head_ref(ref)

        self.assertEqual(branch, "2025feature/mantis-0021568-edm程式優化，將CSS-Code移出<div>")

    def test_finds_only_windows_incompatible_branch_names(self):
        ls_remote_output = "\n".join(
            [
                "abc123\trefs/heads/develop",
                "def456\trefs/heads/feature/css-code-out-div",
                "789abc\trefs/heads/2025feature/mantis-0021568-edm程式優化，將CSS-Code移出<div>",
                "111222\trefs/heads/topic/contains|pipe",
                "333444\trefs/tags/v1.0.0",
            ]
        )

        branches = find_windows_incompatible_branches(ls_remote_output)

        self.assertEqual(
            branches,
            [
                "2025feature/mantis-0021568-edm程式優化，將CSS-Code移出<div>",
                "topic/contains|pipe",
            ],
        )

    def test_build_negative_refspec_targets_original_remote_head(self):
        branch = "2025feature/mantis-0021568-edm程式優化，將CSS-Code移出<div>"

        refspec = build_negative_refspec(branch)

        self.assertEqual(
            refspec,
            "^refs/heads/2025feature/mantis-0021568-edm程式優化，將CSS-Code移出<div>",
        )

    def test_plan_fetch_refspec_updates_adds_default_and_missing_negatives(self):
        current = [
            "+refs/heads/main:refs/remotes/origin/main",
            "^refs/heads/topic/already?blocked",
        ]
        incompatible = [
            "topic/already?blocked",
            "2025feature/mantis-0021568-edm程式優化，將CSS-Code移出<div>",
        ]

        plan = plan_fetch_refspec_updates("origin", current, incompatible)

        self.assertEqual(
            plan.to_add,
            [
                "+refs/heads/*:refs/remotes/origin/*",
                "^refs/heads/2025feature/mantis-0021568-edm程式優化，將CSS-Code移出<div>",
            ],
        )
        self.assertEqual(plan.existing, current)

    def test_invalid_character_set_matches_windows_filename_rules(self):
        self.assertEqual(DEFAULT_INVALID_CHARS, set('<>:"\\|?*'))

    def test_guard_repository_dry_run_does_not_write_config_or_fetch(self):
        runner = FakeGitRunner(
            {
                ("ls-remote", "--heads", "origin"): "\n".join(
                    [
                        "abc123\trefs/heads/develop",
                        "789abc\trefs/heads/2025feature/mantis-0021568-edm程式優化，將CSS-Code移出<div>",
                    ]
                ),
                ("config", "--get-all", "remote.origin.fetch"): "+refs/heads/*:refs/remotes/origin/*\n",
            }
        )

        result = guard_repository("origin", runner, apply=False, fetch=False)

        self.assertEqual(
            result.incompatible_branches,
            ["2025feature/mantis-0021568-edm程式優化，將CSS-Code移出<div>"],
        )
        self.assertEqual(
            result.plan.to_add,
            ["^refs/heads/2025feature/mantis-0021568-edm程式優化，將CSS-Code移出<div>"],
        )
        self.assertEqual(
            runner.calls,
            [
                ("ls-remote", "--heads", "origin"),
                ("config", "--get-all", "remote.origin.fetch"),
            ],
        )

    def test_guard_repository_apply_adds_missing_config_and_fetches(self):
        runner = FakeGitRunner(
            {
                ("ls-remote", "--heads", "origin"): "789abc\trefs/heads/topic/contains|pipe\n",
                ("config", "--get-all", "remote.origin.fetch"): "",
                ("config", "--add", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*"): "",
                ("config", "--add", "remote.origin.fetch", "^refs/heads/topic/contains|pipe"): "",
                ("fetch", "--prune", "origin"): "",
            }
        )

        result = guard_repository("origin", runner, apply=True, fetch=True)

        self.assertTrue(result.applied)
        self.assertTrue(result.fetched)
        self.assertEqual(
            runner.calls,
            [
                ("ls-remote", "--heads", "origin"),
                ("config", "--get-all", "remote.origin.fetch"),
                ("config", "--add", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*"),
                ("config", "--add", "remote.origin.fetch", "^refs/heads/topic/contains|pipe"),
                ("fetch", "--prune", "origin"),
            ],
        )


class FakeGitRunner:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def git(self, args):
        key = tuple(args)
        self.calls.append(key)
        if key not in self.responses:
            raise GitCommandError(f"Unexpected git command: {' '.join(args)}")
        return self.responses[key]


if __name__ == "__main__":
    unittest.main()
