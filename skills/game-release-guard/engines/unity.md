# Unity 6 安全开发与加固

只在 Unity 工程加载，行为与备份规则沿用核心 Skill。优先读取完整 ProjectVersion、Packages 锁文件、asmdef、构建脚本与 Build Profiles；下面菜单以 Unity 6 为基线，不迁移或升级用户工程。

| 技术/位置 | 能做什么、不能做什么、检查方式 |
| --- | --- |
| IL2CPP | 将托管程序集经 C++ 转为 AOT 原生代码，提高直接阅读 C# IL 的门槛；不是加密，也不使原生代码、字符串或资源不可逆向。按精确版本、目标平台及插件兼容性选择，核对实际构建日志和产物，不能仅看编辑器设置。 |
| C# 混淆 | 可变换名称/控制流，增加阅读成本。第三方混淆器需支持所用 Unity、IL2CPP/AOT、反射、序列化、网络协议和热更新方案；保留映射文件及必要排除规则。不得批量重命名 Unity 消息方法、反射入口、序列化字段或资源标识；先在副本测试存档和补丁兼容。 |
| 字符串保护 | 能降低静态搜索的便利性，运行时仍需恢复字符串；不适合藏服务端秘密。会影响性能、日志诊断和第三方 SDK，按价值选用，不自制密钥隐藏方案冒充安全边界。 |
| `global-metadata.dat` | 标准 IL2CPP 产物中的运行时元数据有助于分析类型/方法等信息，但不是全部源码；正常存在不等于“打包失败”。不能删除/改名来保护，也不能看到它就断言所有自定义保护无效。自定义 metadata 保护依赖精确运行时，未经实物验证标 NOT_VERIFIED。 |
| AssetBundles | 资源容器及压缩/分发机制，默认不是保密方案。CRC、内容哈希用于对应的完整性/版本检查，不应当作攻击者无法伪造的来源认证。检查本地/远程包、清单、缓存、加载器以及是否有实际加密/签名验证链。 |
| Addressables | 通过 catalog、地址、依赖和 provider 管理加载，通常使用 AssetBundles。远程地址、散列文件名或 catalog hash 不等于加密或授权；检查 `packages-lock.json` 的包版本、组设置、catalog、远程权限和缓存。自定义 provider 的存在也不是保护已生效的证据。 |
| 原生插件 | C/C++ DLL 可提高部分托管分析门槛，仍可反汇编/调试和搜索字符串；注意导出接口、ABI、AOT 调用、平台架构及第三方符号，不能把秘密移进 DLL 就视为安全。 |
| 调试符号与剥离 | PDB/MDB、符号映射及 do-not-ship 目录放私有归档，按构建标识对应崩溃。不要删除唯一符号；Managed Stripping 是裁剪未使用代码，非混淆，需核对反射/AOT 保留配置和运行测试。 |

操作时先读 `ProjectVersion.txt`、程序集定义、构建脚本和 Build Profile 覆盖。授权调整时，在适用版本的 **Edit → Project Settings → Player → Other Settings → Configuration** 选择 IL2CPP；Unity 6 的 **File → Build Profiles → Windows** 关闭 Development Build，并核对 Script Debugging、Profiler 连接和自定义构建选项。

源码审查 `Assets/` 中实际运行的脚本、场景/Prefab 引用、StreamingAssets、Resources、Addressables 配置、插件和 Editor 边界。`UNITY_EDITOR` / Editor-only asmdef 是已有隔离证据；`DEVELOPMENT_BUILD` 条件还要与真正构建选项匹配。自定义菜单/运行时快捷键不会因关闭 Development Build 自动消失。源码候选不证明代码在最终包内可达。

在授权的独立输出目录构建后检查目标平台、IL2CPP/Mono 证据、开发标志、符号、源码/私有配置和散装资产；运行最终 EXE 验证启动、插件、反射/序列化、旧存档、联机、离线、更新和开发入口。没有打包运行时，这些项保留 NOT_VERIFIED。用户已授权加固时，实施兼容且可恢复的代码或配置改动；缺少构建条件不妨碍完成已核实的静态加固，但不能宣称保护已运行生效。

已有本地工具提供 Unity 6 Windows 构建入口与 Obfuz 4.0.0 名单式适配，默认保留字段；不支持默认全类型混淆，没有 metadata 加密，字符串/控制流保护暂拒绝启用。需要使用时核对实际仓库与工作流，不能把 Skill 介绍的第三方技术当成本地工具已实现。授权加固可以直接修正已确认的调试隔离/构建设置，保留场景 GUID、序列化字段和反射入口；不要以缺少混淆器为由停止所有安全改动。

## 官方参考

- [Unity 6.0 IL2CPP](https://docs.unity3d.com/6000.0/Documentation/Manual/scripting-backends-il2cpp.html)
- [Unity 6.0 BuildOptions](https://docs.unity3d.com/6000.0/Documentation/ScriptReference/BuildOptions.html)
- [Unity 6.0 AssetBundle 完整性](https://docs.unity3d.com/6000.0/Documentation/Manual/AssetBundles-Integrity.html)
- [Addressables 1.21 分组与加载](https://docs.unity3d.com/Packages/com.unity.addressables@1.21/manual/ContentPackingAndLoadingSchema.html)

核对日期：2026-11-27。Addressables 1.21 是版本化参考，不是要求项目固定用该版本；先读项目锁文件再查相应包手册。
