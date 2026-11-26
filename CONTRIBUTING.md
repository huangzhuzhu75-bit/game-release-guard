# Contributing / 参与贡献

## English

Start with the [README](README.en.md), [security boundaries](SECURITY.md) and the relevant workflow. This project is early development; real-engine evidence must remain separate from synthetic tests and API compilation.

- Open an Issue with a minimal **synthetic** reproduction, tool/engine version, command and expected/actual behavior. Do not upload your game, assets, logs containing secrets, symbols or backups. Follow SECURITY.md for vulnerabilities.
- Keep changes focused. Preserve the standard-library Python 3.10+ architecture, existing CLI/GUI, full backup/restore, rollback, tests and explicit advanced opt-in. Do not rewrite unrelated code or add an AI management system.
- Never manufacture PASS evidence, infer encryption from a filename/exit code, generate production keys or silently weaken recovery checks. Test destructive operations on disposable copies.
- Run the existing suite and add meaningful regression coverage when behavior changes. Engine-specific claims need the exact engine/tool version and actual build/runtime evidence; otherwise use NOT_VERIFIED.
- Keep README.md / README.en.md and INSTALL.md / INSTALL.en.md consistent. The canonical security knowledge remains in one SKILL.md. Preserve third-party attributions and license obligations.
- In a pull request, explain the problem, resulting behavior, test scope and unresolved limits. Include no private artifacts. Contributions are distributed under the repository's MIT license; only submit material you are authorized to share.

```shell
python -m unittest discover -s tests -v
python -m compileall -q steam_release_guard
```

## 简体中文

先阅读 [首页](README.md)、[安全边界](SECURITY.md) 和相关工作流。项目仍处于早期开发，合成测试/API 编译与真实引擎证据必须分开。

- Issue 使用最小**合成**复现，说明工具/引擎版本、命令、预期与实际结果；不上传游戏、资源、含凭据日志、符号或备份。漏洞按 SECURITY.md 处理。
- 修改保持聚焦，保留 Python 3.10+ 标准库架构、旧 CLI/GUI、完整备份恢复、回滚、全部测试和高级功能的显式启用；不重写无关代码，不增加 AI 管理系统。
- 不伪造 PASS，不从文件名/退出码推断加密，不生成生产密钥，不悄悄削弱恢复保护。破坏性操作只在可丢弃副本上测试。
- 运行上方测试；行为变化补充有意义的回归测试。引擎结论需要精确工具版本和真实构建/运行证据，否则标 NOT_VERIFIED。
- 中英文 README 和安装说明保持一致；核心安全知识只有一份 SKILL.md，保留第三方署名与许可义务。
- PR 说明问题、最终行为、验证范围及限制，不含私有产物。贡献按 MIT 分发，只提交有权分享的内容。
