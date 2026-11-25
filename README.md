# Steam Release Guard

**给 Unity 6 / Unreal Engine 5 的 Windows、Steam 发布流程做可回滚的一键适配。**

本地桌面界面 + 无第三方 Python 依赖的 CLI。分别检查代码可读性、开发调试入口和资源暴露，生成 HTML / JSON 报告。不会联网扫描工程、收集遥测或上传游戏。

这是一套发布加固与检查工具，不是反盗版保证、资源加密壳或反作弊系统。当前 `0.2.0.dev0` 是 **V2 P0 验收候选**，在 v0.1.0 上补强事务稳定性，保留 CLI、GUI 和报告。P1—P4 尚未实施；完整引擎打包和 Steam 测试分支结果仍需真实项目验收。

## 独立游戏安全开发 Skill

唯一核心文件是 **[skills/steam-release-guard/SKILL.md](skills/steam-release-guard/SKILL.md)**，可以单独下载使用，不依赖本工具或 Python。新 Unity/Unreal 项目按其规则开发；已有工程默认只读检查，在对话中指出文件位置、风险和建议，不改代码、不生成报告。需要 CLI 适配时才读取本仓库的真实命令。

阅读 **[安装说明](skills/steam-release-guard/INSTALL.md)**、**[使用示例](skills/steam-release-guard/EXAMPLES.md)** 或 **[AI-START.md](AI-START.md)**。优先提供项目级 Claude Code、Codex、Gemini CLI 安装路径；其他工具直接读 Markdown。无需安装新的 AI 客户端，也不修改全局设置。

实际读取、四个合成场景、未验证平台和独立包校验见 [Skill 验收记录](docs/SKILL-VALIDATION-20261125.md)。这份 Skill 的知识指导不表示已给游戏实施深度保护。

项目提供 `AGENTS.md`、`CLAUDE.md`、`GEMINI.md` 入口和五份工作流：[完整备份](workflows/backup.md)、[Unity](workflows/unity-release.md)、[Unreal](workflows/unreal-release.md)、[安全与发布包检查](workflows/security-audit.md)、[回滚](workflows/rollback.md)。不支持原生 Skills 的工具直接阅读 Markdown；没有 AI 管理服务、工具扫描/安装、MCP/ACP/Hooks 管理器或全局配置修改。未安装客户端的实际读取不标为已验证。

## 双击使用

1. 下载并解压仓库；本机需有 **Python 3.10+，含 tkinter**。无需 `pip install`，无需管理员权限。引擎构建另需原工程对应的引擎、许可证和 Windows 构建组件。
2. 双击 **`Launch.cmd`**。如果自动寻找 Python 失败，把已有 `python.exe` 的完整路径写入 `.local/python-path.txt`，或设置进程环境变量 `SRG_PYTHON`。工具不会自行下载 Python。
3. 选择工程根目录，先点击“检查工程 / 发布包”或运行 `plan`。首次试用先关闭引擎和同步工具，点击 **完整备份**，完成后用 **恢复完整备份…** 创建新副本，再把“工程目录”切换到该副本。
4. 点击 **一键适配**，审阅修改范围与完整备份位置。工具先复制并核验所选工程的全部文件，成功后才开始适配；失败就停止。
5. 通过“生成构建脚本…”生成并运行对应版本的构建命令；Unity 也可直接使用新增的菜单入口。选择实际发布包，再执行检查。
6. 如需分离符号，选择三个互不嵌套的目录：原构建、空发布目录、空私有符号目录。复制并校验后，对新发布目录重新检查。

“一键”指配置适配、安装 Unity 构建入口和生成检查报告；它不会替你安装引擎、判断插件兼容性、打包上传 Steam 或批准游戏上线。

## 先保留完整工程，再尝试

每次有文件需要修改的 `apply` 都先创建独立的 **完整工程文件备份**，没有跳过备份开关。默认在工程旁的 `<工程名>.srg-backups/<时间编号>/`，也可用 GUI“备份位置…”或 CLI `--backup-dir` 选择工程外的目录。目录里是 `project/` 原文件副本和 `srg-project-backup.json` 校验清单。

