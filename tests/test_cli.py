import io
import unittest
from unittest.mock import patch

from windows_git_ref_guard.cli import SubprocessGitRunner, main
from windows_git_ref_guard.core import GitCommandError


class CliTests(unittest.TestCase):
    def test_main_dry_run_reports_incompatible_branches_and_pending_refspecs(self):
        runner = FakeGitRunner(
            {
                ("ls-remote", "--heads", "origin"): "abc123\trefs/heads/topic/contains|pipe\n",
                ("config", "--get-all", "remote.origin.fetch"): "+refs/heads/*:refs/remotes/origin/*\n",
            }
        )
        stdout = io.StringIO()
        stderr = io.StringIO()

        exit_code = main(["--remote", "origin"], runner=runner, stdout=stdout, stderr=stderr)

        self.assertEqual(exit_code, 0)
        self.assertIn("topic/contains|pipe", stdout.getvalue())
        self.assertIn("^refs/heads/topic/contains|pipe", stdout.getvalue())
        self.assertIn("dry-run", stdout.getvalue())
        self.assertEqual(stderr.getvalue(), "")

    def test_main_apply_fetch_runs_requested_git_commands(self):
        runner = FakeGitRunner(
            {
                ("ls-remote", "--heads", "origin"): "abc123\trefs/heads/topic/contains|pipe\n",
                ("config", "--get-all", "remote.origin.fetch"): "",
                ("config", "--add", "remote.origin.fetch", "+refs/heads/*:refs/remotes/origin/*"): "",
                ("config", "--add", "remote.origin.fetch", "^refs/heads/topic/contains|pipe"): "",
                ("fetch", "--prune", "origin"): "",
            }
        )

        exit_code = main(["--apply", "--fetch"], runner=runner, stdout=io.StringIO(), stderr=io.StringIO())

        self.assertEqual(exit_code, 0)
        self.assertEqual(runner.calls[-1], ("fetch", "--prune", "origin"))

    def test_subprocess_runner_reports_missing_git_executable(self):
        runner = SubprocessGitRunner()

        with patch("windows_git_ref_guard.cli.subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaisesRegex(GitCommandError, "git executable was not found"):
                runner.git(["status"])


class FakeGitRunner:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def git(self, args):
        key = tuple(args)
        self.calls.append(key)
        if key not in self.responses:
            raise AssertionError(f"Unexpected git command: {' '.join(args)}")
        return self.responses[key]


if __name__ == "__main__":
    unittest.main()
