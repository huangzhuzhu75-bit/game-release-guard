# P3 开发前审查

基线：8ed5ebc，P0 草稿仍未合并。2026-11-25 Windows 10 / Python 3.12.14：74 项测试，73 通过、1 个符号链接测试跳过。本次明确授权 P3 开发，不视为 P0 人工验收通过。

1. **已有能力**：Unity 6 IL2CPP/非开发构建入口；UE5 Shipping、去发布调试文件、已有 AES key 下可选 Pak index；独立 Steam DRM opt-in 脚本；发布目录启发式检查；完整备份、事务回滚、符号分离、CLI/Tk GUI。
2. **缺失能力**：混淆器、元数据加密、独立 Pak 策略、IoStore 官方工具产物验证、版本完整性清单、客户端关键数据检查、性能和运行证据绑定。
3. **技术缺口**：Unity 没有混淆事件/真实程序集证据；IL2CPP 不是元数据加密。UE 配置值不是容器加密证明；IoStore 需独立工具与证据。所有引擎的运行和保护效果需真实游戏验收。
4. **复用**：core 路径/INI/哈希/报告；operations 锁/取消/空间检查；project_backup 完整副本；transactions 冲突感知回滚；staging 已完成/失败状态与安全清理。只给事务接口增加可选内部 planner，默认仍调用旧 plan。
5. **第三方**：Obfuz 4.0.0，源码固定 `b83c53d4df525232a4d8e783d68995706b3a5d5d`；UE 自带 UnrealPak 与 IoStoreUtilities。Python 保持 3.10+ 标准库，无自动安装。
6. **授权维护**：见下表。网络安装/许可证激活由用户控制；本工具没有上传接口。外部程序不受本工具沙箱约束，必须来自可信官方来源。
7. **风险**：反射/JSON/Unity 序列化/DI/RPC/第三方 SDK/存档名称兼容；强命名程序集、原生插件；加密 IO 和补丁熵；DLC 和不同 key 版本；玩家离线/更新体验。按项关闭、基线对照，不能用测试夹具代替游戏实测。

| 候选 | 来源、授权与维护核查 | 能力与决策 |
|---|---|---|
| Obfuz | [官方源码](https://github.com/focus-creative-games/obfuz/tree/b83c53d4df525232a4d8e783d68995706b3a5d5d)，MIT，844 stars；2026-11-25 有提交 | 声称 Unity 2019+/Mono/IL2CPP，类型/方法/字段、常量、控制流；Unity 专用排除。第一版仅符号混淆；保留反射检测，字段默认不混淆。VM/密钥必须由用户先配置，本工具不生成。运行性能尚未验证。 |
| Obfuscar | [官方仓库](https://github.com/obfuscar/obfuscar)，MIT，3232 stars；最近推送 2026-09-18 | 通用 .NET 符号/字符串混淆、XML 排除；Unity6/当前 IL2CPP 的集成需要额外测试，本阶段不接入。 |
| BitMono | [官方仓库](https://github.com/bitmono-project/BitMono)，MIT，581 stars；有持续开发历史 | 有 Unity 路线；不同文档对 IL2CPP 支持存在差异，未核实版本组合，不接入。 |
| Beebyte | [官方商店入口](https://marketplace.unity.com/packages/tools/utilities/obfuscator-48919) 本次无法读取 | 当前授权、维护、Unity6 支持未验证，不依据第三方转述选用。 |
| Mfuscator 2.1.0 | [官方商店](https://marketplace.unity.com/packages/tools/utilities/mfuscator-il2cpp-encryption-256631)，Extension Asset / Standard Asset Store EULA，2026-10-05 更新 | 本机无许可证；商品页不能证明 Unity 6000.6.6f1 兼容或无需引擎初始化修改。暂不集成、不购买、不再分发。 |
| Unreal 官方工具 | 随用户已授权的对应 UE 安装提供；本仓库不再分发引擎二进制 | 使用本机 Build.version 与官方工具帮助核对命令；不推断所有版本 CLI 相同，不生成/轮换生产 key。 |

MIT 工具可用于商业用途，分发其代码或二进制时保留版权/许可证及依赖许可；不是对任意第三方 SDK 的许可保证。Obfuz 编辑器依赖 dnlib，运行程序集和用户已有 VM 需随项目处理。下载/激活可能联网；本工具执行参数不包含上传动作，但不能替第三方工具担保网络行为。

资料优先通过 Context7 查询。Obfuz 未收录准确版本，转为固定官方源码；UE Context7 为未分版本文档，因此执行前仍检查本机精确版本与帮助。参考 [CryptoKeys API](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/CryptoKeys/UCryptoKeysSettings)、[Obfuz 符号规则](https://www.obfuz.com/en/docs/manual/symbol-obfuscation)。源码审查确认 Obfuz 部分构建异常会被捕获，SRG 额外检查完成事件、程序集有效性和选中类型改名证据。

本机仅约 238 MiB 空间；发现 Unity 6000.6.6f1，可做编译级检查。用户确认无 UE/商业混淆许可证，允许继续开发、真实引擎验收标记 NOT_VERIFIED。不删除用户备份腾空间，不在真实游戏上测试。
