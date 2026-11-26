[简体中文](INSTALL.md) | [English](INSTALL.en.md)

# Game Release Guard：通用安装与使用

下载一次，适用于 Unity、Unreal、Godot、Cocos Creator 和 GameMaker。一个核心 Skill 根据项目选择引擎知识，不需要 Python 或本地工具。

## 交给 AI

```text
请读取 https://github.com/huangzhuzhu75-bit/game-release-guard 的 README.md 和 skills/game-release-guard/SKILL.md。
为当前游戏项目安装并使用整个 game-release-guard Skill 目录，包括 engines/ 和 LICENSE；支持原生 Skill 时使用项目级安装，否则按 Markdown 阅读。
先识别引擎和版本，只加载对应引擎文档。保留已有指令，不覆盖同名文件，不改全局配置、不安装额外软件。
安装后说明实际路径，等待任务：我说“检查”就只读；明确要求“加固”时，在范围内备份后实际修改和验证。不擅自上传工程或生成独立报告。
```

## 手动下载

下载 [独立 Skill ZIP](https://github.com/huangzhuzhu75-bit/game-release-guard/raw/refs/heads/main/downloads/game-release-guard-skill.zip)，解压并保留整个 `game-release-guard/` 目录：核心 [SKILL.md](SKILL.md)、`engines/` 五份知识、双语说明/示例及 [LICENSE](LICENSE)。不要只复制 SKILL.md 而遗漏引擎文件。

让 AI 读取该目录下的 SKILL.md；它先识别项目，再加载对应引擎文件。支持原生 Skill 的客户端使用其当前版本的项目级安装方式，其他工具直接读 Markdown。不能访问文件的助手可阅读你提供的核心及对应引擎文档内容，不要为安装而上传游戏、资源或密钥。

## 三种用法

- **开发**：“使用 Game Release Guard，先检查【工程路径】的引擎版本，按安全规范开发【功能】。”
- **检查**：“只读检查【工程路径】，在对话中指出文件位置、风险和建议；不改文件、不运行构建、不生成报告。”
- **加固**：“帮我加固【工程路径】的【明确范围】。核对已有修改和保护，建立可恢复备份后实施适用修改，验证并在对话中说明结果；不换生产密钥、不上传、不生成报告。”

[五引擎示例](EXAMPLES.md)。核心知识正文为中文，可以要求用其他语言回复。安装 Skill 本身不会加密游戏；加固需要 AI 能访问工程且用户已授权具体范围。

## 更新、迁移与移除

旧名称为 steam-release-guard。先备份旧 Skill 和用户改动，比较差异，再迁移到 `game-release-guard`；同一客户端不要同时启用两份同名/旧名知识副本。保留已有项目指令，只更新你添加的 Skill 引用，不覆盖全局配置。

更新时复制完整目录，不能只更新核心文件。移除时仅移除本次安装的 Skill 与引用，不删除游戏代码或备份。安装/卸载 Skill 不会应用或回滚游戏保护。

本地工具仅适配 Unity / Unreal，仍使用 `python -m steam_release_guard`。只有需要该工具时才获取完整仓库并先读真实 CLI/工作流；其他三个引擎没有本地自动加密适配器。

[简体中文](INSTALL.md) | [English](INSTALL.en.md)
