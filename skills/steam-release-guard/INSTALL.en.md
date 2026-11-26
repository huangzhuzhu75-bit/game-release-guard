[简体中文](INSTALL.md) | [English](INSTALL.en.md)

# Universal AI guide

One [SKILL.md](SKILL.md), one set of prompts. Give your assistant the repository URL and the prompt below. You do not need Python or the Steam Release Guard application to use the Skill.

## Ask your assistant to install or read it

```text
Read README.en.md and skills/steam-release-guard/SKILL.md at https://github.com/huangzhuzhu75-bit/steam-release-guard. Set up and use this Skill for my current game project.
If you support native Skills, use your current client's project-level installation method; otherwise read and follow the Markdown directly. Keep LICENSE and existing instructions. Do not overwrite same-named files, change global configuration or install extra software.
Briefly state the source you read or the path you saved, then wait for my development or review task. Installing the Skill does not authorize game edits, builds, reports or project uploads.
```

An assistant with native Skill support can use its own installation method. Others can read the Markdown directly. Installation adds guidance; it does not automatically enable obfuscation, encryption or any other protection in your game.

## Download manually

1. Download the [standalone Skill ZIP](https://github.com/huangzhuzhu75-bit/steam-release-guard/raw/refs/heads/main/downloads/steam-release-guard-skill.zip) and extract it into your documentation folder.
2. Give your assistant the path to `steam-release-guard/SKILL.md`, or provide the file's text in the conversation.
3. Choose a development or review task below. Keep [LICENSE](LICENSE) when redistributing the Skill.

You can also save [raw SKILL.md](https://raw.githubusercontent.com/huangzhuzhu75-bit/steam-release-guard/main/skills/steam-release-guard/SKILL.md) and [raw LICENSE](https://raw.githubusercontent.com/huangzhuzhu75-bit/steam-release-guard/main/skills/steam-release-guard/LICENSE) individually. Save the Markdown source, not the GitHub web page. The ZIP contains only the Skill, its license and these bilingual guides, with no engine, application or game content.

An assistant without internet access can read local files; one without filesystem access can read the Skill text you provide. Do not upload game code, assets or secrets just to configure it. The core text is Chinese; ask for replies in your preferred language.

## Universal task prompts

**New game or authorized feature development:**

```text
Use the Steam Release Guard Skill. My project is [Unity / Unreal, project path], and this task is [specific feature]. Check the engine version and project instructions first. Follow secure development practices within this feature's scope, without generating an extra security report.
```

**Existing-game review:**

```text
Use the Steam Release Guard Skill for a read-only review of [project path]. Check the engine version first. In this conversation, identify specific files or locations, explain the risks and suggest fixes. Recognize existing protection and missing evidence. Do not edit files, run builds, create reports or upload the project.
```

[Unity, Unreal and toolkit examples](EXAMPLES.en.md)

## Update or remove

Keep the previous version and compare changes before updating. Do not overwrite a same-named file. Ask the assistant to briefly identify the version or path it actually read. For ongoing use, add a Skill reference to your current game's existing project instructions while preserving their contents.

To remove it, delete only the Skill files you added and your own references. Leave game code, backups and unrelated instructions in place. Installing or removing the Skill does not apply or roll back game protection.

The standalone Skill has no CLI. Download the full repository only when you need toolkit operations such as backups or release adaptation. Read the corresponding README, workflow and actual code before running an existing command.

[简体中文](INSTALL.md) | [English](INSTALL.en.md)
