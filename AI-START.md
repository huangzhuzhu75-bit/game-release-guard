# 下载后，让 AI 直接读取

核心知识只有 [skills/steam-release-guard/SKILL.md](skills/steam-release-guard/SKILL.md) 一份，可以独立使用。项目级安装路径、单文件下载和通用 Markdown 方式见 [安装说明](skills/steam-release-guard/INSTALL.md)，真实路径提示词见 [使用示例](skills/steam-release-guard/EXAMPLES.md)。

## 两种日常用法

新项目或已经授权的功能开发：

> 请完整读取【SKILL.md 本地路径】，先核对【游戏目录】的引擎版本和已有结构，按其中规范完成【明确的开发任务】。把安全性融入代码，不额外生成安全报告。

检查已有项目：

> 请完整读取【SKILL.md 本地路径】，检查【游戏目录】的安全风险。已有发布包在【目录，或“尚未构建”】。指出具体文件/位置、问题、原因、建议、已有保护和未验证项。

第二种用法默认只读，不改代码、不创建独立报告。若 AI 无法读本地文件，提供 Skill 文本及非敏感项目信息即可；它不能声称已经检查工程，不要为此上传源码、资源或密钥。

## 需要发布适配时

只有用户要求调用 Release Guard 时，才读取本仓库 README、相关工作流和实际 CLI 代码，核对版本与 --help；先 plan/预览或已授权的 audit。**audit 即使加 --json 也会写 HTML/JSON 报告，没有 --no-report。** 不应把“检查工程”自动变成运行 audit。

实际适配先按 [完整备份与恢复](workflows/backup.md) 保留工程，并在恢复的新副本尝试；apply 有变更时会强制完整备份及核验，随后生成本地报告。风险授权、回滚和能力边界统一遵循 Skill。

## 平台入口与证据

| 平台 | 完整仓库入口 / 独立安装 | 验收边界 |
| --- | --- | --- |
| Codex | [AGENTS.md](AGENTS.md) / 项目 .agents/skills | 本机 0.171.0-alpha.13；原生发现 4/4，四个合成任务均完整读取正文并完成设计/只读检查；真实游戏运行未验证。 |
| Claude Code | [CLAUDE.md](CLAUDE.md) / 项目 .claude/skills | 官方格式核对；本机未安装，实际读取/行为 NOT_VERIFIED。 |
| Gemini CLI | [GEMINI.md](GEMINI.md) / 项目 .gemini/skills | 官方格式核对；本机未安装，实际读取/行为 NOT_VERIFIED。 |
| 其他 AI | 显式读取指定 SKILL.md | 通用 Markdown；不声称原生自动发现或特定客户端实测。 |

不为验证安装缺失客户端，不注册后台服务，不修改全局配置。安装成功、被发现、正文被读、行为符合要求是不同证据；不能仅凭文件存在就宣布平台通过。验收方法和限制见 [Skill 验收记录](docs/SKILL-VALIDATION-20261125.md)。

## 官方依据

2026-11-25 核对：[Claude Code Skills](https://code.claude.com/docs/en/skills)、[项目指令](https://code.claude.com/docs/en/memory)；[Codex Skills](https://developers.openai.com/codex/skills)、[AGENTS.md](https://developers.openai.com/codex/guides/agents-md)；[Gemini Skills](https://geminicli.com/docs/cli/skills/)、[GEMINI.md](https://geminicli.com/docs/cli/gemini-md/)。

工作流：[Unity](workflows/unity-release.md) · [Unreal](workflows/unreal-release.md) · [安全与发布包检查](workflows/security-audit.md) · [回滚和失败暂存清理](workflows/rollback.md)。
