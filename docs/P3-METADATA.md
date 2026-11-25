# IL2CPP 与原生插件审查

本阶段没有找到同时满足精确版本兼容、无需改引擎/初始化流程、无需额外许可证且有实机证据的元数据加密方案，因此**不实现元数据加密开关**。保留 IL2CPP，增加只读产物检查。global-metadata.dat 缺失、改名、压缩、未知头都不是加密证明。

- 本机 Unity 6000.6.6f1 的 `libil2cpp/vm/GlobalMetadata.cpp` 检查 magic 0xFAB11BAF、metadata version 108。本工具读取头信息而不硬套旧版布局，不改该文件。
- GameAssembly.dll 是可逆向的原生代码。元数据仍可能含类型、方法及字符串信息；混淆改名与元数据内容加密不同。
- [Code-Protection-for-Unity](https://github.com/AndreasKarageorgos/Code-Protection-for-Unity) 的 metadata 路线需要改 MetadataLoader.cpp，违反本阶段限制；不采纳。
- [Mfuscator](https://marketplace.unity.com/packages/tools/utilities/mfuscator-il2cpp-encryption-256631) 需要用户许可及精确版本、引擎改动、运行验证，当前不接入。没有购入或下载商业二进制。
- 独立安全代码放服务端比在客户端藏秘密可靠；客户端必须能解码的资源/数据在运行中仍能被截取。

PE 检查依据 [Microsoft 官方格式](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format)，仅检查结构、CLI metadata 指示、imports、导出数量和 debug directory。不会 LoadLibrary/执行 DLL，不检查 Authenticode 信任链，不凭存在 debug directory 删除模块。导入表并不是完整依赖图（延迟加载、动态加载、OS API sets 需人工核对）。符号按 P0 stage 分离保留，运行 DLL/原生 SDK 不自动移除。

潜在 ASCII 密钥字面量只报告规则和文件偏移，不输出内容。编码/UTF16/运行时生成/混淆后的秘密不在此规则保证范围；候选需人工确认。运行测试包括 SDK 初始化、旧/新存档、反射、RPC、联机、崩溃与离线启动。
