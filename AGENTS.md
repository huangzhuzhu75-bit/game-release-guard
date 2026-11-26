# Steam Release Guard 项目指令

开始任务时先完整读取 [统一 Skill / Markdown 操作说明](skills/steam-release-guard/SKILL.md)，按其中的新项目开发、已有项目只读检查、已授权工具操作三种场景处理。这是明确的读取指令，普通 Markdown 链接不代表原生 Skill 已自动加载。只有实际需要调用工具时，再读对应的 [Unity](workflows/unity-release.md)、[Unreal](workflows/unreal-release.md)、[安全检查](workflows/security-audit.md) 或 [回滚](workflows/rollback.md) 工作流及真实代码。

先核实项目目录、引擎精确版本。已有工程检查默认只读、仅在对话中给出位置/风险/建议，不改代码、不生成报告；audit 即使带 --json 也会写报告，不能默认调用。执行已授权的工具操作前先 plan/预览，或在用户要求报告后 audit。其余操作边界以统一 Skill 为准。

首次使用真实游戏先读 [完整备份与恢复](workflows/backup.md)，在恢复的新副本上尝试。apply 有文件变更时必须先成功完成工程外的完整文件备份与核验；不绕过该步骤、不上传备份、不强制覆盖恢复目标。

修改本工具时保留 Python 3.10+ 标准库架构、旧 CLI/GUI/报告及回滚兼容性。执行 `python -m unittest discover -s tests -v`，不删除或削弱旧测试。用户在 2026-11-25 明确授权独立 P3 分支开发，并允许在缺少 UE/许可证/实机条件时将真实引擎验收记为 NOT_VERIFIED；2026-11-26 用户另行授权整合，PR #2 再 PR #1 已按依赖合并到 main；这不代表真实游戏保护验收通过。高级操作先读 [P3 工作流](workflows/advanced-protection.md) 与对应实际代码。仓库 AI 适配只维护 Markdown，不构建 AI 管理系统，不修改全局 AI 配置。
