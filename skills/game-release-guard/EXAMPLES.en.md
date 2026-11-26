[简体中文](EXAMPLES.md) | [English](EXAMPLES.en.md)

# Game Release Guard: five-engine examples

Install the complete Skill directory, then replace paths, versions and tasks with your own. These are reusable requests, not evidence that your project has passed review. The assistant should read actual files and version-matched official documentation. Development authorizes the scoped feature work; review stays read-only; explicit hardening authorizes scoped changes. Findings belong in the conversation, without separate reports.

## New projects: start with secure development

> Read <Skill directory>/SKILL.md. I am developing a <Unity / Unreal / Godot / Cocos Creator / GameMaker> game in <project directory>; version evidence is in the project. Identify the actual engine and version and load only its guide. Implement <specific feature>, validate untrusted input, isolate development tools, and preserve the existing structure and uncommitted work. Do not add privileged client credentials, an extra backend or unnecessary encryption. Do not create a security report.

For example, a player-name validator should check type, length and allowed characters and use the existing error UI. It is not payment entitlement or online authentication and does not require a new server.

## Review an existing project

| Engine | Request to copy |
| --- | --- |
| Unity | Read-only review of D:/Games/MyUnity. It has IL2CPP settings, Addressables and development shortcuts, but no packaged build. Identify locations, existing protection, risks and fixes. Do not edit files. |
| Unreal | Read-only review of D:/Games/MyUE. Shipping, Pak and IoStore settings exist, but no container verification records. Separate configuration evidence from missing proof. Do not change keys or files. |
| Godot | Read-only review of project.godot and export_presets.cfg in D:/Games/MyGodot: script export, PCK prerequisites, templates and resource-pack loading. Do not mistake config_version for the engine version or edit files. |
| Cocos Creator | Read-only review of D:/Games/MyCocos. Identify Creator version and Native/Web target first. Check Encrypt JS, JSC evidence, script-backup, remote Bundles and debug entry points. Do not edit files. |
| GameMaker | Read-only review of D:/Games/MyGM. Distinguish IDE from Runtime, VM/YYC/GMRT, target platform and Included Files. Missing build records mean unknown results. Do not edit files. |

Explain file/location, issue, impact, fix, existing protections and evidence level. Distinguish compilation, compression and encryption; an empty search does not prove safety. Report credential type and location, never the value.

## Explicit hardening: implement the changes

Choose only the item matching the project. Each request starts with: read the core and matching engine guide, preserve existing edits, verify an external backup, modify only the authorized scope, and create no independent report.

- **Unity**: Isolate developer cheat shortcuts in D:/Games/MyUnity while preserving Editor/Development usage, serialized fields and save contracts; review release settings. Build only with an available, authorized engine. Do not install an obfuscator or expand its type list.
- **Unreal**: Isolate development console commands from release builds in D:/Games/MyUE. Preserve container strategy and Crypto Keys. Do not switch containers for protection or reuse Pak evidence for IoStore.
- **Godot**: Isolate release debug entry points in D:/Games/MyGodot and assess its PCK preset. Without custom templates compiled with the matching key, leave encryption pending and continue applicable code edits; do not leave a broken export configuration.
- **Cocos Creator**: Isolate debug features for the actual version in D:/Games/MyCocos and fix a confirmed release copy list. Assess Encrypt JS only for an explicit Native target with an existing key. Do not delete source, bootstrap JS or unknown assets, or apply Native protection to Web.
- **GameMaker**: Isolate developer cheats in D:/Games/MyGM while preserving saves and Included Files. Assess YYC after checking target, license and components. Do not install components automatically or call YYC resource encryption.

Describe changed files, backup/recovery, and actual checks in the conversation. Static hardening is possible without an engine, but it does not verify builds, startup, loading, saves, multiplayer or updates.

## Use the local Unity / Unreal toolkit

> Game Release Guard is in D:/Tools/game-release-guard. Read its README, CLI and backup implementation to confirm real commands. For now, run only plan on D:/Games/MyGame-Copy and explain backup/report side effects. Do not apply.

Keep `python -m steam_release_guard`. `apply` writes settings and reports; `rollback` reverts toolkit changes only; full restore creates a new directory. Do not invent protect-all, steam-upload, audit --no-report, or CLI adapters for the other three engines.

[简体中文](EXAMPLES.md) | [English](EXAMPLES.en.md)
