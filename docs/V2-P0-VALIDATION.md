# V2 P0 验收记录

候选版本：0.2.0.dev0。基线 f87d8df / v0.1.0。范围仅 P0 + 轻量 Markdown；P1—P4 未实施，等待人工验收。

补充：2026-11-25 已完成 Windows 10 / Python 3.12 的真实工程副本往返、失败暂存/安全清理和原生 GUI/报告检查，详见 [本机验收记录](P0-ACCEPTANCE-20261125.md)。以下自动化测试的合成数据范围与此次本机检查分别记录。

后续完整工程备份功能和扩充至 74 项的测试另见 [完整备份验收记录](FULL-BACKUP-VALIDATION-20261125.md)；下方 56 项结果保留为此前候选的历史证据。

## 已实施

| 文件 | 变化 |
| --- | --- |
| `steam_release_guard/operations.py` | 本机 OS 写锁、进度/取消、磁盘空间预检、日志校验、统一无敏感内容异常 |
| `steam_release_guard/transactions.py` | 预览绑定、全部备份与目标校验、schema 2 状态、旧日志回滚、失败恢复 |
| `steam_release_guard/staging.py` | 独立复制事务、SHA256、INCOMPLETE 阻断、冲突感知安全清理 |
| `steam_release_guard/core.py` | 接入事务、原有审查规则保留、Windows 扩展路径、持久化写入 |
| `steam_release_guard/cli.py` | JSON、dry-run/yes、确认退出码、进度、stage-cleanup |
| `steam_release_guard/gui.py` | 写入预览确认、进度/取消、不可取消阶段、异常恢复、关闭等待 |
| `tests/test_transactions.py` / `tests/test_gui.py` | 子进程、故障恢复与界面异常测试；旧 GUI 测试只增加确认输入，原断言保留 |
| `tests/test_docs.py` | 文档命令使用真实 CLI parser 校验，链接/项目入口/Skill 结构检查 |
| `skills/` / `workflows/` / 三平台入口 / `AI-START.md` / README | 可下载直接阅读的统一操作说明；没有 AI 管理系统 |

## 验证方法与证据边界

- 本机 Windows / Python 3.12.14，标准库实现，不新增运行依赖。
- 原有 33 个测试全部保留。新增测试包含真实子进程锁竞争、强制结束 apply/stage、Windows 文件占用、中文长路径、磁盘不足/写满注入、日志损坏/重复条目、旧备份恢复、用户后续修改、取消及 GUI 意外异常。
- 磁盘故障采用可重复的 ENOSPC/剩余空间注入，不实际填满用户磁盘。强制结束使用真实子进程 kill；不是硬件断电试验。
- 自动化测试的工程/EXE/容器为合成数据，只验证工具文件行为，不证明 IL2CPP、Pak 或 IoStore 保护效果。补充本机检查使用真实工程副本及已有构建，未运行新引擎构建。
- 文档命令逐条交给当前 CLI parser；这证明命令语法一致，不能替代真实游戏执行。
- Claude Code、Gemini CLI 本机未安装，按用户决定使用 Markdown 兼容路线；不安装、不伪造客户端读取成功。
- Codex 0.171.0-alpha.13 已确认存在，采用 Markdown 阅读入口；原生 Skill 自动发现仍 NOT_VERIFIED。项目入口官方依据见 [AI-START](../AI-START.md)。

本机 56 个测试：55 通过，1 因 Windows 符号链接创建权限跳过。Actionlint 1.7.12、Gitleaks 8.30.1（无泄露命中）、PowerShell 解析和 Git diff 空白检查通过。Skill 生成器自带 `quick_validate.py` 因当前 Python 缺少 PyYAML 未运行成功；没有安装依赖，仓库自身的标准库测试已核对必要字段、链接和全部示例命令。不能把此项记作外部校验器通过。

远端 CI 与最终提交见交付的候选 PR；真实 Unity/UE/Steam 验收继续参照 [首版验证记录](VALIDATION.md)，不改写历史证据。

## 尚未解决及操作限制

1. Windows 本机缺少符号链接创建权限时对应旧测试跳过；Linux CI 运行该分支。真实引擎构建/插件/存档/联机/Steam 测试未在 P0 中执行。
2. OS 锁为同主机协作锁，保守串行化无工程参数的 stage；不是跨主机分布式锁，不能锁住外部编辑器。所有进程应共享同一锁目录。
3. stage 输出需支持同卷硬链接，例如 NTFS；不支持时保留失败记录，不退化为覆盖已有文件。
4. 初始日志尚未成功落盘就出现 ENOSPC/进程终止，可能留下无 manifest 的准备目录/临时记录，需要人工检查。断电与硬件故障无恢复保证。
5. 部分副本无法与原构建匹配、未知文件、后来编辑或损坏记录会阻止自动清理/回滚；这属于保留数据的设计，不提供强制删除开关。
6. SHA256 只能检测意外损坏，日志不含认证签名；不能抵抗有权限重写全部文件的恶意主体。
7. GUI 代码/回调测试不是完整视觉与可用性验收；本次补充的原生点击范围和未覆盖项详见本机验收记录。真实发布批准仍由人完成；COMPLETE/退出码 0 不是 RELEASE_APPROVED。

## 人工验收

先审阅 [实施前审查](V2-P0-REVIEW.md)、改动、测试证据和上述限制，在工程副本中走一遍 plan → apply → audit → rollback，以及失败 stage → cleanup。验收后再决定合并候选分支和启动下一阶段；本次不自动推进 P1。
