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

编辑 [UE 策略](../examples/advanced/unreal-policy.json)。schema 2 把容器策略和 CryptoKeys 开关分开，`container_policy` 必须明确选择；schema 1 的 `iostore` 布尔值不能表达是否允许启用 Pak，旧配置会停止并要求人工迁移，不会猜测或自动修改。

| 策略 | UsePakFile / bUseIoStore | 当前处理 |
|---|---|---|
| `pak-only` | True / False | 按明确选择预览、备份后写入 |
| `pak+iostore` | True / True | 按明确选择预览、备份后写入；Pak 和 IoStore 分别验收 |
| `iostore-only` | False / True | 当前 Windows/UAT profile 没有已验证的独立组合，NOT_VERIFIED，写入前停止；不自动改成 True / True |

策略允许你明确改变原容器方式，但 CryptoKeys 开关本身不会选择容器。先对照原工程 Packaging、平台覆盖与发布流程选择策略，再用 dry-run 审核；没有授权的策略变化就不执行 apply。官方 Zen Loader 流程还使用伴随 Pak 承载 loose files，并在挂载 Pak 时挂载对应容器；不能只凭两个 INI 布尔值承诺纯 IoStore 支持。

配置审查范围仍是 UE 5.0–5.6；未知/自编译 GUID 和更新版本需重新核查。现有 AES key 必须是有效非零 32 字节 Base64；签名字段只检查编码/非空，**不是 RSA key 对正确性验证**。生产 key 必须由你在 UE 管理；SRG 不生成/轮换，不在结果中输出其值。

```powershell
python -m steam_release_guard advanced unreal-plan "D:/UECopy" --config "D:/Profiles/unreal.json" --json
python -m steam_release_guard advanced asset-plan "D:/UECopy" --config "D:/Profiles/unreal.json" --json
python -m steam_release_guard advanced unreal-apply "D:/UECopy" --config "D:/Profiles/unreal.json" --backup-dir "D:/Backups/UECopy" --dry-run --json
python -m steam_release_guard advanced unreal-apply "D:/UECopy" --config "D:/Profiles/unreal.json" --backup-dir "D:/Backups/UECopy" --yes --json
python -m steam_release_guard advanced unreal-verify "D:/UECopy" --engine-root "D:/UE_5.6" --build "D:/Builds/UE-001" --evidence-dir "D:/Private/UE-001" --crypto-json "D:/Private/Crypto.json" --dry-run --json
python -m steam_release_guard advanced unreal-verify "D:/UECopy" --engine-root "D:/UE_5.6" --build "D:/Builds/UE-001" --evidence-dir "D:/Private/UE-001" --crypto-json "D:/Private/Crypto.json" --yes --json
```

实际构建继续使用原有 `build-script` 流程。`unreal-verify` 分别建立 PakFileUtilities 和 IoStoreUtilities 检查入口，先从同一安装的 `Engine/Build/Build.version` 核对版本，再检查该入口自己的帮助；版本不符、缺工具或未知参数不会调用容器命令，记录 NOT_VERIFIED。

- Pak 使用 `Engine/Binaries/Win64/UnrealPak.exe -Help`，仅对 `.pak` 调用帮助中明确支持的 `-Test` / `-List`。
- IoStoreUtilities 是 UE Developer 模块。已查到的官方入口由 `UnrealPak.exe IoStore` 承载，不是已确认存在的独立 `IoStoreUtilities.exe`。当前只开放已核对文档的 UE 5.6 入口；独立调用 `IoStore -Help`，要求它明确给出 IoStore 身份、`-List=<container>` 和 `-Csv=<path>`，才对 `.utoc` 运行 `IoStore -List=<utoc> -Csv=<私有输出>`。不复用 Pak 帮助，不把 `.utoc` 交给普通 Pak 检查。不认识的独立 EXE/DLL 不当作可执行替代品。
- 使用 `--crypto-json` 时，各入口还必须明确支持 `-CryptoKeys=`。缺少参数只记录未验证，不尝试其他拼法/命令。只检查与构建内现有容器类型对应的入口；另一类记录 NOT_REQUESTED。
- 分别保存 `pak/verification.json`、`iostore/verification.json`、各自帮助/执行日志；总记录为 `verification.json`。每类记录包含模块、版本/程序哈希、单容器结果。一个入口失败不覆盖另一类记录；执行失败标 FAIL，缺参数标 NOT_VERIFIED。IoStore 返回零但没有生成非空清单仍为 NOT_VERIFIED。
- 返回零且有检查证据最多记 REVIEW，两个容器的加密/签名和真实运行仍分别 NOT_VERIFIED。没有提取资源或自动安装工具。Build.version 绑定所选安装，程序哈希记录所用二进制；它们不能替代官方来源核验或真实引擎测试。

