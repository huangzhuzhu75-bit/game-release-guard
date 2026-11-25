# Unity 6 Windows 发布流程

前置阅读：[统一操作规则](../skills/steam-release-guard/SKILL.md)。在工具仓库根目录运行下面命令；替换占位目录。保留原工程和原构建。没有独立 AI 服务或自动安装步骤。

1. 读取工程 `ProjectSettings/ProjectVersion.txt`，核实精确的 6000.x Editor。其他版本停止自动适配。确认 Python 3.10+、Unity 许可证、Windows IL2CPP 模块、C++ 工具链和插件兼容性；本 P0 不自动验证/安装这些依赖。
2. 先检查并解释拟修改的文件。apply 只安装 Editor 适配器和更新 `.gitignore`；不是执行引擎构建。

```powershell
python -m steam_release_guard plan 'D:/Games/MyUnityGame' --json
python -m steam_release_guard audit 'D:/Games/MyUnityGame' --json
python -m steam_release_guard apply 'D:/Games/MyUnityGame' --dry-run --json
```

3. 首次试用先按 [完整备份与恢复](backup.md) 创建新的工程副本。用户已授权适配范围后，关闭编辑器和同步工具，核实工程外的完整备份位置，再执行；apply 会自动完整复制并核验，失败就停止：

```powershell
python -m steam_release_guard apply 'D:/Games/MyUnityGame' --yes --json
```

4. 使用工程准确版本 Unity.exe 生成构建脚本；先预览，再经授权保存。CLI 不执行脚本。

```powershell
python -m steam_release_guard build-script 'D:/Games/MyUnityGame' --tool 'D:/Engines/Unity/Editor/Unity.exe' --output 'D:/Builds/MyUnityGame-v1' --save 'D:/Builds/build-unity-v1.ps1' --dry-run --json
python -m steam_release_guard build-script 'D:/Games/MyUnityGame' --tool 'D:/Engines/Unity/Editor/Unity.exe' --output 'D:/Builds/MyUnityGame-v1' --save 'D:/Builds/build-unity-v1.ps1' --yes --json
```

5. 审阅脚本、场景和构建配置；获得执行引擎构建的授权后运行生成的文件，或在 Unity 使用 **Tools → Steam Release Guard → Build Windows Release**。目标为 Windows x64、IL2CPP、非 Development、关闭脚本调试和分析。自定义 Build Profile 会被拒绝，需要人工集成；普通 Unity Build 按钮不自动使用此适配器。构建失败则保留日志，不拿旧构建替代新输出。
6. 实际构建完成后，按 [发布包检查](security-audit.md) 分离符号并检查最终目录。检查 GameAssembly.dll、metadata、Managed DLL、boot.config、私有符号、StreamingAssets/Bundle/Addressables；文件存在只是指标。
7. 用最终构建验证启动、旧/新存档、反射/序列化、插件、联机、离线、测试菜单/跳关/快捷键、性能和更新。没有证据标 NOT_VERIFIED，需要人工判断标 REVIEW；不把 IL2CPP 写成资源加密或防破解保证。

最终记录：工程与版本、改动清单、恢复日志、实际构建命令/日志、报告路径、私有符号目录、兼容性与 Steam 测试待办。异常时按 [回滚](rollback.md) 处理；引擎强退后的 PlayerSettings 恢复需另查工程版本控制。
