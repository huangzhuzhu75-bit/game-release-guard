---
name: steam-release-guard
description: 在用户自己的 Unity 6 或 Unreal Engine 5 Windows/Steam 工程中，用 Steam Release Guard 预览发布配置、审查代码与资源暴露、分离私有符号、检查发布包并安全回滚。适用于发布前检查或恢复失败适配；不负责管理 AI、上传 Steam 或承诺防破解。
---

# Steam Release Guard 操作 Skill

本文件也是通用 Markdown 操作说明。下载完整仓库后可以直接交给具备本地文件/终端能力的 AI 阅读，不需要安装 Skill、Agent、MCP 或 Hooks。没有文件/终端能力的 AI 只能提供说明，不能声称已经执行。

## 功能与支持范围

工具是 Python 3.10+ 标准库 CLI、Tkinter GUI、HTML/JSON 报告；不自动安装运行时或引擎。Unity 6（6000.x）和 Unreal 5.x 的 Windows 发布基础适配可用。GUID/自编译 UE 关联或其他版本只能先审查，自动修改会拒绝。

当前为 `0.2.0.dev0` / V2 P0 验收候选。没有混淆器、元数据保护器、IoStore 加密适配、服务端逻辑改写或 SteamPipe 发布管理。P1—P4 不属于本阶段。

## 必须遵守的操作顺序

1. 确认仓库位置、用户工程目录、引擎精确版本和实际构建目录。读取 Unity `ProjectVersion.txt` 或 UE `.uproject`；不要因本机装了某版本就替换项目版本。先确认 Python 3.10+；缺失时告知，不自行安装。
2. 在工具仓库根目录执行 `plan` 或 `audit`，先读结果再修改。`plan` 不写工程；`audit` 会保存本地报告。版本不明、输入错误或已有未完成事务时停止相应写入。
3. 解释将修改的文件、输出目录、报告、完整备份位置、可取消阶段和恢复方法。关闭引擎和同步工具，保留原工程。每次有修改的 apply 必须先完成工程外的完整文件备份及核验；没有跳过开关。首次试用按 [完整备份流程](../../workflows/backup.md) 先恢复出新副本再适配，不擅自提交用户游戏工程。
4. 只有用户已授权该具体修改范围时才执行写操作；使用 `--yes` 表示这次明确授权，不能把示例中的参数当作授权。先运行 `--dry-run`；范围变化、冲突或新危险操作需重新确认。
5. 完成后检查 CLI 退出码、JSON `status`、事务状态与报告。提供改动文件、备份、SHA256 验证结果、FAIL/WARN/REVIEW/NOT_VERIFIED 和下一项人工验收。失败也要报告，不能只说“命令已执行”。

## 命令速查

以下命令在仓库根目录执行。示例目录是占位路径，先换成用户明确提供的真实路径。

```powershell
python -m steam_release_guard --version
python -m steam_release_guard plan 'D:/Games/MyGame' --json
python -m steam_release_guard audit 'D:/Games/MyGame' --json
python -m steam_release_guard apply 'D:/Games/MyGame' --dry-run --json
python -m steam_release_guard apply 'D:/Games/MyGame' --yes --json
python -m steam_release_guard audit 'D:/Games/MyGame' --build 'D:/Builds/MyGame-v1' --json
python -m steam_release_guard stage 'D:/Builds/MyGame-v1' --release 'D:/Release/MyGame-v1' --symbols 'D:/PrivateSymbols/MyGame-v1' --dry-run --json
python -m steam_release_guard rollback 'D:/Games/MyGame' --dry-run --json
```

其他实际入口：`backup`（完整工程文件备份）、`backup-verify`（核验副本）、`backup-restore`（恢复到新目录）、`build-script`（只生成脚本）、`stage-cleanup`（核验后清理失败副本）、`gui`。参数以仓库 `python -m steam_release_guard --help` 和各子命令 `--help` 为准。没有 `deploy`、`protect-all`、`steam-upload`、`resume` 命令。

- `--json` 输出单个 JSON 对象，含 schema/tool_version/command/status/result/error；不出现交互确认。`--progress` 可额外向 stderr 输出阶段事件。
- 写命令支持 `--dry-run` / `--yes`。不加 `--yes` 时，交互终端先显示预览并询问；非交互或 JSON 模式返回 `CONFIRMATION_REQUIRED`。
- 退出码：0 完成/预览；1 操作错误；2 自动检查阻断（或 `--fail-on-warnings` 命中）；3 尚未确认；130 取消。0、COMPLETE 都不等于 RELEASE_APPROVED。

## Unity 流程

