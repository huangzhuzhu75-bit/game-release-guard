# Steam Release Guard

**给 Unity 6 / Unreal Engine 5 的 Windows、Steam 发布流程做可回滚的一键适配。**

本地桌面界面 + 无第三方 Python 依赖的 CLI。分别检查代码可读性、开发调试入口和资源暴露，生成 HTML / JSON 报告。不会联网扫描工程、收集遥测或上传游戏。

这是一套发布加固与检查工具，不是反盗版保证、资源加密壳或反作弊系统。`v0.1.0` 是待真实项目验收的首版；完整引擎打包和 Steam 测试分支结果见 [验证记录](docs/VALIDATION.md)。

## 双击使用

1. 下载并解压仓库；本机需有 **Python 3.10+，含 tkinter**。无需 `pip install`，无需管理员权限。引擎构建另需原工程对应的引擎、许可证和 Windows 构建组件。
2. 双击 **`Launch.cmd`**。如果自动寻找 Python 失败，把已有 `python.exe` 的完整路径写入 `.local/python-path.txt`，或设置进程环境变量 `SRG_PYTHON`。工具不会自行下载 Python。
3. 选择工程根目录，点击 **一键适配**。先点击“检查”或运行 `plan` 可预览范围。建议先关闭 Unity / Unreal 编辑器。
4. 通过“生成引擎构建脚本…”生成并运行对应版本的构建命令；Unity 也可直接使用新增的菜单入口。选择实际发布包，再执行检查。
5. 如需分离符号，选择三个互不嵌套的目录：原构建、空发布目录、空私有符号目录。复制并校验后，对新发布目录重新检查。

“一键”指配置适配、安装 Unity 构建入口和生成检查报告；它不会替你安装引擎、判断插件兼容性、打包上传 Steam 或批准游戏上线。

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

# 一键适配并生成报告
python -m steam_release_guard apply 'D:/Games/MyGame'

# Unreal 可选索引加密；必须先在引擎内建立有效密钥
python -m steam_release_guard apply 'D:/Games/MyGame' --encrypt-pak-index

# 检查实际 Steam depot 内容目录
python -m steam_release_guard audit 'D:/Games/MyGame' --build 'D:/Builds/MyGame-v1'

# 私有符号单独归档，保留原始构建；不会自动删除其他可疑文件
python -m steam_release_guard stage 'D:/Builds/MyGame-v1' `
  --release 'D:/Release/MyGame-v1' --symbols 'D:/PrivateSymbols/MyGame-v1'

# 回滚最近一次未回滚的适配
python -m steam_release_guard rollback 'D:/Games/MyGame'
```

构建脚本只生成、不执行；使用原项目准确版本的 `Unity.exe` 或 `RunUAT.bat`：

```powershell
python -m steam_release_guard build-script 'D:/Games/MyGame' `
  --tool 'D:/Engines/Unity/Editor/Unity.exe' `
  --output 'D:/Builds/MyGame-v2' --save 'D:/Builds/build-my-game-v2.ps1'
```

Unreal 生成 `BuildCookRun -platform=Win64 -clientconfig=Shipping -serverconfig=Shipping -nodebuginfo` 等参数；现有 `bUseIoStore=True` 时增加 `-iostore`。不要用历史 Development 产物填入新构建目录。脚本路径拒绝 `% ! & | < > ^` 等批处理特殊字符，支持空格、中文和单引号。

退出码：`0` = 操作完成且未检出自动阻断项；`1` = 输入、文件、版本或操作错误；`2` = 检查检出阻断项（适配本身可能已经保存）。`audit --fail-on-warnings` 也会将候选风险作为 CI 失败。

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

每次适配先保存原文件并核对 SHA256，再写新内容；备份及事务记录在 `.steam-release-guard/backups/`。原文件不存在时，回滚只删除工具创建的对应文件。遇到后续人工修改或备份损坏，整批恢复在改写前停止。断途中断后可运行 `rollback` 处理 prepared 事务；不要删除恢复目录。

回滚保留本地恢复记录，以及 Unity 后来生成的目录 / `.meta` 文件。不要将 `.steam-release-guard` 复制进 Steam depot；它包含私有工程备份。工具不为用户工程自动执行 Git 提交。

```powershell
python -m unittest discover -s tests -v
python -m compileall -q steam_release_guard
# 已安装 Unity 的机器上，仅编译适配器并核对 API；不打包游戏、不下载依赖
./scripts/Test-UnityAdapter.ps1 -UnityEditor 'D:/Engines/Unity/Editor/Unity.exe'
```

GitHub Actions 覆盖 Windows / Linux、Python 3.10 / 3.12 的工具测试，不含 Unity / Unreal 许可证、引擎下载、游戏构建或 Steam 凭据。

更多：[发布人工验收表](docs/RELEASE-CHECKLIST.md) · [来源与复用评估](docs/SOURCES.md) · [验证记录](docs/VALIDATION.md) · [安全边界](SECURITY.md)

MIT License。Unity、Unreal、Steam 为各自权利人的商标，本项目与其无隶属关系。
