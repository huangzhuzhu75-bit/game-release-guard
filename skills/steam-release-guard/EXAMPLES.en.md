[简体中文](EXAMPLES.md) | [English](EXAMPLES.en.md)

# Example prompts

Follow [INSTALL.en.md](INSTALL.en.md) to install the Skill or point your assistant at the actual [SKILL.md](SKILL.md) file. Replace the example paths below. These are prompts, not claims that your game has been tested. A review stays in the conversation; subsequent edits need authorization for their scope.

## New Unity project

> Use steam-release-guard. D:/Games/MyNewUnityGame is a newly initialized Unity project for an offline Windows/Steam game. Read its version and structure first, then implement a small initial inventory/save feature following the Skill. Limit changes to that feature. Do not add a server, obfuscator or always-online requirement for piracy prevention, and do not generate a security report.

Expected behavior: check the engine version, preserve the original project, separate runtime and Editor functionality, avoid claims that client-side encryption is unbreakable, and keep existing saves. Describe file changes, save compatibility and engine execution as separate outcomes.

## New Unreal multiplayer project

> Use steam-release-guard. D:/Games/MyNewUEGame will be a multiplayer game with an item economy. Read .uproject and the existing networking approach. Propose an initial item-purchase flow and pseudocode in this conversation, without writing files. Explain what the client submits, what a trusted server validates, and where real authentication and storage still need integration.

Expected behavior: the client submits purchase intent rather than authoritative prices or balances. The server decides the outcome using identity, item/price checks, balances and idempotent transactions. Do not invent an existing server or Steam verification. Explain the host trust limitation of a Listen Server and the different roles of Shipping and encryption.

## Review an existing Unity project

> Use steam-release-guard to review D:/Games/ExistingUnity. IL2CPP is configured, but we do not have this release's build yet. Identify specific files/lines, explain each issue and risk, and suggest fixes. Recognize protection supported by evidence and identify what remains unverified. Review only.

For example, an F8 money-grant shortcut in runtime code without build isolation should be located precisely, with runtime reachability still checked. An Editor-only file containing “cheat” is not automatically a release vulnerability. IL2CPP configuration can be confirmed while build/runtime behavior remains NOT_VERIFIED. Do not run the report-writing audit command automatically.

## Review an existing Unreal project

> Use steam-release-guard to review D:/Games/ExistingUE. We enabled Shipping, IoStore and Pak index encryption and want to understand whether that is enough. No packaging logs are available. Explain findings by file location. Do not edit files or create reports.

Expected behavior: inspect the actual settings and overrides; explain that Pak index encryption does not prove IoStore content encryption, Server RPCs still require input validation, and signing does not provide confidentiality. Container/runtime conclusions without evidence remain NOT_VERIFIED. Do not generate or rotate Crypto Keys.

## Use the toolkit after authorization

> I also have the Steam Release Guard repository at D:/Tools/steam-release-guard. Read its README, CLI and backup implementation to confirm the actual commands. Run only plan on D:/Games/MyGame-Copy, and explain the scope of full backups, adaptation and reports. Do not apply changes yet.

Expected behavior: provide a read-only preview and identify the tool version. Explain that apply performs a full backup and writes reports, rollback restores tool changes only, and a full restore creates a new directory. Do not invent protect-all, steam-upload or audit --no-report commands, and do not upload the game.

[简体中文](EXAMPLES.md) | [English](EXAMPLES.en.md)