- 复制工程目录内全部普通文件、隐藏文件、`.git`、`.meta`、资源、配置、缓存、已有构建和空目录，不按 Git 忽略规则省略。工程大，备份和核验就需要相应空间与时间。
- 源文件和副本均重新核验 SHA256；磁盘不足、文件占用、源文件变化、损坏或取消都会停止，INCOMPLETE 备份不能用于恢复。已完成备份不自动删除。
- 点击“完整备份”可先单独备份；点击“恢复完整备份…”会核验后创建**新的工程副本**，保留当前工程。首次试用可先恢复副本，再对副本适配。
- 这是工程根目录内的文件内容备份。工程外的本地依赖、玩家存档、引擎和系统环境不在范围内；链接/连接点直接拒绝，不能跳过后假称完整。文件所有者、ACL、NTFS 备用数据流和完整文件系统元数据不保证保留。操作前关闭编辑器和同步工具；不提供系统快照或硬件故障保证。

```powershell
python -m steam_release_guard backup 'D:/Games/MyGame' --backup-dir 'D:/PrivateBackups/MyGame' --dry-run --json
python -m steam_release_guard backup 'D:/Games/MyGame' --backup-dir 'D:/PrivateBackups/MyGame' --yes --json
# 将“时间编号”替换为上一条输出的实际 backup_path
python -m steam_release_guard backup-verify 'D:/PrivateBackups/MyGame/时间编号' --json
python -m steam_release_guard backup-restore 'D:/PrivateBackups/MyGame/时间编号' --output 'D:/Games/MyGame-Restored' --dry-run --json
python -m steam_release_guard backup-restore 'D:/PrivateBackups/MyGame/时间编号' --output 'D:/Games/MyGame-Restored' --yes --json
```

恢复输出目录必须不存在；失败时保留部分输出和相邻的 `.srg-restore.json`，状态为 INCOMPLETE。检查原因后选择另一个新目录重试，不覆盖原工程。备份含源码、资源和可能的密钥，保持本地私有，不上传 GitHub 或 Steam。详见 [完整备份与恢复](workflows/backup.md)。

测试范围与实物验证记录见 [完整备份验收](docs/FULL-BACKUP-VALIDATION-20261125.md)。

## 会做什么

| 项目 | 自动执行 | 仍需验收 |
| --- | --- | --- |
| Unity 6 | 安装 Editor-only 构建入口；构建时选择 IL2CPP、Windows x64、非开发模式，关闭脚本调试和性能分析，构建后恢复原设置 | IL2CPP 模块、C++ 工具链、AOT/反射、原生插件、存档、多人模式 |
| Unreal 5 | 修改 `DefaultGame.ini`：`BuildConfiguration=PPBC_Shipping`、`IncludeDebugFiles=False`；保留其他配置和数组 | 平台 INI、Launch Profile、源码 Target 规则、UAT 实际日志与最终运行行为 |
| 开发入口 | 检索候选调试菜单、作弊命令、Shipping 覆盖；检查发布包符号、Unity `boot.config` 和非 Shipping 命名 | 文本命中可能是假阳性；Blueprint、场景、Prefab、二进制插件和运行时快捷键需实测 |
| 资源暴露 | 列出散装音频、模型、贴图、源码及容器；可选启用已有密钥的 UE Pak 索引加密 | Unity 资源内容、Pak 内容与 IoStore 分开验收；扩展名不能证明加密 |
| 私有符号 | 复制分离 PDB、MDB、debug/sym 文件及 Unity 的 do-not-ship 文件夹，保存 SHA256 对照清单 | UE 未暂存到包内的符号仍在构建输出中，需要另行保留并核对同一版本 |
| Steam DRM | 提供独立的显式选择脚本，保留输入 EXE，输出新文件 | 需要 Steamworks 权限；会上传 EXE 给 Valve；需要测试分支重新安装验收 |

## 引擎适配边界

**Unity**

- 安装位置：`Assets/SteamReleaseGuard/Editor/`。安装本身不更改 `PlayerSettings`，不会令现有构建自动变成 IL2CPP。
- 在 **File → Build Profiles** 选择 Windows 的平台配置，切到 Windows x64，并启用需要发布的场景。
- 使用 **Tools → Steam Release Guard → Build Windows Release**，选择新的空输出目录。
- 首版拒绝自定义 Build Profile，避免悄悄忽略其场景、PlayerSettings 和宏覆盖。已有 Addressables、AssetBundle、自定义构建流水线需单独集成；本工具不负责生成这些内容。
- 使用 Unity 编辑器的普通 Build 按钮或其他构建脚本不会自动受到本适配器保护。适配器只校验自己的构建。
- `finally` 恢复正常退出时的后端、开发、调试、分析和子目标设置；Unity 崩溃或进程被强制终止时，需要检查这些设置或从项目版本控制恢复。
- IL2CPP 仍含可逆向的原生代码与元数据，不加密资源。不要自行删除 `global-metadata.dat`。

