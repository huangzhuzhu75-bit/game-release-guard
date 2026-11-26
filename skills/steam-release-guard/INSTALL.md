[简体中文](INSTALL.md) | [English](INSTALL.en.md)

# 通用 AI 使用说明

一份 [SKILL.md](SKILL.md)，一套提示词。把仓库地址和下面的提示词交给你正在使用的 AI 即可。不需要先安装 Python 或 Steam Release Guard 程序。

## 交给 AI 安装或读取

```text
请读取 https://github.com/huangzhuzhu75-bit/steam-release-guard 的 README.md 和 skills/steam-release-guard/SKILL.md，为当前游戏项目安装并使用这份 Skill。
如果你支持原生 Skill，按当前客户端的项目级方式安装；否则直接读取 Markdown 并遵循。保留 LICENSE 和已有指令，不覆盖同名文件，不修改全局配置，不安装额外软件。
完成后简短说明实际读取或保存的位置，等待我的开发或检查任务。不要因为安装 Skill 就修改游戏、运行构建、生成报告或上传工程。
```

有原生 Skill 功能的助手按自身方式安装；其他助手直接阅读 Markdown。安装只放入操作说明，不会自动给游戏启用混淆、加密或其他保护。

## 手动下载

1. 下载 [独立 Skill ZIP](https://github.com/huangzhuzhu75-bit/steam-release-guard/raw/refs/heads/main/downloads/steam-release-guard-skill.zip)，解压到自己的文档目录。
2. 把 `steam-release-guard/SKILL.md` 的路径交给 AI，或在对话里提供文件内容。
3. 选择下面的开发或检查任务。分发时保留 [LICENSE](LICENSE)。

也可以单独保存 [Raw SKILL.md](https://raw.githubusercontent.com/huangzhuzhu75-bit/steam-release-guard/main/skills/steam-release-guard/SKILL.md) 和 [Raw LICENSE](https://raw.githubusercontent.com/huangzhuzhu75-bit/steam-release-guard/main/skills/steam-release-guard/LICENSE)。保存 Markdown 原文，不要保存 GitHub 网页。ZIP 只包含 Skill、许可和这套双语说明，不含引擎、程序或游戏内容。

不能联网的 AI 可以读本地文件；没有本地文件访问能力的 AI 可以读你提供的 Skill 内容。不要为了配置 Skill 上传游戏源码、资源或密钥。核心正文为中文，可要求 AI 用其他语言回复。

## 通用任务提示词

**新游戏或已授权的功能开发：**

```text
使用 Steam Release Guard Skill。项目是【Unity / Unreal，工程路径】，这次开发【具体功能】。先核对引擎版本和项目约定，在这项功能范围内遵守安全开发规范，不额外生成安全报告。
```

**检查已有游戏：**

```text
使用 Steam Release Guard Skill，只读检查【工程路径】。先核对引擎版本；在对话中指出具体文件或位置、风险原因和修复建议，说明已有保护及缺少的证据。不修改文件、不运行构建、不生成报告、不上传工程。
```

[Unity、Unreal 与工具操作示例](EXAMPLES.md)

## 更新与移除

更新前保留旧版，比较差异；同名文件存在时不要直接覆盖。让 AI 简短说明它实际读取的版本或路径即可。需要长期生效时，只在当前游戏项目的已有指令中追加 Skill 引用，保留原有内容。

移除时只删除本次放入的 Skill 和自己添加的引用，不动游戏代码、备份或其他指令。仅安装或移除 Skill 不会应用或回滚游戏保护。

独立 Skill 不包含 CLI。只有需要备份、发行适配等工具操作时，才下载完整仓库，先读对应 README、工作流和实际代码，再调用存在的命令。

[简体中文](INSTALL.md) | [English](INSTALL.en.md)
