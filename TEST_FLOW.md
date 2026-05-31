# Test Flow

This repository is used to verify `windows_git_ref_guard` on Windows.

Phase 1:

```bat
git clone git@github.com:DanielDcool/windows-git-ref-guard-test.git
cd windows-git-ref-guard-test
git fetch --prune origin
```

Expected result: clone and fetch succeed.

Phase 2 starts after a Windows-incompatible remote branch is added.

Expected failing branch:

```text
2025feature/mantis-0021568-edm程式優化，將CSS-Code移出<div>
```

Run the guard:

```bat
python -m windows_git_ref_guard --apply --fetch
```

Expected result: the guard adds a local negative refspec and fetch succeeds.