参考 [UE5.6 Zen Loader 官方说明](https://dev.epicgames.com/documentation/en-us/unreal-engine/zen-loader-in-unreal-engine?application_version=5.6) 和 [UE5.6 命令行参数参考](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-engine-command-line-arguments-reference?application_version=5.6)（`csv` 给出 `-list=<ContainerFile> -csv=<path>`）。Context7 仅提供未分版本索引，本次转查上述精确版本文档；本机没有 UE，帮助输出和实际执行尚未实测，能力门槛不满足就停止，不伪造兼容性。

`.utoc` 描述容器结构，`.ucas` 承载数据；Pak index 加密不能证明 IoStore 加密。部分项目还有分区 `.ucas`、DLC 和平台配置覆盖，全部需纳入版本清单和实际加载验证。签名有效性当前保留 NOT_VERIFIED，不能依据 `.sig` 存在或退出码推断有效。

`asset-plan` 对 Content 文件按显式路径规则分 A/B/C，缺规则和重复命中都标 REVIEW。分级不会自动创建 Chunk/PrimaryAssetLabel/AssetManager 或分配 secondary key。先在 Editor 审核依赖和加载关系后实现分块；全资源加密是全局开关，不能称为分级加密。分别评估 A 核心资源、B 普通资源、C 公开资源的收益，记录启动、加载、内存、补丁和 DLC 基线。

回滚仍使用普通 `rollback`。关闭某一开关只写该项 false，含义是放弃相应加密/签名保护；不会删除 key。所有修改保持原 INI 编码、无关配置、注释与数组；后续编辑冲突会阻止回滚。

## 版本文件完整性与 Steam Wrapper 产物

最终完成构建、DRM/签名、符号分离后再为确切 depot 创建 SHA256 清单；更新后创建新 build-id 和新清单。预览不写文件，创建需要明确确认。默认包含所有文件，包括 EXE/DLL/资源/配置；只有显式 mutable 路径被排除。manifest 存在构建外，不能覆盖。

```powershell
python -m steam_release_guard advanced integrity-create "D:/Builds/Final-001" --build-id "release-001" --output "D:/Private/release-001.json" --mutable "Saved/*" --dry-run --json
python -m steam_release_guard advanced integrity-create "D:/Builds/Final-001" --build-id "release-001" --output "D:/Private/release-001.json" --mutable "Saved/*" --yes --json
python -m steam_release_guard advanced integrity-verify "D:/Builds/Final-001" --manifest "D:/Private/release-001.json" --build-id "release-001" --expected-manifest-sha256 "REPLACE_WITH_TRUSTED_64_HEX" --json
python -m steam_release_guard advanced drm-inspect --original "D:/Private/original.exe" --wrapped "D:/Builds/Final-001/Game.exe" --expected-original-sha256 "REPLACE_WITH_PRE_WRAPPER_64_HEX" --json
```

把创建结果中的 manifest_sha256 固定到独立可信发布记录/CI/服务端，校验时传该值；不要从同一个可替换目录即时计算并当成信任依据。SHA256 清单不是数字签名，不防攻击者同时替换客户端验证器/清单。校验命令只读，报告改动、缺失、多出的文件。退出码 2 表示字节不符，不等于作弊或盗版。

运行时研究结论：可由启动器在游戏未运行、更新已结束时调用 `steam_release_guard.advanced.integrity.verify`，或在现有游戏框架中实现等价标准 SHA256 校验；应异步/分批处理，实测大资源 IO 成本，避免逐帧全量散列。可信清单/签名和重要状态优先由服务端验证。本模块没有注入游戏、内核驱动、反调试、自动删除或封禁逻辑；尚未验证任何游戏内运行时集成。遇到异常提示 Steam 验证文件/修复，保留存档和允许的 mod；合法补丁暂停检查并原子更新基线，不把旧版本清单套到新游戏。

原 `scripts/Invoke-SteamDrm.ps1` 保留原有上传明确确认。先独立记录原 EXE SHA256，再执行已授权 Wrapper。`drm-inspect` 检查原件未变、输出 PE 结构及差异，**不能单靠二进制变化证明 Wrapper 成功**。Wrapper 日志、Steam 启动、离线行为和测试分支重新安装全部需要真实验收；本模块不运行 EXE 或上传 Steam。

## 关键数据与多人客户端（只读）

```powershell
python -m steam_release_guard advanced security-inspect "D:/GameCopy" --json
```

直接输出文件、行号、候选问题、原因和修复方向，不写独立报告、不改源码、不连接服务器。覆盖字面量秘密、货币/背包/交易/奖励/结果、管理员标志、RPC、附近的本地随机数、调试入口、危险反序列化和证书绕过候选。发现 IsServer/HasAuthority/开发宏会记为上下文线索，不能认定安全或不安全；存在服务端检查时应逐条读取对应实现，避免重复开发。

主要建议：客户端提交操作意图，服务端验证身份、所有权、数量/余额/价格、时序、速率、重放和幂等性，并原子处理交易/结算/奖励。离线游戏的可编辑存档和显示用数值应按实际威胁模型处理，不能一律判成漏洞。Blueprint、外部服务、动态/编码数据和跳过的大文件明确未验证，正则扫描不能证明服务端缺乏校验。不会自行改服务器、撤销 key 或输出秘密值。

## 性能、兼容性和三层验收

```powershell
python -m steam_release_guard advanced acceptance-template
python -m steam_release_guard advanced acceptance-check "D:/Private/acceptance.json" --baseline-build "D:/Builds/Baseline" --candidate-build "D:/Builds/Protected" --baseline-manifest "D:/Private/baseline.json" --candidate-manifest "D:/Private/protected.json" --evidence-root "D:/Private/Measurements" --json
```

第一条仅打印模板。把对象保存为自己的 acceptance.json，填写不同 build-id 及从可信记录得到的两个 manifest_sha256；这两个清单分别由 integrity-create 创建。不要使用 `--json` 的外层 envelope 作为记录；若用 --json，取其 result 对象。

- 同一硬件/OS/引擎、场景、画质、网络条件和冷热缓存条件下，分别测基线与每个单项保护，再测组合。时间/内存/CPU/网络/存档指标至少三次；单次可用于实际文件/补丁字节、崩溃次数。记录测量工具。不要以 Editor Play Mode 代替分发的游戏。
- metrics 包含 startup_ms、scene_load_ms、memory_mib、cpu_percent、file_bytes、patch_bytes、crash_count、network_rtt_ms、save_read_ms、save_write_ms。file_bytes 自动计算清单范围；其他值需真实采样。每项填写 baseline_samples、candidate_samples 和自行选择的 max_regression_pct，未填阈值保持 NOT_VERIFIED。patch_bytes 使用实际 Steam/DLC 补丁产物，不能拿文件差异量冒充下载量。
- 私有 evidence 引用形式为 `{"path":"session/load-times.csv","sha256":"实际64位小写哈希"}`，路径相对 evidence-root。记录数据来源与过程，保留脱敏日志/录像/测量文件。工具只核对文件存在和哈希，不能自动判断录像/日志含义。
- runtime_checks 分别记录启动、资源、旧/新存档、联机、插件、离线、补丁、DLC、Steam 测试分支、调试入口。protection_checks 每个已启用保护单独填写 configuration、artifact、runtime。支持 PASS/FAIL/REVIEW/NOT_VERIFIED/NOT_APPLICABLE；不适用仍需人审，不能用来绕过必要验收。
- PASS 声明缺证据降为 NOT_VERIFIED；有匹配证据也只记 RECORDED_PASS。REVIEW/NOT_VERIFIED 原样保留，不自动批准发行。游戏文件、证据被改或指标回退超阈值会 BLOCKED。候选崩溃次数非零会阻断。

真实游戏验收当前尚未完成。待有可用磁盘、正确引擎、用户选择安装的保护器及游戏副本后执行；本工具不自动启动/上传真实游戏来补齐记录。
