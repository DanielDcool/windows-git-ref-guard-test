import argparse
import subprocess
import sys
from collections.abc import Sequence
from typing import TextIO

from windows_git_ref_guard.core import GitCommandError, guard_repository


class SubprocessGitRunner:
    def git(self, args: list[str]) -> str:
        completed = subprocess.run(
            ["git", *args],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            message = completed.stderr.strip() or completed.stdout.strip()
            raise GitCommandError(message or f"git {' '.join(args)} failed", completed.returncode)
        return completed.stdout


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="windows-git-ref-guard",
        description="Exclude Windows-incompatible remote branch refs from local Git fetches.",
    )
    parser.add_argument("--remote", default="origin", help="Remote name to scan. Default: origin")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write missing remote fetch refspecs to local .git/config.",
    )
    parser.add_argument(
        "--fetch",
        action="store_true",
        help="Run git fetch --prune after applying the refspec updates.",
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    runner=None,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.fetch and not args.apply:
        print("--fetch requires --apply so the guard rules are written before fetching.", file=stderr)
        return 2

    git_runner = SubprocessGitRunner() if runner is None else runner

    try:
        result = guard_repository(args.remote, git_runner, apply=args.apply, fetch=args.fetch)
    except GitCommandError as error:
        print(f"Git command failed: {error}", file=stderr)
        return 1

    if not result.incompatible_branches:
        print(f"No Windows-incompatible remote branches found on {args.remote}.", file=stdout)
        return 0

    print("Windows-incompatible remote branches:", file=stdout)
    for branch in result.incompatible_branches:
        print(f"  - {branch}", file=stdout)

    if result.plan.to_add:
        mode = "applied" if args.apply else "dry-run"
        print(f"\nFetch refspec updates ({mode}):", file=stdout)
        for refspec in result.plan.to_add:
            print(f"  git config --add remote.{args.remote}.fetch {refspec}", file=stdout)
    else:
        print("\nLocal fetch refspecs already include the needed guard rules.", file=stdout)

    if result.fetched:
        print(f"\nRan git fetch --prune {args.remote}.", file=stdout)
    elif not args.apply:
        print("\nRun again with --apply to write these local-only guard rules.", file=stdout)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
