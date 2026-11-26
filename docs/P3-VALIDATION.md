# P3 验证记录

基线 8ed5ebc，独立分支 `p3/advanced-protection`。P0 不合并，不改用户真实游戏。

## 阶段 1：混淆适配

- Windows 10 / Python 3.12.14：83 项，82 通过、1 个旧符号链接测试跳过。新增 9 项覆盖 opt-in、排除规则、错误配置、缺工具、完整备份/回滚、写入确认、真实子进程日志脱敏；这些是合成夹具，不能证明游戏保护效果。
- 用本机 Unity 6000.6.6f1 的 Roslyn/真实引用程序集编译 Obfuz.Runtime、Obfuz.Editor、P0 builder 和新增 bridge，成功。外部源码固定 b83c53d4，MIT，仅下载到隔离 D 盘作编译检查；没有安装进用户游戏。
- 供应商源码产生过时 UnsafeUtility API 和未使用字段警告；本次未修改第三方源码。编译脚本保留用于复现。
- 实际 Obfuz 构建、IL2CPP 游戏启动、存档/联机/性能：**NOT_VERIFIED**。字符串/控制流额外初始化尚未实现，拒绝启用。未加密 metadata。

## 阶段 2：元数据与原生模块

- 新增 4 项测试通过：PE32/PE32+、CLR 区别、截断/越界拒绝、未知 metadata 不误报加密、敏感候选脱敏且不改文件。
- 用实际 Unity.exe 和阶段 1 编译的 bridge DLL 做只读 PE 检查，正确区分原生与托管，并列出导入依赖。
- 核对本机引擎 metadata 头版本；未修改引擎、插件或 metadata。没有可批准的 metadata 加密方案，功能明确 NOT_VERIFIED，不冒充已实现。

## 阶段 3：UE CryptoKeys / Pak / IoStore

- 新增 7 项合成测试通过：独立开关、密钥原值保留、逐字节回滚、非法/零密钥拒绝、关闭保护、版本不符、缺失分区、depot 中私钥引用拒绝、分级冲突、只读预览与脱敏。
- 官方工具调用测试使用明确标注的 mock，检查 Pak 与 IoStore 走不同命令，即使退出零也不会给出保护 PASS。没有实际安装 UE，实际命令兼容、RSA key 对/签名有效性、加密产物、资源加载和 DLC/补丁 **NOT_VERIFIED**。
- 分级是分类/建议，不自动建立 Chunk 或 per-asset 加密。生产配置不生成/轮换 key。

## 阶段 4：文件完整性与 DRM 产物

- 新增 6 项测试通过：字节修改/删除/添加、清单被替换、错误 build-id、路径穿越/重复条目、显式可变存档、合法更新新基线、旧文件拒绝覆盖、DRM 原件哈希与 PE 验证。
- 新清单必须使用外部可信 SHA256 pin；不会把自签 checksum 当认证。没有引入自制密码算法或外部加密依赖。
- 所有测试为明确的结构夹具；Steam Wrapper 没有调用/上传，游戏启动器集成、离线/测试分支与游戏运行时完整性 **NOT_VERIFIED**。

## 阶段 5：客户端架构风险

- 新增 4 项测试通过：Unity/UE 具体位置、敏感值不进入输出、只读且不生成报告、已有 authority/debug 宏线索、UTF16、大文件/编码覆盖限制、不将无命中当 PASS。
- 使用合成 C#/C++/INI；扫描规则提供风险定位与服务端设计建议，不声称语义证明。没有重写游戏或服务器、没有网络测试和 key 轮换。

## 阶段 6：性能记录与三层验收

- 新增 5 项验收测试通过：无数据/无阈值不通过，REVIEW/NOT_VERIFIED 不升级，PASS 声明必须关联哈希匹配的文件且只记 RECORDED_PASS，指标退化/零基线、证据和构建被修改、路径穿越/布尔伪造数字均被识别。
- 最后审查补充 2 项防误判测试：快速结束的工具输出超过 16 MiB 仍失败且限制读取量；合成构建回执必须绑定精确程序集、引擎/工具版本和生成 EXE。manifest 在同一次有界读取中校验可信 pin 并解析，避免校验后重新读取另一份内容。
- Windows 10 22H2 / Python 3.12.14 最终全量 **111 项：110 通过、1 个 Windows 符号链接测试跳过**。原 74 项测试完整保留，含真实 Tk 控件回调、报告生成、完整备份恢复、事务冲突、进程中止、失败暂存和安全清理。GUI 仍是原有基础功能；高级操作目前走 CLI。
- 在隔离的合成 UE 工程上实际执行 10 条 CLI：完整备份、核验、恢复新副本，advanced unreal-plan → apply 预览/执行 → 完整备份复核 → audit → rollback 预览/执行。原目录未变，恢复副本的工程文件在回滚后逐字节匹配，HTML 报告保持 REQUIRES_MANUAL_REVIEW。它不是 UE 打包/游戏运行验收。
- 全部 PowerShell 脚本语法检查和 git diff --check 通过。文档命令由实际 CLI parser 校验，项目级 AI 入口仍指向同一 Skill；新增 P3 段落没有重新进行各 AI 平台行为验收，Claude Code/Gemini CLI 仍未安装、NOT_VERIFIED。

