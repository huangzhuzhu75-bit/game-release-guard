[简体中文](EXAMPLES.md) | [English](EXAMPLES.en.md)

# Game Release Guard：五引擎使用示例

先安装整个 Skill 目录，再把示例中的路径、版本和任务换成自己的。以下是可复制的请求，不代表你的工程已通过检查；AI 应实际读文件、按版本核对官方资料。新项目/授权开发可修改任务内代码，检查只读，明确加固才执行对应修改。结果在对话说明，不额外生成报告。

## 新项目：从第一天使用

> 读取【Skill 目录】/SKILL.md。我正在【工程目录】开发【Unity / Unreal / Godot / Cocos Creator / GameMaker】游戏，版本证据在工程里。先确认实际引擎和版本，只读对应引擎知识。请完成【具体功能】，验证不可信输入，隔离开发工具，保留已有结构和未提交内容。不要加入客户端高权限凭据、额外后端或不必要的加密，不生成安全报告。

例如新增玩家名称校验：验证类型、长度和允许字符，按现有界面处理失败。它不是付费解锁或联网身份认证，不需要为此搭建服务器。

## 检查已有项目

| 引擎 | 可直接复制的任务 |
| --- | --- |
| Unity | 只读检查 D:/Games/MyUnity。已有 IL2CPP 设置、Addressables 和开发快捷键，尚无打包结果。指出具体位置、已有保护、风险和建议，不改文件。 |
| Unreal | 只读检查 D:/Games/MyUE。Shipping、Pak 和 IoStore 配置都存在，缺少实际容器验证记录。分别说明配置证据及缺口，不改密钥或文件。 |
| Godot | 只读检查 D:/Games/MyGodot 的 project.godot 和 export_presets.cfg，判断脚本导出、PCK 加密前提、模板与资源包加载风险。不要把 config_version 当引擎版本，不改文件。 |
| Cocos Creator | 只读检查 D:/Games/MyCocos，先区分 Creator 版本和 Native/Web 目标。核对 Encrypt JS、JSC 证据、script-backup、远程 Bundle 和调试入口，不改文件。 |
| GameMaker | 只读检查 D:/Games/MyGM，区分 IDE 和 Runtime、VM/YYC/GMRT、目标平台及 Included Files。没有构建记录就说明未知，不改文件。 |

给出文件/位置、问题、影响、修复建议、已采用的保护及证据层级。编译、压缩和加密分别判断，不因没有源码命中就保证安全。凭据只报告类别和位置，不复述值。

## 明确要求加固：要实际实施

以下五项每次只选择当前工程适用的一项；统一前提是“先读核心和对应引擎文档，检查已有修改，核验工程外备份，只修改已授权范围，不生成独立报告”：

- **Unity**：在 D:/Games/MyUnity 隔离开发作弊快捷键，保留 Editor/Development 用法、序列化字段和存档契约；检查发布配置。有引擎才做授权构建，不安装混淆器或扩大类型名单。
- **Unreal**：在 D:/Games/MyUE 隔离正式构建中的开发控制台命令，保留现有容器策略和 Crypto Keys。不要为了保护启用不同容器或把 Pak 证据用于 IoStore。
- **Godot**：在 D:/Games/MyGodot 隔离 Release 的开发入口；评估既有 PCK preset。缺少匹配密钥的自定义模板时保留加密待办，继续适用的代码修改，不留下不可运行的导出设置。
- **Cocos Creator**：在 D:/Games/MyCocos 按实际版本隔离调试入口，修正已确认的发行复制清单。仅在明确的 Native 目标和现有密钥条件下评估 Encrypt JS；不删除源码、bootstrap JS 或未知资源，不套到 Web。
- **GameMaker**：在 D:/Games/MyGM 隔离开发作弊入口，保留正常存档和 Included Files。核实目标、许可证和组件后评估 YYC，不擅自安装组件或把 YYC 当资源加密。

完成后在对话说明改过哪些文件、备份和恢复方式、做过哪些验证。没有引擎/工具链时可完成静态加固，但实际构建、启动、资源加载、存档、联网和更新仍无法据此确认。

## 使用 Unity / Unreal 本地工具

> Game Release Guard 在 D:/Tools/game-release-guard。读 README、CLI 和备份实现，确认真实命令；现在只对 D:/Games/MyGame-Copy 运行 plan，解释备份和报告副作用，不 apply。

保留 `python -m steam_release_guard`。`apply` 写配置与报告，`rollback` 只撤回工具改动，完整恢复到新目录；不发明 protect-all、steam-upload、audit --no-report 或另外三引擎的 CLI。

[简体中文](EXAMPLES.md) | [English](EXAMPLES.en.md)
