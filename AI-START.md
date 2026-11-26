# 下载一次，让 AI 按引擎使用

下载 [完整 Skill ZIP](downloads/game-release-guard-skill.zip)，解压保留整个 `game-release-guard/` 目录。入口只有 [SKILL.md](skills/game-release-guard/SKILL.md)，它按项目识别结果选择一份 `engines/` 文档，无需 Python。只复制入口文件会缺少引擎知识。

[中文安装](skills/game-release-guard/INSTALL.md) · [English installation](skills/game-release-guard/INSTALL.en.md) · [中文示例](skills/game-release-guard/EXAMPLES.md) · [English examples](skills/game-release-guard/EXAMPLES.en.md)

## 三种日常用法

- **开发**：读取核心 Skill 和当前引擎文档，完成明确的功能任务，安全规则融入代码，不额外写报告。
- **检查**：只读工程，直接在对话给出文件位置、风险、已有保护和修复建议。
- **加固**：明确授权后，在范围内核验工程外备份、实际修改代码/配置、运行适用检查，在对话说明验证边界和恢复方法。

把安装说明中的通用提示词交给你使用的 AI。支持原生 Skill 时按该客户端当前项目级格式安装；否则明确读取 Markdown。保留已有指令，不覆盖同名文件，不改全局配置。如果助手无法读本地文件，可提供核心和对应引擎文档，以及非敏感项目信息；它不能声称已经检查不可访问的工程。

## 需要本地工具时

Unity / Unreal 才有本仓库的 CLI / GUI。读取 README、对应工作流和真实代码，核对 `--help`；先 plan/预览。Godot、Cocos Creator、GameMaker 不存在本地自动加密适配器。

`audit` 即使加 `--json` 也写 HTML/JSON 报告，没有 `--no-report`。`apply` 也生成报告；不应把默认只读检查或不需要报告的加固直接变成这些调用。工具修改前遵守 [备份与恢复](workflows/backup.md)，其余边界以 Skill 为准。

## 维护与验证

仓库级入口 [AGENTS.md](AGENTS.md)、[CLAUDE.md](CLAUDE.md)、[GEMINI.md](GEMINI.md) 都指向同一核心。通用 Markdown 方式不依赖某客户端的自动发现，也不承诺输入 URL 就能绕过网络、文件或安装权限。

[五引擎合成验证](docs/MULTI-ENGINE-SKILL-VALIDATION.md)记录本次行为证据；[旧版验证](docs/SKILL-VALIDATION-20261125.md)仅描述当时版本。这里不安装缺失 AI 客户端或注册后台服务。
