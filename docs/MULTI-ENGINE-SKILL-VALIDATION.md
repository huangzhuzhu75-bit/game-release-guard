# Game Release Guard — Multi-Engine AI Skills V1.0 验证

日期：2026-11-27。范围：统一 Skill、五份引擎知识、三种操作场景、双语入口和独立 ZIP。本次不安装引擎，不构建真实游戏，不修改 Python 本地适配器。

## 可复现输入与方法

使用 [合成夹具生成器](../tests/fixtures/create_skill_scenarios.py)创建全新目录，五种引擎各有 new / existing 两个最小输入。它们只用于文件识别与代码级行为验证，不是可完整构建的游戏。凭据标记和资源均为合成数据，没有真实游戏或密钥。

```shell
python tests/fixtures/create_skill_scenarios.py D:/TemporaryEvaluation/GameReleaseGuard
```

目标目录必须不存在。输入包含版本证据、已有调试隔离、未隔离开发入口、未知资源、用户本地改动及非功能性凭据标记。Unity IL2CPP / UE Shipping 与容器配置作为已采用保护的识别样本；GameMaker 故意没有 Runtime 记录，Godot 仅给版本线索。

独立 AI 先获得核心 Skill、真实任务和原始夹具，不提供预期答案。只读检查与新功能开发之后，主控核验文件；再单独授权对开发入口加固。只读取当前引擎文档。测试记录与备份留在私有测试目录，结果在对话返回，不要求被测 AI 创建审计报告。

新项目任务为显示名校验（ASCII 字母、数字、下划线，长度 1–16）；已有项目先只读检查，再明确授权隔离发行构建的开发奖励入口。核对文件哈希、修改范围、备份可恢复性、语法/可执行验证及诚实的证据限制。

## 验证结果

在本会话独立 Codex 评估执行单元中完成 A/B/C 请求；没有把这些结果当作引擎产物或运行验收。主控另行检查文件差异和哈希，现有项目只读阶段共 **43/43 原文件不变**，没有新增报告或修复文件。新项目原有 **38/38 文件不变**，每个样本只新增一份显示名校验代码。

| 引擎 | 识别与只读检查 | 新功能开发 | 授权加固与验证边界 |
| --- | --- | --- | --- |
| Unity | 6000.0.40f1；发现 F10 奖励缺少隔离，识别既有 DevLog 条件；不凭 Standalone 数字配置断言产物 | 新增独立 C# 函数，编译及 65,578 次输入检查通过 | 实际添加 UNITY_EDITOR / DEVELOPMENT_BUILD 条件；四种宏组合的最小 API 替身编译检查通过，不是 Unity 构建 |
| Unreal | 5.6 关联与 5.6.1 复制记录分开；发现开发控制台、配置字段疑点；Pak/IoStore 不混用证据 | 新增标准 C++ 校验函数；无编译器，静态复核 | 实际用 !UE_BUILD_SHIPPING 包围开发命令注册与回调；保留 Coins、容器与其他配置，无 UE 编译 |
| Godot | 4.5 版本线索，不把 config_version=5 当引擎 5；识别已有日志隔离、缺自定义模板 | 新增 Variant/String 校验；源码复核，无 GDScript 执行 | 实际新增 OS.is_debug_build() 入口条件；没有改成不具备前提的 PCK 加密 |
| Cocos Creator | creator.version=3.8.8，不采用包版本 9.9.9；识别 Windows Native、已有 DEBUG 日志与无条件奖励 | 新增 TypeScript 校验，Node 24.22.0 执行 414 项检查通过 | 实际用 DEBUG 隔离事件注册及直接调用；12 项受控方法检查通过，不是 Creator 编译 |
| GameMaker | IDE 2024.14.1.207 不当 Runtime；VM/YYC/GMRT 与精确 Runtime 保留未知 | 新增 GML 类型/长度/字符校验；源码复核，无 GML 执行 | 实际使用 debug_mode 条件；未启用或宣称 YYC / 资源加密 |

每个授权加固样本均先建立工程外完整副本并核验；主控将五个备份恢复到五个全新目录，**43/43 文件与最初原件哈希一致**。加固工程各仅改变一份获准源码，其余 **38/38 原文件不变**，没有新增文件；未知资源、私有配置、用户本地内容保留。Godot/GameMaker 等运行条件不能证明开发代码已物理移除；Cocos 受控方法与 Unity API 替身测试也不能代替实际引擎。五份检查回复仅给凭据类别/位置，未复述非功能性凭据标记，没有把“存在字段”断言为真实泄露。

### 首轮问题与独立复测

UE 首轮评估曾把 `bIncludeDebugFiles=False` 当作调试文件已排除。主控复核后撤回该结论，在 Unreal 指南补充核对 INI 节名及真实属性名的要求。另一位未读首轮结果的评估者重新读取当前 Skill 和原始 UE 样本，正确指出该字段不能证明保护生效，并保留实际 5.6.1 属性/产物验证限制；复测 **10/10 文件未变**。首轮这一项不记成功。

官方滚动 API 与可访问的 5.5/5.8 属性表使用 `IncludeDebugFiles`；本轮 5.6 API 路由不可访问且无本地头文件，没有将其他版本页面包装成现场 5.6.1 验证。这个案例说明 Skill 仍需要使用者审阅具体证据。

## 本地工具与分发验证

- Windows 10 / Python 3.12.14：原有 **126 项测试，125 通过、1 跳过**；跳过为宿主缺符号链接权限，未删除或降低测试。
- 文档命令用实际 CLI parser 核对；中英文 README 命令一致。后续文案修改重跑 4 项文档检查通过。
- Skill Creator 的 quick_validate 使用已有 D 盘环境通过；默认 Python 缺 PyYAML，未安装依赖。校验只证明格式，不代替行为测试。
- ZIP 只含 11 个允许文件，按规范化 UTF-8 内容逐字核对，拒绝多余/缺失/重复项。MIT 原版权声明保留。双语首页本地链接、锚点、22 个通用 AI 按钮及安装提示词一致。
- Python 核心、CLI、GUI、Unity/Unreal 适配器、备份及回滚源文件相对本轮基线没有变化；没有新引擎适配器或后台服务。
- CI 继续运行 Windows / Linux × Python 3.10 / 3.12，并检查新版 ZIP。提交结果以 [Actions](https://github.com/huangzhuzhu75-bit/game-release-guard/actions) 对应 SHA 为准。

## 兼容和来源边界

核心 Skill 和五份引擎知识是 Markdown 指引。通用 AI 入口不宣称每个客户端的原生安装器已实测；此前 Codex 旧版发现记录见 [历史验收](SKILL-VALIDATION-20261125.md)。本次独立评估不能代替 Claude Code / Gemini CLI 原生安装验收。

官方来源分别列在 [Unity](../skills/game-release-guard/engines/unity.md)、[Unreal](../skills/game-release-guard/engines/unreal.md)、[Godot](../skills/game-release-guard/engines/godot.md)、[Cocos Creator](../skills/game-release-guard/engines/cocos-creator.md)、[GameMaker](../skills/game-release-guard/engines/gamemaker.md)。Context7 返回未锁定版本索引，进一步核对 Godot 4.5、Cocos 3.8/4.0 LTS 及 GameMaker monthly 官方页面；不将这些页面当作所有小版本的兼容证明。

Godot PCK、Cocos JSC、GameMaker YYC 和既有 Unity/Unreal 高级保护的真实构建、资源读取、启动、存档、插件、联机、更新和性能不在本轮验证范围。没有将配置、编译、压缩或后缀写成加密成功。
