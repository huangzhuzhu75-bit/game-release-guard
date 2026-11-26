# Unreal Engine 5 安全开发与加固

只在 UE 工程加载，行为与备份规则沿用核心 Skill。读 .uproject、目标 Target/Build.cs、平台 Config 覆盖及实际 Engine/Build/Build.version；EngineAssociation 的 GUID 不当成版本号。以下保护依据 UE5 的官方机制，字段和工具参数必须匹配小版本。

| 技术/位置 | 能做什么、不能做什么、检查方式 |
| --- | --- |
| Shipping | 面向发行的编译配置，通常裁掉多种开发调试能力；不是反逆向或自定义后门清除器。核对 Packaging、平台 INI、Target/Build.cs、Launch Profile/UAT 覆盖、真实日志及运行入口。 |
| Pak | `.pak` 打包容器本身不保密。`Encrypt Pak Index` 保护索引，不等于音频/模型/纹理主体已加密。需要已有合法密钥及真正构建证据，不能从一个 INI 布尔值直接声称防提取。 |
| IoStore | `.utoc`/`.ucas` 是另一套容器布局；`bUseIoStore=True` 仅表示配置意图。按引擎版本、构建参数和容器标志核对实际加密/签名及加载。Pak 索引开关不能证明 IoStore 内容受保护；Release Guard P3 候选提供独立官方工具检查入口，实际加密/签名与运行仍需验证。 |
| UAsset / Cook | Cook 转换成目标平台可用数据，并可能去掉编辑器数据，不能推断所有内容不可分析。`Encrypt UAsset Files` 在 Pak 场景主要保护相关包头/字符串信息，不能推断全部 bulk data 加密；结合 `.uexp`/`.ubulk` 或 IoStore 的实际布局判断。 |
| INI 加密 | `Encrypt Pak Ini Files` 针对被放入 Pak 的 INI，不能保护源码目录、散装配置、日志或客户端内存中的秘密。配置合并/平台覆盖可能改变结果，须检查最终产物。 |
| Pak 签名 | 用于检测篡改和验证受信来源，提供完整性而非保密。签名私钥留构建/签名环境，客户端可有公钥；核对目标版本运行时确实验证/拒绝错误签名。不是防资源读取或服务端反作弊。 |
| Crypto Keys / 全资源加密 | 管理构建使用的加密/签名材料。需要运行时解密的客户端仍有可利用的解密路径；不要随意生成/轮换、泄漏 `DefaultCrypto.ini` 或签名私钥。`Encrypt All Asset Files` 的覆盖范围按实际容器核对，增加 I/O 与补丁代价，应实测加载时间、包/补丁体积和旧版本升级。 |
| 调试符号 | Shipping 仍可能生成符号；“不随包分发”与“停止生成”不同。关闭适用版本的 Include Debug Files in Shipping Builds，另存匹配构建的 PDB/符号，不丢弃唯一崩溃诊断资料。 |

授权配置时，在 **Edit → Project Settings → Packaging** 核对 Shipping 和调试文件选项；按所用版本在 Encryption/Crypto Keys 检查已有策略。审查 `Config/`、`Source/`、插件、Target 规则、Blueprint/输入绑定的可达开发入口；`WITH_EDITOR` / `UE_BUILD_SHIPPING` 等正确条件隔离是已有保护。没有打开/解析 Blueprint 时，不声称其已审计。

INI 的节名与属性名也要核对，不把包含 Debug/Encrypt 的布尔文本直接当成有效配置。官方 `UProjectPackagingSettings` 的调试文件属性名为 `IncludeDebugFiles`，不能自行加成 `bIncludeDebugFiles`；无法核实目标版本属性、覆盖和最终构建时保留不确定性。按真实字段识别已有保护，不能让拼错的字段获得“已生效”结论。

按原引擎版本打包到新目录，复查 UAT 日志、配置覆盖、容器和私有文件；实测最终程序的控制台/作弊入口、客户端/服务端边界、存档、插件、更新以及实际加密/签名行为。原生 C++、Blueprint cooked 数据、扩展名或 Shipping 文件名都不能单独证明无法分析。

授权加固时，备份后实际修正已确认的 Shipping/符号分发配置或源码开发入口，不重复覆盖已有保护。保留原 Pak/IoStore 容器策略与密钥，各保护选项独立选择；缺合法密钥或版本依据时不写入会破坏加载的加密设置，继续其他有依据的静态改动。没有真实容器/引擎时不宣布加密、签名或运行成功。

本地高级适配按明确策略处理 Pak/IoStore；UE 5.6 的 IoStoreUtilities 使用 `UnrealPak.exe IoStore` 模块入口，和 Pak 的调用/证据分开。`iostore-only` 在现有工具 profile 中被拒绝，缺版本/帮助参数证据返回 NOT_VERIFIED。不要因知识文档讨论 IoStore 就绕过这些实际工具限制。

## 官方参考

- [UE 5.6 Packaging](https://dev.epicgames.com/documentation/en-us/unreal-engine/packaging-your-project?application_version=5.6)
- [UE 项目加密与打包设置](https://dev.epicgames.com/documentation/en-us/unreal-engine/project-section-of-the-unreal-engine-project-settings)
- [UProjectPackagingSettings 属性（滚动 API）](https://dev.epicgames.com/documentation/unreal-engine/API/Developer/DeveloperToolSettings/UProjectPackagingSettings)
- [Crypto Keys API](https://dev.epicgames.com/documentation/en-us/unreal-engine/API/Plugins/CryptoKeys/UCryptoKeysSettings)
- [Project Launcher](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-the-project-launcher-in-unreal-engine)

核对日期：2026-11-27。非版本化 Epic 页面可能默认展示较新 UE，先切到实际工程版本；滚动 API 文档不证明所有 UE5 小版本支持相同字段或工具参数。
