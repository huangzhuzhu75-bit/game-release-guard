# P3 高级保护（候选，真实游戏验收未完成）

先读 [开发前审查](../docs/P3-REVIEW.md)。P0 旧命令和 GUI 保留；高级功能使用 `advanced` 命令空间。默认所有引擎运行、保护效果及性能均未验证，不因配置正确而批准发行。只有你拥有的游戏副本和官方可信工具可用于试验。

## Unity 符号混淆

1. 按 [完整备份](backup.md) 先 backup、backup-verify，再 backup-restore 到新的工程副本。关闭编辑器和同步工具。
2. 用户自行安装 Obfuz，官方地址 `https://github.com/focus-creative-games/obfuz.git#b83c53d4df525232a4d8e783d68995706b3a5d5d`。SRG 不下载、不修改 Packages manifest；本机安装检测只读。按该版本官方说明配置 Obfuz.asset 和生成 VM，保留原有配置/密钥。即使仅符号混淆，该工具也要求已有 VM；SRG 不代为生成或轮换密钥。
3. 复制并编辑 [示例配置](../examples/advanced/unity-obfuz.json)：填写精确 Unity 版本、自己拥有的 asmdef 程序集及少量普通 C# 类型。不要直接照抄示例类型。反射、JSON/存档 DTO、序列化、DI 注册、RPC、第三方 SDK 先加入 exclude_types；reference_assemblies 必须覆盖引用被混淆程序集的程序集。
4. 默认保留所有名称，只对 include_types 中明确类型启用类型/方法改名；字段默认保留。exclude_types 后匹配优先。Unity 自带特殊类型规则仍可能阻止改名，不能用空改动宣称成功。strings/control_flow 暂不开放；传 true 明确报错，不静默忽略。需额外运行时初始化的保护仍为 NOT_VERIFIED。

```powershell
python -m steam_release_guard advanced obfuscator-detect "D:/GameCopy" --json
python -m steam_release_guard advanced obfuscator-detect "D:/GameCopy" --tool-path "D:/Tools/obfuz" --json
python -m steam_release_guard advanced unity-plan "D:/GameCopy" --config "D:/Profiles/unity.json" --json
python -m steam_release_guard advanced unity-apply "D:/GameCopy" --config "D:/Profiles/unity.json" --backup-dir "D:/Backups/GameCopy" --dry-run --json
python -m steam_release_guard advanced unity-apply "D:/GameCopy" --config "D:/Profiles/unity.json" --backup-dir "D:/Backups/GameCopy" --yes --json
python -m steam_release_guard advanced unity-build "D:/GameCopy" --config "D:/Profiles/unity.json" --editor "D:/Unity/Editor/Unity.exe" --output "D:/Builds/Protected-001" --evidence-dir "D:/Private/Protected-001" --dry-run --json
python -m steam_release_guard advanced unity-build "D:/GameCopy" --config "D:/Profiles/unity.json" --editor "D:/Unity/Editor/Unity.exe" --output "D:/Builds/Protected-001" --evidence-dir "D:/Private/Protected-001" --yes --json
python -m steam_release_guard rollback "D:/GameCopy" --dry-run --json
python -m steam_release_guard rollback "D:/GameCopy" --yes --json
```

`--tool-path` 用于候选包检测；实际构建使用 Unity 已解析的 UPM 包，桥接再次检查包版本与 Editor 版本。使用标准 Windows x64 Profile，启用发布场景；没有 Windows IL2CPP 模块/编译环境时停止。执行引擎只接受本工具验证恢复得到的副本；会产生正常的 Unity 导入缓存。输出与证据目录必须全新且与工程互不嵌套。

日志、符号映射、原程序集备份为私有资料。不要上传 Steam 或 GitHub。桥接检查 Obfuz 的 success 事件和实际程序集元数据，要求选中类型有改名证据；配置和原 Obfuz.asset 在 finally 中恢复。断电/进程被杀时可能无法执行 finally，保留副本，使用完整备份重新恢复；不要对唯一工程执行。

