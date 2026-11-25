# Steam Release Guard 项目指令

开始任务时先完整读取 [统一 Skill / Markdown 操作说明](skills/steam-release-guard/SKILL.md)，再读取适用的 [Unity](workflows/unity-release.md)、[Unreal](workflows/unreal-release.md)、[安全检查](workflows/security-audit.md) 或 [回滚](workflows/rollback.md) 工作流。这是明确的读取指令，普通 Markdown 链接不代表原生 Skill 已自动加载。

先核实项目目录、引擎精确版本，运行 plan 或 audit，说明修改范围并保留原工程。写操作需要已授权的具体范围；不擅自改密钥、删未知文件、上传源码/资源或上传 Steam。REVIEW 和 NOT_VERIFIED 不得改成 PASS。

修改本工具时保留 Python 3.10+ 标准库架构、旧 CLI/GUI/报告及回滚兼容性。执行 `python -m unittest discover -s tests -v`，不删除或削弱旧测试。P0 验收前不进入 P1—P4。仓库 AI 适配只维护 Markdown，不构建 AI 管理系统，不修改全局 AI 配置。
