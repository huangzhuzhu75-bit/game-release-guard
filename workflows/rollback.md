# 回滚与失败暂存清理

先阅读 [统一操作规则](../skills/steam-release-guard/SKILL.md)。核实工程、版本、原始路径与恢复日志，关闭编辑器。不要删除备份、修改日志哈希或删除锁文件绕过冲突。在工具仓库根目录执行下面命令，替换占位目录。

## 工程适配回滚

先 plan 或 audit 了解当前状态；随后预览最近一次未回滚事务的全部目标：

```powershell
python -m steam_release_guard audit 'D:/Games/MyGame' --json
python -m steam_release_guard rollback 'D:/Games/MyGame' --dry-run --json
```

确认预览中的恢复日志与文件属于本次工程。用户已授权恢复范围后：

```powershell
python -m steam_release_guard rollback 'D:/Games/MyGame' --yes --json
python -m steam_release_guard audit 'D:/Games/MyGame' --json
```

回滚前核验全部目标与备份。原文件必须处于已知修改前/修改后状态；发现后来人工修改就停止，不能自行覆盖或强制回滚。旧 schema 1 记录支持恢复但没有新日志封印，仍逐文件检查。schema 2 校验版本、数量、状态、路径、重复项和 SHA256；这不是防恶意伪造签名。

回滚写入阶段不可取消。文件占用、磁盘写满或进程退出后保留恢复记录，解决问题再运行相同预览与回滚；已恢复的文件可识别。不要把恢复失败宣称为完成。新增空目录及引擎生成的 `.meta` 可能保留，不删除用途不明文件。

Python 工具回滚不能替代存档、引擎构建输出、Unity 崩溃后 PlayerSettings 或 Steam 发布版本的恢复。

## 清理 INCOMPLETE 暂存副本

本版提供安全清理，**没有 resume 命令**。先对相应工程/失败发布目录 audit，并保存私有目录 `srg-stage-journal.json`。原构建不可删除或修改，部分副本可能需要与它进行前缀验证。

```powershell
python -m steam_release_guard audit 'D:/Games/MyGame' --build 'D:/Release/MyGame-v1' --json
python -m steam_release_guard stage-cleanup 'D:/PrivateSymbols/MyGame-v1/srg-stage-journal.json' --dry-run --json
```

解释预览中将删除的已核验副本，用户授权后再执行：

```powershell
python -m steam_release_guard stage-cleanup 'D:/PrivateSymbols/MyGame-v1/srg-stage-journal.json' --yes --json
```

只清理失败事务的可核验文件、对应部分副本和已知空子目录，保留原构建及私有事务日志。发现未知文件、修改过的副本、无法确认的 partial、损坏日志/标记时停止，交给人工处理。已完成的发布目录不能通过此命令删除。清理后的 journal 为 CLEANED，私有目录仍非空；下一次 stage 使用新的发布与符号目录。

原始备份准备阶段若被强制终止，可能留下尚无 manifest 的私有准备目录；不自动删它。检查原工程未被改写，保留该目录供人工审查。若磁盘满到无法保存新的失败状态，使用最后一个有效的 prepared/applying/rolling_back 或 stage 日志，不手工将它改为完成。

完成后报告：恢复/清理状态、实际处理文件、保留位置、冲突或未知文件、随后 audit 结果与未验证事项。
