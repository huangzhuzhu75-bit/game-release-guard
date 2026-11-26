# Unreal Engine 5 Windows 发布流程

前置阅读：[统一操作规则](../skills/game-release-guard/SKILL.md)。以下命令在工具仓库根目录运行；替换占位目录，保留原工程。

本页用于用户要求发布适配的场景。仅检查已有工程时，按 Skill 在对话中给出发现，不默认执行本页流程；audit 会写本地报告，须在用户要求报告后执行。apply 的授权范围包含配置修改、完整备份和本地报告。

1. 读取 `.uproject` 的 EngineAssociation，核实实际 UE 5.x 版本。自编译/GUID 关联版本不明时只审查，不篡改描述文件绕过检查。P0 沿用基础 INI 适配，不声称已具备逐小版本的真实构建验证。
2. 先检查并预览 Shipping / 排除调试文件的修改；检查平台 INI、Target.cs 和构建配置覆盖。

```powershell
python -m steam_release_guard plan 'D:/Games/MyUnrealGame' --json
python -m steam_release_guard audit 'D:/Games/MyUnrealGame' --json
python -m steam_release_guard apply 'D:/Games/MyUnrealGame' --dry-run --json
```

3. 首次试用先按 [完整备份与恢复](backup.md) 创建新的工程副本。用户已授权后关闭编辑器和同步工具，再适配；apply 会先完整备份工程到工程外并核验，失败就停止：

```powershell
python -m steam_release_guard apply 'D:/Games/MyUnrealGame' --yes --json
```

可选 Pak 索引加密必须单独说明范围并取得授权。要求工程已有合法非零 256-bit 密钥；缺失时由用户在对应引擎中处理，不替用户生成/轮换密钥。不要打印配置中的密钥值。

```powershell
python -m steam_release_guard plan 'D:/Games/MyUnrealGame' --encrypt-pak-index --json
python -m steam_release_guard apply 'D:/Games/MyUnrealGame' --encrypt-pak-index --dry-run --json
python -m steam_release_guard apply 'D:/Games/MyUnrealGame' --encrypt-pak-index --yes --json
```

4. 使用本工程对应的 RunUAT.bat 生成脚本。只生成，不自动调用引擎；保存后需审阅并获得实际构建授权。

```powershell
python -m steam_release_guard build-script 'D:/Games/MyUnrealGame' --tool 'D:/Engines/UE_5/Engine/Build/BatchFiles/RunUAT.bat' --output 'D:/Builds/MyUnrealGame-v1' --save 'D:/Builds/build-unreal-v1.ps1' --dry-run --json
python -m steam_release_guard build-script 'D:/Games/MyUnrealGame' --tool 'D:/Engines/UE_5/Engine/Build/BatchFiles/RunUAT.bat' --output 'D:/Builds/MyUnrealGame-v1' --save 'D:/Builds/build-unreal-v1.ps1' --yes --json
```

5. 核对 UAT 实际日志/receipt 中的 Shipping、Win64、nodebuginfo，以及原有 IoStore 设置是否保留。配置正确不等于产物正确。
6. 按 [发布包检查](security-audit.md) 分离符号、检查真正 depot 文件。保留未暂存进发布包的原始引擎符号，并核对其构建版本。不要将 DefaultCrypto.ini、私有备份、密钥或源码上传。
7. 对自己的实际构建，用版本匹配的官方引擎工具分别验证 Pak 索引访问、资源内容和 IoStore。当前工具不能证明容器加密有效；保留 REVIEW/NOT_VERIFIED。全资源加密和签名不由 P0 自动启用。
8. 实测正常启动、输入、插件、存档、联机、加载、补丁及调试控制台。Steam Wrapper/上传另行明确授权。

最终交付检查结果、恢复日志、实际构建证据、人工待办；失败时使用 [回滚流程](rollback.md)。
