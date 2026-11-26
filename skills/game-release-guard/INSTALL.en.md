[简体中文](INSTALL.md) | [English](INSTALL.en.md)

# Game Release Guard: universal setup and use

Download once for Unity, Unreal, Godot, Cocos Creator and GameMaker. One core Skill selects the relevant engine guidance. Python and the local toolkit are not required.

## Give this to your AI

```text
Read README.en.md and skills/game-release-guard/SKILL.md at https://github.com/huangzhuzhu75-bit/game-release-guard.
Set up the entire game-release-guard Skill folder, including engines/ and LICENSE, for this project. Use project-level native Skill support if available; otherwise read it as Markdown.
Identify the engine and version, then read only its engine guide. Preserve existing instructions. Do not overwrite files, change global configuration or install extra software.
State the actual path and wait for my task: review means read-only; an explicit hardening request means back up, implement scoped changes and verify. Do not upload the project or create a separate report.
```

## Download manually

Download the [standalone Skill ZIP](https://github.com/huangzhuzhu75-bit/game-release-guard/raw/refs/heads/main/downloads/game-release-guard-skill.zip). Extract and keep the entire `game-release-guard/` folder: [SKILL.md](SKILL.md), five `engines/` guides, bilingual instructions/examples and [LICENSE](LICENSE). Copying only SKILL.md leaves required engine references behind.

Point your assistant at SKILL.md. It identifies the project before reading the relevant engine file. Native Skill clients can use their current project-level installation method; other assistants read the Markdown. If file access is unavailable, provide the core and relevant engine document text. Do not upload game code, assets or secrets just to install it.

## Three modes

- **Develop:** “Use Game Release Guard. Check the engine version at [project path], then develop [feature] using secure practices.”
- **Review:** “Review [project path] read-only. Identify file locations, risks and recommendations in this conversation. Do not edit files, run builds or create reports.”
- **Harden:** “Harden [specific scope] in [project path]. Check existing changes/protection, create a recoverable backup, implement applicable edits and verify them. Explain results here; do not rotate production keys, upload the project or create a report.”

[Five-engine examples](EXAMPLES.en.md). Core guidance is Chinese; request replies in your preferred language. Installing a Skill does not encrypt a game. Hardening requires project access and authorization for its scope.

## Update, migrate or remove

The previous name was steam-release-guard. Back up the old Skill and your edits, compare changes, then migrate to `game-release-guard`. Avoid activating both old/new copies in the same client. Preserve existing project instructions and update only your Skill reference; leave global configuration alone.

Update the entire folder, not just the core file. Removal deletes only the Skill and references you added, not game code or backups. Installing/removing the Skill does not apply or roll back protection.

Local tools still support Unity / Unreal only and use `python -m steam_release_guard`. Download the full repository only when those tools are needed, and inspect the real CLI/workflows first. The other three engines have no local automated encryption adapter.

[简体中文](INSTALL.md) | [English](INSTALL.en.md)