**Unreal**

- 通过 `EngineAssociation` 识别 UE 5.x；GUID / 自编译引擎关联只能检查，适配前需人工核实版本，不自动升级引擎。
- 可选的 `--encrypt-pak-index` 要求在 **Project Settings → Encryption** 已生成非零的 256-bit 主密钥。不会生成、轮换或打印密钥。
- 该选项写入 `UsePakFile=True` 和 `bEncryptPakIndex=True`，保留 `bUseIoStore`。Pak 索引加密不能证明 `.utoc/.ucas` 或资源主体受到保护。
- 不自动启用 `Encrypt All Asset Files`。已经启用时提示检查加载耗时、补丁大小和更新兼容性。
- `DefaultCrypto.ini` 与本地备份可能含私有密钥；本工具不会把它们上传到此仓库。请按团队密钥管理办法保存，不能因客户端有密钥就宣称无法提取。

## CLI

在仓库根目录运行（下面 `python` 指 Python 3.10+）：

```powershell
# 只预览文件清单；不创建状态目录，不写工程
python -m steam_release_guard plan 'D:/Games/MyGame'

# 先预览；确认本次范围后才使用 --yes 写入
python -m steam_release_guard apply 'D:/Games/MyGame' --dry-run --json
python -m steam_release_guard apply 'D:/Games/MyGame' --yes --json

# Unreal 可选索引加密；必须先在引擎内建立有效密钥
python -m steam_release_guard apply 'D:/Games/MyGame' --encrypt-pak-index --dry-run --json

# 检查实际 Steam depot 内容目录
python -m steam_release_guard audit 'D:/Games/MyGame' --build 'D:/Builds/MyGame-v1'

# 私有符号单独归档，保留原始构建；不会自动删除其他可疑文件
python -m steam_release_guard stage 'D:/Builds/MyGame-v1' `
  --release 'D:/Release/MyGame-v1' --symbols 'D:/PrivateSymbols/MyGame-v1' --dry-run --json

# 回滚最近一次未回滚的适配
python -m steam_release_guard rollback 'D:/Games/MyGame' --dry-run --json
```

构建脚本只生成、不执行；使用原项目准确版本的 `Unity.exe` 或 `RunUAT.bat`：

```powershell
python -m steam_release_guard build-script 'D:/Games/MyGame' `
  --tool 'D:/Engines/Unity/Editor/Unity.exe' `
  --output 'D:/Builds/MyGame-v2' --save 'D:/Builds/build-my-game-v2.ps1' --dry-run --json
```

Unreal 生成 `BuildCookRun -platform=Win64 -clientconfig=Shipping -serverconfig=Shipping -nodebuginfo` 等参数；现有 `bUseIoStore=True` 时增加 `-iostore`。不要用历史 Development 产物填入新构建目录。脚本路径拒绝 `% ! & | < > ^` 等批处理特殊字符，支持空格、中文和单引号。

写操作预览后，用户明确授权才将 `--dry-run` 换为 `--yes` 执行。不加两者时，交互终端询问；非交互/JSON 模式返回 `CONFIRMATION_REQUIRED`。`--json` 输出单个结果对象，`--progress` 向 stderr 输出阶段事件，GUI 同步提供进度和取消按钮。备份/复制阶段可取消，项目写入、回滚和最终提交阶段不可取消。

退出码：`0` = 完成或预览；`1` = 操作错误；`2` = 自动检查阻断（适配可能已保存）；`3` = 尚未确认；`130` = 取消。`audit --fail-on-warnings` 也将候选风险作为 CI 失败。

**退出码 0 不代表可上线。** 没提供发布包时是工程检查；所有报告保留 `REQUIRES_MANUAL_REVIEW` 或 `BLOCKED`，不会把缺失的实机证据算作通过。`review` 是需要人工验证，`warn` 是需要判断的候选问题，`fail` 是已检出的发布阻断项。

报告默认在工程 `.steam-release-guard/reports/latest/`；`--report-dir` 必须使用新的空目录或本工具已有的报告目录。报告列出路径和规则，不复制源码片段或密钥值。

## Steam DRM：独立操作

先阅读 [Valve Steam DRM 文档](https://partner.steamgames.com/doc/features/drm)。该服务在服务器端包裹可执行文件，**会把原始 EXE 上传给 Valve**。

```powershell
./scripts/Invoke-SteamDrm.ps1 `
  -SteamCmd 'D:/Steamworks/tools/ContentBuilder/builder/steamcmd.exe' `
  -AppId 123456 -Account 'your_build_account' `
  -InputExe 'D:/Release/MyGame/Game.exe' `
  -OutputExe 'D:/ReleaseWrapped/MyGame/Game.exe' `
  -AcknowledgeExecutableUpload
```

