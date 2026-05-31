# Windows Git Ref Guard

这个小工具用于解决 Windows 拉取 Git 仓库时，远端分支名包含 Windows 文件名非法字符导致的 fetch/pull 失败。

它只修改当前本地仓库的 `.git/config`，不会修改远端分支，也不会删除远端分支。

## 解决的问题

例如远端存在这样的分支：

```text
origin/2025feature/mantis-0021568-edm程式優化，將CSS-Code移出<div>
```

Windows 不能创建包含 `<` 或 `>` 的本地 ref 文件，所以 Git for Windows 会报类似错误：

```text
Unable to create .../.git/refs/remotes/origin/...<div>.lock: Invalid argument
```

本工具会扫描远端分支，把 Windows 不兼容的分支加入本地 fetch 排除规则：

```text
^refs/heads/2025feature/mantis-0021568-edm程式優化，將CSS-Code移出<div>
```

## 使用方式

在目标仓库根目录执行：

```bat
python -m windows_git_ref_guard
```

默认是 dry-run，只显示将要添加的本地配置，不会写入。

确认无误后执行：

```bat
python -m windows_git_ref_guard --apply --fetch
```

也可以使用仓库里的 Windows 启动脚本：

```bat
windows-git-ref-guard.cmd --apply --fetch
```

如果远端不是 `origin`：

```bat
python -m windows_git_ref_guard --remote upstream --apply --fetch
```

## 和 SourceTree 配合

先在仓库目录执行一次：

```bat
python -m windows_git_ref_guard --apply --fetch
```

之后 SourceTree 的拉取按钮会继续使用同一个本地 `.git/config`，因此会自动跳过这些 Windows 不兼容的远端分支。

也可以在 SourceTree 里配置 Custom Action，命令指向：

```bat
windows-git-ref-guard.cmd
```

参数填：

```bat
--apply --fetch
```

## 不会做什么

- 不会删除远端分支。
- 不会重命名远端分支。
- 不会修改代码文件。
- 不会解决已经被 Windows 文件系统禁止写入的其他路径问题。

## Windows 分支名风险字符

Windows 文件名不支持这些字符：

```text
< > : " \ | ? *
```