## PR #2 定向复审修复（2026-11-26）

基于复审时 PR HEAD `fbef061e130359569fdb41155e1c5c63cc93ba08` 追加，不改 P0、Unity/Obfuz、GUI 或事务架构，PR 保持 Draft。

- Unreal 容器检查分为 PakFileUtilities / IoStoreUtilities 两个入口，各自保存帮助、命令结果和 `verification.json`。版本从所选安装的 Build.version 校验；未知版本、缺工具/参数或不匹配均不执行相应容器检查。工具执行失败记 FAIL，退出零最多 REVIEW；没有非空 IoStore 清单仍为 NOT_VERIFIED，加密/签名和运行始终单独验收。
- 官方 UE 5.6 文档提供的 IoStoreUtilities 是由 `UnrealPak.exe IoStore` 承载的模块入口，并没有确认独立 `IoStoreUtilities.exe`。测试中的“仅 Pak / 仅 IoStoreUtilities”表示宿主分别只提供一种检查能力，不冒充存在两个官方独立 EXE；普通 Pak 命令不能检查 `.utoc`。IoStore 命令 profile 暂只开放已核对文档的 5.6，且仍需现场帮助确认。
- UE 策略升级 schema 2，容器选择明确写为 `pak-only` 或 `pak+iostore`；旧 schema 1 不自动迁移。`iostore-only` 在当前 Windows/UAT profile 没有验证过的独立组合，写入和备份前停止，不擅自开启 Pak。两个支持的策略均验证完整备份、密钥保留和逐字节回滚。
- 新增 14 项回归测试；原 111 项全部保留。原 UE 测试仅更新显式策略夹具、版本错误的 NOT_VERIFIED 预期和正确的模块调用断言，没有删除或降低覆盖。覆盖仅一种入口、两种入口、缺宿主/未确认的独立 EXE、版本不匹配/未知版本、参数缺失、帮助/执行失败、退出零无清单、两类结果隔离、单类容器不调用另一类和只读 CLI 预览。
- 本机 Windows 10 / Python 3.12.14 全量 **125 项：124 通过，1 个旧 Windows 符号链接权限测试跳过**。合成工具和容器只验证调用/安全边界，不证明 UE 实际兼容或保护效果。README/P3 工作流示例由实际 CLI parser 检查，未新增 CLI 命令。
- 保留 `.github/workflows/test.yml` 的 Windows/Linux × Python 3.10/3.12 四组合，以及模块编译、Windows PowerShell 语法检查。最终提交的矩阵结果以 [PR #2 Checks](https://github.com/huangzhuzhu75-bit/game-release-guard/pull/2/checks) 绑定的 HEAD 与日志为准；不能用本机结果代替其余环境。
- 对固定 Obfuz 源码的事件、配置类型、生成路径和程序集引用做定向复查，未发现新的确定 API/配置错误；没有扩展字符串/控制流保护或 metadata 加密。真实游戏构建与运行仍 **NOT_VERIFIED**。

## 未完成的真实验收

用户此前明确允许在无 UE/商业保护器许可、当时 D 盘空间不足的条件下继续开发并保留 **NOT_VERIFIED**。此次复审仍未安装 UE 或进行真实引擎验收；Unity API 编译不是 Unity 导入/构建，更不是保护效果或运行验证。

尚未验证：真实 Obfuz 构建/程序集运行、IL2CPP 游戏启动、反射/序列化/旧存档/RPC/插件；UE 实际 Pak 与 IoStore 加密和签名、DLC/补丁；游戏内完整性集成；Steam Wrapper、启动/离线/测试分支；所有真实启动/加载/内存/CPU/包体/补丁/崩溃/网络/存档性能测量。现有记录器不自动生成这些测量，也不认可空的 PASS 声明。

尚未实施：字符串/控制流保护（暂拒绝 true）、metadata 加密、自动资源分块/按等级加密、运行时反篡改注入。没有可靠验证方案时保留限制，不以改名、压缩、配置或检查入口冒充已经生效的深度保护。P3 为开发候选，P0 和 P3 都没有自动合并或发行。