按 [Unity 工作流](../../workflows/unity-release.md) 执行：识别 6000.x → plan/audit → 预览并授权 apply → 安装 Editor-only 构建适配器 → 用户核实 IL2CPP 模块/C++ 工具链与插件 → 生成、审阅并在授权后运行实际引擎构建 → stage → 对最终发布目录 audit → 实测启动、存档、插件、联机、离线和调试快捷键。

安装适配器不代表已有构建使用 IL2CPP。适配器拒绝自定义 Build Profile；不得绕过拒绝去丢失其场景/宏配置。引擎强退后检查原 PlayerSettings，不能把 Python 回滚当作引擎崩溃恢复。

## Unreal 流程

按 [Unreal 工作流](../../workflows/unreal-release.md) 执行：识别 UE 5.x → plan/audit → 预览并授权 Shipping/排除调试文件 → 根据需要单独决定 Pak 索引加密 → 生成准确版本 UAT 命令 → 实际打包 → stage/audit → 核对日志/配置覆盖及运行结果。

`--encrypt-pak-index` 仅使用已有合法非零 256-bit 密钥；不创建、不替换、不打印密钥。不能从 Pak 索引加密推断资源主体或 IoStore 已加密。

## 安全与发布包检查

按 [安全检查工作流](../../workflows/security-audit.md) 分开检查配置证据、源码候选和真正交付的发布包。先保留原始构建，再将符号复制到私有目录；原构建、发布副本、符号目录必须互不嵌套。失败暂存带 INCOMPLETE 标记，禁止作为发布结果。

调试文本扫描是候选检查，覆盖不了所有 Blueprint、Prefab、二进制插件或运行时入口。资源扩展名、归档存在、GameAssembly.dll/metadata 存在都不能证明防提取有效。工具报告中的局部 PASS 仅限该检查项。

## 回滚与中断

完整备份默认在工程同级 `<工程名>.srg-backups/<时间编号>/`，可用 `--backup-dir` 指定工程外目录；包含根目录内全部普通文件、隐藏文件和空目录，不跳过缓存。链接/连接点拒绝；外部依赖、系统环境、ACL/备用数据流等不保证包含。完整恢复仅到不存在的新目录，原工程和备份保留。具体命令、失败状态和权限要求见 [完整备份流程](../../workflows/backup.md)。

按 [回滚工作流](../../workflows/rollback.md) 先预览。apply/rollback 的全部目标和备份先校验；后续修改发生冲突就停止，不要加“强制覆盖”。备份在工程 `.steam-release-guard/backups/`，可能含敏感配置，不上传。

stage 独立保存私有 `srg-stage-journal.json`。本版选择安全清理，不支持断点续传。仅在全部文件/部分副本均可核验时清理失败输出；未知文件、修改过的文件或损坏日志需要人工处理。保留原构建。不要删除锁文件来解锁，崩溃后的 OS 锁会自动释放。

## 能力限制与风险确认

- IL2CPP、Shipping、索引加密、DRM 只能增加部分分析/复制成本；不保证防破解、防逆向或阻止资源提取。
- 保留私有符号用于崩溃分析。全资源加密、混淆和反篡改需独立兼容性/性能/补丁验证，本版不自动启用。
- 禁止擅自修改密钥、删除未知文件、覆盖原构建、上传源码/资产/凭据。已有明确授权仅适用于约定对象与范围。
- Steam DRM Wrapper 会上传 EXE 给 Valve；必须明确说明并获得该次上传授权。不要自动运行 DRM、SteamCMD 登录、测试分支上传或正式发行；本 Skill 不授予这些权限。
- 不把 REVIEW 或 NOT_VERIFIED 改成 PASS；缺少真实引擎、插件、存档、联机或 Steam 测试证据就保留待验证。只有人工发行审批可决定上线，本工具不会生成 RELEASE_APPROVED。
- 锁协调的是同一台主机上的本工具写任务，不阻止外部编辑器；操作前关闭编辑器。SHA256 日志校验不等于防恶意篡改签名；进程强退已纳入测试，断电/硬件故障不能保证恢复。

## AI 适配边界

只使用仓库内说明；不修改用户全局 AI 配置。没有 Agent 自动扫描/安装、AI 管理 GUI、权限中心、MCP/ACP/Hooks 管理器、本机 AI 监控或 AI 操作审计系统。

这个 `skills/` 路径是统一说明源，不能假设所有平台自动发现。Claude/Codex/Gemini 项目入口均指向本文件；原生发现与手动阅读是不同验收项。安装情况、官方格式依据与待验证项见 [AI 使用入口](../../AI-START.md)。
