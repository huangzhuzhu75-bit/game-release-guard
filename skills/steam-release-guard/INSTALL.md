[简体中文](INSTALL.md) | [English](INSTALL.en.md)

# 独立安装与 Markdown 使用

只需 `SKILL.md` 即可阅读和使用。分发时保留 [LICENSE](LICENSE)；本目录的 [EXAMPLES.md](EXAMPLES.md) 提供提示词。无需 Python、Release Guard、插件后台或全局 AI 配置。只有调用 Release Guard CLI 时才需要完整工具仓库及已有 Python 3.10+。

## 下载

打开 main 上的 [SKILL.md 源文件](https://github.com/huangzhuzhu75-bit/steam-release-guard/blob/main/skills/steam-release-guard/SKILL.md)，选择 Raw/Download raw file，保存为 UTF-8 的 `SKILL.md`，不要保存 GitHub 网页。另下载本目录 LICENSE。也可以从仓库 ZIP 中只取出 `skills/steam-release-guard/` 文件夹。

P0、P3 和 Skill 已按依赖顺序整合到 main。可以直接使用 [Raw 文件](https://raw.githubusercontent.com/huangzhuzhu75-bit/steam-release-guard/main/skills/steam-release-guard/SKILL.md) 和 [Raw 许可证](https://raw.githubusercontent.com/huangzhuzhu75-bit/steam-release-guard/main/skills/steam-release-guard/LICENSE)。可单独打包整个 `steam-release-guard/` 文件夹，保留双语安装说明和许可；不要包含任何游戏代码或资源。核心 Skill 正文目前为中文，只有一个知识源。

## 只安装到自己的游戏项目

先保存游戏工程和已有指令。手动创建下列目录，把同一份 `SKILL.md` 和 LICENSE 复制进去；目标已存在时先比较和备份，不覆盖用户的修改。不要把整个工具仓库复制到引擎的 Assets/Content 目录，也不要为此创建链接、安装 AI 或修改全局配置。

| 已安装客户端 | 游戏工程内的文件位置 | 读取方式 |
| --- | --- | --- |
| Claude Code | `.claude/skills/steam-release-guard/SKILL.md` | 在该项目启动新会话，使用 `/steam-release-guard` 或明确要求使用该 Skill。 |
| Codex | `.agents/skills/steam-release-guard/SKILL.md` | 在该项目启动新会话，使用 `$steam-release-guard`，让它先说明实际读取的文件。 |
| Gemini CLI | `.gemini/skills/steam-release-guard/SKILL.md` | 在该项目启动会话，查看 `/skills list`，要求使用该 Skill；客户端要求信任目录/激活确认时由用户决定。 |
| 其他工具或旧版本 | 任意项目内文档目录 | 明确要求完整阅读指定 `SKILL.md` 后再执行任务；不声称原生自动发现。 |

Gemini 当前官方文档还允许 `.agents/skills` 别名；表中选择独立路径以方便识别。不要在同一客户端的多个发现目录重复安装同名副本。这里只维护一个知识源，平台目录中的副本升级时从同一版本更新。

上表按 2026-11-25 官方文档核对，实际支持取决于下载者的客户端版本、工作目录、信任策略和 Skill 开关。安装目录正确不等于正文已被读取。先让 AI 说出文件路径、区分新项目开发和已有工程只读检查，并说明 audit 的报告副作用，再做实际任务。是否已经运行验证，以仓库验收记录为准，未实测平台保持 NOT_VERIFIED。

## 不安装：直接读 Markdown

把本文件夹放在游戏工程以外的文档目录也可以，告诉 AI：

> 完整阅读【SKILL.md 的本地路径】，按其中规则处理【游戏目录】。这次检查已有工程。先核对版本，仅在对话中给出具体文件位置、问题、风险、建议、已有保护和未验证项。

没有文件访问能力的工具只能阅读你提供的 Skill 和非敏感信息；它不能声称看过本地工程。不要为了使用 Skill 上传游戏源码、资源或密钥。使用云端 AI 时确认你的数据使用授权，Skill 不提供离线隔离。

## 项目入口、升级与卸载

原生 Skill 安装不要求额外建立 AGENTS.md/CLAUDE.md/GEMINI.md。本工具仓库保留这三个薄入口，是为了下载完整工具后直接读取同一个核心文件。

如希望新项目每次开发都应用规则，可以在**已有项目级**入口中手动追加一句“开始游戏开发或安全检查前完整读取【项目内 SKILL.md 路径】”。保留原有指令，勿覆盖整个入口，勿把本工具仓库的维护约束复制进游戏项目。没有必要时直接在会话中点名即可。

升级前备份旧 Skill，比较版本差异；新会话核对实际加载路径。卸载只移除本次安装的 Skill 文件和自己添加的引用，不删除工程代码、备份或用户其他指令。Skill 的安装/卸载本身不会给游戏应用或回滚保护配置。

## 官方格式依据

- [Agent Skills 格式](https://agentskills.io/specification)：标准 name/description frontmatter 和 Markdown 正文。
- [Claude Code Skills](https://code.claude.com/docs/en/skills)、[CLAUDE.md 导入](https://code.claude.com/docs/en/memory)。
- [Codex Skills](https://developers.openai.com/codex/skills)、[AGENTS.md](https://developers.openai.com/codex/guides/agents-md)。
- [Gemini CLI Skills](https://geminicli.com/docs/cli/skills/)、[GEMINI.md](https://geminicli.com/docs/cli/gemini-md/)。

[简体中文](INSTALL.md) | [English](INSTALL.en.md)
