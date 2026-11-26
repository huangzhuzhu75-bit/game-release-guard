# Security and privacy boundaries

Game Release Guard is a local release review aid. It does not claim to prevent copying, reverse engineering, resource extraction or piracy, and it is not anti-cheat software.

- `plan`, `apply`, `audit`, `stage` and `rollback` make no network calls. Opening an HTML report uses the local browser and a self-contained page without scripts or remote assets.
- `Invoke-SteamDrm.ps1` is the explicit exception: it invokes the user's SteamCMD and uploads the input EXE to Valve after `-AcknowledgeExecutableUpload` is supplied. It does not include credentials or upload a depot.
- A generated engine build script invokes the locally installed engine. Engines, plugins and custom build hooks have their own behavior and may contact services. Inspect those separately.
- P3 `advanced unity-build` and `advanced unreal-verify` invoke explicitly selected local tools after preview/consent. They are not a sandbox for vendor code. No downloads, activation, key generation or upload are requested by SRG. Logs/mappings/evidence are private and remain outside the depot; process interruption can leave an incomplete copy and engine child processes. Verify that the engine has stopped before inspecting or retrying that copy.
- P3 read-only inspections print results without creating reports. Integrity checks require a separately trusted manifest hash and build ID; a checksum stored beside a replaceable client is not authentication. Acceptance checks verify evidence file hashes and supplied measurements, not the truth of a declared runtime test. Configuration, artifact and runtime evidence remain separate.
- Reports omit source snippets and key values, but file names can still be confidential. Keep reports and backups private. Backups may contain original crypto configuration; they are not encrypted at rest.
- The tool excludes its state from Git, and stops on backup corruption, path traversal, symlinks/junctions during inspection, conflicting later edits or occupied staging directories.
- Source inspection is heuristic. Do not interpret a match as proof of a vulnerability or an absence of matches as proof of safety. The tool does not parse Blueprint bytecode or binary plugins.
- Project files and transactions are intended to be used sequentially with the editor closed. Do not run simultaneous writers or edit configuration while a transaction is in progress.
- Always retain your own project version control and off-machine recovery plan. Local recovery journals do not replace a complete project backup.

If reporting a defect, provide the tool version, command, sanitized file layout and a minimal synthetic reproduction. Do not post game assets, Steam secrets, private symbols or encryption keys in issues.

## Reporting a vulnerability

This is an early-development project, not a supported stable security product. If the repository Security page offers **Report a vulnerability**, use that private channel. If it is unavailable, open an Issue asking for a private contact route without posting exploit details or confidential data. Do not attach a real game, backup, credential or private build. A maintainer response time is not guaranteed.

If a real credential has already been disclosed, its owner should revoke/rotate it and review accessible history, branches, logs and artifacts. Removing only the current file does not remove past exposure. This project will not rotate a user's keys automatically.

## 中文安全报告说明

项目仍处于早期开发，不是有稳定支持承诺的安全产品。仓库 Security 页面如提供 **Report a vulnerability**，请使用其私有渠道；未提供时，可提交不含漏洞利用细节的 Issue 请求私下联系。不要附真实游戏、备份、凭据或私有构建，不承诺固定响应时限。

真实凭据泄露后，由责任人撤销/轮换，并检查可访问历史、分支、日志和附件；只删除当前文件不能消除历史泄露。本工具不会替用户自动轮换密钥。详细限制见上文及中英文 README。