构建完成仍需插件、旧/新存档、反射/JSON、RPC/联机、离线、更新和真实保护效果验收。`execution.json` 的 REVIEW 不是发行 PASS。关闭混淆使用普通 P0 构建入口或回滚桥接；关闭后名称分析更容易。

## Unity 元数据与原生插件（只读）

```powershell
python -m steam_release_guard advanced unity-inspect "D:/GameCopy" --build "D:/Builds/Protected-001" --json
```

仅输出检查结果，不写报告文件、不执行/删除 DLL。[技术限制](../docs/P3-METADATA.md) 包含版本核查、插件依赖和元数据方案排除理由。

## Unreal 独立配置与容器检查

编辑 [UE 策略](../examples/advanced/unreal-policy.json)，每项都是显式开关。当前审查范围 UE 5.0–5.6；未知/自编译 GUID 和更新版本需重新核查。现有 AES key 必须是有效非零 32 字节 Base64；签名字段只检查编码/非空，**不是 RSA key 对正确性验证**。生产 key 必须由你在 UE 管理；SRG 不生成/轮换，不在结果中输出其值。

```powershell
python -m steam_release_guard advanced unreal-plan "D:/UECopy" --config "D:/Profiles/unreal.json" --json
python -m steam_release_guard advanced asset-plan "D:/UECopy" --config "D:/Profiles/unreal.json" --json
python -m steam_release_guard advanced unreal-apply "D:/UECopy" --config "D:/Profiles/unreal.json" --backup-dir "D:/Backups/UECopy" --dry-run --json
python -m steam_release_guard advanced unreal-apply "D:/UECopy" --config "D:/Profiles/unreal.json" --backup-dir "D:/Backups/UECopy" --yes --json
python -m steam_release_guard advanced unreal-verify "D:/UECopy" --engine-root "D:/UE_5.6" --build "D:/Builds/UE-001" --evidence-dir "D:/Private/UE-001" --crypto-json "D:/Private/Crypto.json" --dry-run --json
python -m steam_release_guard advanced unreal-verify "D:/UECopy" --engine-root "D:/UE_5.6" --build "D:/Builds/UE-001" --evidence-dir "D:/Private/UE-001" --crypto-json "D:/Private/Crypto.json" --yes --json
```

实际构建使用原有 `build-script` 流程。`unreal-verify` 读取 Engine/Build/Build.version，匹配项目版本后检查 UnrealPak 自身帮助：Pak 调用 -Test/-List，IoStore 独立调用 -Info/-List（帮助没有对应参数则不猜测）。只保存私有日志和文件哈希，不提取资源。返回零仅记 REVIEW；必须审阅日志里的具体加密范围、签名/完整性证据，并在同版引擎启动验证。缺少官方工具不会安装第三方解包器。

参考 [UE5.6 Zen Loader 官方说明](https://dev.epicgames.com/documentation/en-us/unreal-engine/zen-loader-in-unreal-engine?application_version=5.6)。`.utoc` 描述容器结构，`.ucas` 承载数据；Pak index 加密不能证明 IoStore 加密。部分项目还有分区 `.ucas`、DLC 和平台配置覆盖，全部需纳入版本清单和实际加载验证。签名有效性当前保留 NOT_VERIFIED，不能依据 `.sig` 存在或退出码推断有效。

`asset-plan` 对 Content 文件按显式路径规则分 A/B/C，缺规则和重复命中都标 REVIEW。分级不会自动创建 Chunk/PrimaryAssetLabel/AssetManager 或分配 secondary key。先在 Editor 审核依赖和加载关系后实现分块；全资源加密是全局开关，不能称为分级加密。分别评估 A 核心资源、B 普通资源、C 公开资源的收益，记录启动、加载、内存、补丁和 DLC 基线。

回滚仍使用普通 `rollback`。关闭某一开关只写该项 false，含义是放弃相应加密/签名保护；不会删除 key。所有修改保持原 INI 编码、无关配置、注释与数组；后续编辑冲突会阻止回滚。
