[简体中文](INSTALL.md) | [English](INSTALL.en.md)

# Standalone installation and Markdown use

You only need `SKILL.md` to read and use the guidance. Keep [LICENSE](LICENSE) when distributing it; [EXAMPLES.md](EXAMPLES.md) contains additional prompts. No Python, Release Guard installation, background service or global AI configuration is required. Python 3.10+ and the full toolkit are needed only when you choose to use its CLI.

## Download

Open [SKILL.md on main](https://github.com/huangzhuzhu75-bit/steam-release-guard/blob/main/skills/steam-release-guard/SKILL.md), choose Raw/Download raw file, and save the UTF-8 Markdown file rather than the GitHub web page. Also download its LICENSE. Alternatively, take only `skills/steam-release-guard/` from the repository ZIP.

P0, P3 and the Skill have been integrated into main in dependency order. Direct downloads: [raw Skill](https://raw.githubusercontent.com/huangzhuzhu75-bit/steam-release-guard/main/skills/steam-release-guard/SKILL.md) and [raw license](https://raw.githubusercontent.com/huangzhuzhu75-bit/steam-release-guard/main/skills/steam-release-guard/LICENSE). You may package the entire `steam-release-guard/` folder independently, retaining the bilingual installation notes and license. Never include game code or assets. The canonical Skill is currently written in Chinese; there is only one knowledge source.

## Install inside your game project

Save your project and existing instructions first. Manually create the appropriate directory below and copy the same `SKILL.md` and LICENSE into it. If files already exist, compare and back them up instead of overwriting changes. Do not copy the whole toolkit into the engine's Assets/Content directory, create links, install an AI client, or alter global configuration just to use this Skill.

| Installed client | File inside your game project | How to read it |
|---|---|---|
| Claude Code | `.claude/skills/steam-release-guard/SKILL.md` | Start a new project session and use `/steam-release-guard`, or explicitly request this Skill. |
| Codex | `.agents/skills/steam-release-guard/SKILL.md` | Start a new project session, use `$steam-release-guard`, and ask which file was actually read. |
| Gemini CLI | `.gemini/skills/steam-release-guard/SKILL.md` | Start a project session, inspect `/skills list`, and request the Skill. Decide any directory-trust or activation prompts yourself. |
| Other tools or older clients | Any project documentation directory | Explicitly ask the assistant to read the entire file. Do not assume native discovery. |

Gemini's documented `.agents/skills` alias is another option; the table uses a dedicated directory for clarity. Do not install duplicate copies of the same Skill into multiple discovery paths for one client. Update project copies from the same canonical version.

Paths were checked against official documentation on 2026-11-25. Support depends on your client version, working directory, trust settings and Skill configuration. A correct path does not prove the body was read. Ask the assistant to identify its source, distinguish new development from read-only inspection, and explain that Release Guard `audit` writes reports before it acts. Codex discovery and four synthetic scenarios were tested; Claude Code and Gemini CLI execution remain **NOT_VERIFIED**. Other clients have a Markdown fallback, not a verified native integration.

## Use Markdown without installation

You can keep the folder outside the game project and tell your assistant:

> Read [local path to SKILL.md] in full and apply its rules to [game directory]. This is an existing-project inspection. Check the engine version first. Describe file locations, risks, recommendations, existing protections and unverified items in this conversation only. Do not edit files, run audit, create reports or upload project data.

A tool without filesystem access can only inspect the Skill and non-sensitive information you provide. It must not claim to have inspected your local project. Do not upload game code, assets or secrets just to use the Skill. Confirm the data scope when using cloud AI; this document does not create offline isolation.

## Entry files, updates and removal

Native Skill installation does not require an extra AGENTS.md, CLAUDE.md or GEMINI.md. The full toolkit keeps thin entry files so clients can read the same canonical source.

For ongoing development, optionally append a short instruction to an **existing project-level** entry file: “Before game development or security review, read [project Skill path] in full.” Preserve existing instructions. Do not replace the entry file or copy toolkit-maintenance constraints into your game project. Naming the Skill in a conversation is sufficient when persistent instructions are unnecessary.

Before updating, back up the old Skill and compare changes. In a new session, check the loaded path. To uninstall, remove only the Skill files you installed and the references you added. Keep game code, backups and unrelated instructions. Installing/removing this Skill does not apply or roll back game protection settings.

## Official format references

- [Agent Skills specification](https://agentskills.io/specification): name/description frontmatter and Markdown body.
- [Claude Code Skills](https://code.claude.com/docs/en/skills), [CLAUDE.md imports](https://code.claude.com/docs/en/memory).
- [Codex Skills](https://developers.openai.com/codex/skills), [AGENTS.md](https://developers.openai.com/codex/guides/agents-md).
- [Gemini CLI Skills](https://geminicli.com/docs/cli/skills/), [GEMINI.md](https://geminicli.com/docs/cli/gemini-md/).

[简体中文](INSTALL.md) | [English](INSTALL.en.md)
