# 下载后，直接让 AI 读这份说明

解压完整仓库，在仓库根目录打开你正在使用的 AI 工具。无需安装 Claude Code、Gemini CLI 或任何 AI 管理组件；本工具运行只需已有的 Python 3.10+，桌面界面另需 tkinter。

首次试用先按 [完整备份与恢复](workflows/backup.md) 保留整个工程目录，并恢复新副本，在副本上尝试。apply 也会在修改前强制完成独立的完整备份与核验。

复制下面这段话，把工程目录换成自己的真实目录：

> 请先完整读取 `skills/steam-release-guard/SKILL.md`，再读取与我的引擎对应的 `workflows/unity-release.md` 或 `workflows/unreal-release.md`。我的游戏工程是【填写目录】，已打包构建是【填写目录，或写“尚未构建”】。先确认引擎版本，运行 plan 或 audit，解释修改范围、备份和未验证事项。未经我授权不要修改配置、密钥、删除文件、上传源码/资源或上传 Steam。完成后给我检查结果，保留 REVIEW 和 NOT_VERIFIED。

如果 AI 无法访问本地文件，先把 [统一操作说明](skills/steam-release-guard/SKILL.md) 及相应工作流的文本交给它阅读；命令由你在本地执行。不要为此上传游戏源码、资源、密钥或私有备份。仅下载这份 Markdown 可以阅读流程，执行 CLI 需要完整仓库。

## 入口与验收边界

| 工具 | 项目入口 | 当前证据 |
| --- | --- | --- |
| 通用 AI / 人工操作 | 本页 → [统一操作说明](skills/steam-release-guard/SKILL.md) | Markdown 链接、命令与 CLI 对照验证；无需原生 Skill 支持 |
| Codex | [AGENTS.md](AGENTS.md) | 项目指令格式按官方文档；本机 CLI 0.171.0-alpha.13，Markdown 可直接读取；原生 Skill 自动发现 NOT_VERIFIED |
| Claude Code | [CLAUDE.md](CLAUDE.md) | 官方项目文件及 `@` 导入格式；本机未安装，实际客户端读取 NOT_VERIFIED |
| Gemini CLI | [GEMINI.md](GEMINI.md) | 官方项目文件及 `@` 导入格式；本机未安装，实际客户端读取 NOT_VERIFIED |
| 其他 AI 工具 | 手动提供 Markdown | 不声称原生 Skill 支持，也不修改全局设置 |

根据用户决定，不为验收安装缺失的 AI CLI。`skills/steam-release-guard/` 是说明源，不是声称所有工具自动扫描的目录。没有注册脚本、后台服务或管理系统。

如果下载者已经安装相应客户端，可在项目根目录让它列出实际读到的文件、复述“先 plan/audit”“不修改密钥”“不将 REVIEW/NOT_VERIFIED 标为 PASS”，再只执行一次 `plan --json` 检查。记录客户端版本与实际输出后才能把该项标为已验证；阅读成功不代表游戏保护验收通过。

## 官方格式依据

核对日期：2026-11-25。Claude/Gemini 未指定本机版本，Context7 官方仓库资料与当前官方文档只能证明格式依据，不能替代某个已安装版本的实测。

- [Claude Code 项目指令与导入](https://code.claude.com/docs/en/memory)：根目录 `CLAUDE.md`，相对 `@path` 导入。
- [Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md)：根目录项目级 Markdown 指令；链接由 AI 按指令读取。
- [Codex Skills](https://developers.openai.com/codex/skills)：原生仓库发现目录与本项目的通用 `skills/` 说明路径不同，本项目不自动注册。
- [Gemini CLI GEMINI.md](https://geminicli.com/docs/cli/gemini-md/)：项目 Markdown 上下文及相对文件导入。

工作流：[Unity](workflows/unity-release.md) · [Unreal](workflows/unreal-release.md) · [安全和发布包检查](workflows/security-audit.md) · [回滚和失败暂存清理](workflows/rollback.md)。
