from dataclasses import dataclass


DEFAULT_INVALID_CHARS = set('<>:"\\|?*')
HEAD_PREFIX = "refs/heads/"


class GitCommandError(RuntimeError):
    """Raised when an underlying git command fails."""

    def __init__(self, message: str, returncode: int | None = None):
        super().__init__(message)
        self.returncode = returncode


@dataclass(frozen=True)
class RefSpecUpdatePlan:
    existing: list[str]
    to_add: list[str]


@dataclass(frozen=True)
class GuardResult:
    incompatible_branches: list[str]
    plan: RefSpecUpdatePlan
    applied: bool
    fetched: bool


def branch_name_from_head_ref(ref: str) -> str:
    if not ref.startswith(HEAD_PREFIX):
        raise ValueError(f"Not a branch head ref: {ref}")
    return ref[len(HEAD_PREFIX) :]


def has_windows_invalid_chars(branch_name: str, invalid_chars: set[str] | None = None) -> bool:
    invalid = DEFAULT_INVALID_CHARS if invalid_chars is None else invalid_chars
    return any(char in invalid for char in branch_name)


def find_windows_incompatible_branches(ls_remote_output: str) -> list[str]:
    branches: list[str] = []
    for line in ls_remote_output.splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        if not ref.startswith(HEAD_PREFIX):
            continue
        branch = branch_name_from_head_ref(ref)
        if has_windows_invalid_chars(branch):
            branches.append(branch)
    return branches


def build_negative_refspec(branch_name: str) -> str:
    return f"^{HEAD_PREFIX}{branch_name}"


def default_fetch_refspec(remote: str) -> str:
    return f"+refs/heads/*:refs/remotes/{remote}/*"


def plan_fetch_refspec_updates(
    remote: str,
    current_fetch_refspecs: list[str],
    incompatible_branches: list[str],
) -> RefSpecUpdatePlan:
    wanted = [default_fetch_refspec(remote)]
    wanted.extend(build_negative_refspec(branch) for branch in incompatible_branches)

    current = set(current_fetch_refspecs)
    to_add = [refspec for refspec in wanted if refspec not in current]

    return RefSpecUpdatePlan(existing=current_fetch_refspecs, to_add=to_add)


def guard_repository(remote: str, runner, apply: bool = False, fetch: bool = False) -> GuardResult:
    ls_remote_output = runner.git(["ls-remote", "--heads", remote])
    incompatible_branches = find_windows_incompatible_branches(ls_remote_output)

    try:
        config_output = runner.git(["config", "--get-all", f"remote.{remote}.fetch"])
    except GitCommandError as error:
        if error.returncode != 1:
            raise
        config_output = ""
    current_fetch_refspecs = [line for line in config_output.splitlines() if line.strip()]
    plan = plan_fetch_refspec_updates(remote, current_fetch_refspecs, incompatible_branches)

    applied = False
    if apply:
        for refspec in plan.to_add:
            runner.git(["config", "--add", f"remote.{remote}.fetch", refspec])
        applied = True

    fetched = False
    if fetch:
        runner.git(["fetch", "--prune", remote])
        fetched = True

    return GuardResult(
        incompatible_branches=incompatible_branches,
        plan=plan,
        applied=applied,
        fetched=fetched,
    )