目录需事先存在，输出文件必须是新文件。SteamCMD 自行处理登录 / Steam Guard；不要把密码写进脚本。`-Flags` 支持官方列出的 `0 / 6 / 32 / 38`，默认 `0`；兼容性模式请按官方说明测试。

脚本不替换原 EXE、不上传 depot、不改上线分支。审核新输出、按发行流程签名、放入新暂存副本，再从测试分支重新安装，验证正版玩家的在线、离线、Steam 启动、存档和联机体验。愿望单与销售比例不能证明盗版损失。

## 恢复与测试

每次有修改的适配先完成工程外的完整文件备份，再保存本次待修改文件的原件并核对 SHA256，最后写新内容。逐文件回滚备份及事务记录仍在 `.steam-release-guard/backups/`，并记录完整备份位置。schema 2 包含状态、数量及日志校验，仍支持旧 schema 1 回滚。后续修改、日志/备份损坏会阻止恢复。写入失败保留日志，解决文件占用/空间不足后可重复 rollback。不要删除恢复目录或锁文件。

同一主机通过 OS 文件锁保守串行化写任务（包括未传工程参数的旧 stage 调用），另有工程锁。默认锁目录在系统临时目录的 `steam-release-guard-locks`；若需指定 D 盘位置，为本工具所有进程设置同一 `SRG_LOCK_DIRECTORY`。不要在操作过程中更换它。锁不阻止外部编辑器，也不支持跨主机/网络盘协调。进程退出后锁自动释放；磁盘预检不能排除复制过程中空间被其他程序耗尽。

stage 使用独立事务；发布目录 `.srg-stage.json` 只有完成后才为 COMPLETE，失败为 INCOMPLETE 并阻断 audit。私有目录保存 `srg-stage-journal.json`。安全清理只删除经核验的失败副本，保留原构建、未知文件与恢复日志：

```powershell
python -m steam_release_guard stage-cleanup 'D:/PrivateSymbols/MyGame-v1/srg-stage-journal.json' --dry-run --json
```

授权清理范围后换为 `--yes`。本版不提供续传。stage 提交副本使用同卷硬链接避免覆盖，输出文件系统需支持硬链接（例如 NTFS）；不支持时会安全失败。初始记录尚未落盘就发生写满/断电，可能需要人工处理空目录或临时记录；不保证硬件断电恢复。SHA256 用于校验意外损坏，不是防恶意篡改签名。

回滚保留本地恢复记录，以及 Unity 后来生成的目录 / `.meta` 文件。不要将 `.steam-release-guard` 复制进 Steam depot；它包含私有工程备份。工具不为用户工程自动执行 Git 提交。

```powershell
python -m unittest discover -s tests -v
python -m compileall -q steam_release_guard
# 已安装 Unity 的机器上，仅编译适配器并核对 API；不打包游戏、不下载依赖
./scripts/Test-UnityAdapter.ps1 -UnityEditor 'D:/Engines/Unity/Editor/Unity.exe'
```

GitHub Actions 覆盖 Windows / Linux、Python 3.10 / 3.12 的工具测试，不含 Unity / Unreal 许可证、引擎下载、游戏构建或 Steam 凭据。

更多：[P0 实施前审查](docs/V2-P0-REVIEW.md) · [P0 验证记录](docs/V2-P0-VALIDATION.md) · [发布人工验收表](docs/RELEASE-CHECKLIST.md) · [来源与复用评估](docs/SOURCES.md) · [v0.1 验证记录](docs/VALIDATION.md) · [安全边界](SECURITY.md)

MIT License。Unity、Unreal、Steam 为各自权利人的商标，本项目与其无隶属关系。
