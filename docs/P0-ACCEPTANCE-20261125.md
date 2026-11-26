# P0 本机验收记录 — 2026-11-25

范围：`0.2.0.dev0` 的稳定性与 Markdown 适配，按完整测试 → 工程副本事务 → 失败暂存/清理 → GUI/报告的顺序执行。技术检查已完成，提交用户人工验收；本记录不代表已合并、游戏发行批准或 Unity 深度保护验收。

## 环境与完整测试

- Windows 10 Home China 22H2，build 19045.6466；CPython 3.12.14；Tk 8.6。
- 仓库命令：`python -m unittest discover -s tests -v`。
- 初次完整运行：56 项，55 通过，1 跳过。GUI 显示修复后再次完整运行：相同结果。
- 唯一跳过项：当前 Windows 用户缺少创建符号链接的权限。旧测试和断言均保留；没有增加运行依赖。

## 真实工程副本事务

使用本地已有的 Unity **6000.6.6f1** 工程创建独立副本，复制 `Assets`、`Packages`、`ProjectSettings` 和根目录文件，共 **167 个文件**。未复制可重建缓存与已有构建；原工程保持只读。

在工具仓库中执行下列实际 CLI。`$copy` 是验收副本，`$reports` 是独立本地报告目录：

```powershell
python -m steam_release_guard plan $copy --json
python -m steam_release_guard apply $copy --yes --report-dir "$reports/apply" --json
python -m steam_release_guard audit $copy --report-dir "$reports/audit" --json
python -m steam_release_guard rollback $copy --yes --json
```

| 检查 | 观察结果 |
| --- | --- |
| plan | 退出 0，PREVIEW；副本内容未改变 |
| apply | 退出 0；仅修改预览中的三个文件，备份与事务记录保留 |
| audit | 退出 0，REQUIRES_MANUAL_REVIEW；没有将待验证项提升为 PASS |
| rollback | 退出 0，COMPLETE；日志为 rolled_back |
| 回滚后核对 | 167 个工程文件的相对路径及 SHA256 与适配前完全一致；原工程也完全一致 |

三个适配文件为 `.gitignore`、`Assets/SteamReleaseGuard/Editor/SteamReleaseGuardBuild.cs` 和 `Assets/SteamReleaseGuard/Editor/SteamReleaseGuard.Editor.asmdef`。回滚保留 `.steam-release-guard` 内的报告与恢复记录；“完全一致”指工程文件，不包含新增的私有审计记录。

本次验证安装与撤销已有构建适配器，没有启动 Unity、改变 PlayerSettings 或运行新构建。

## 失败暂存与安全清理

使用同一本地工程已有的 Windows 构建作为只读输入：**305 个文件，172,880,027 字节**。发布副本和私有符号目录均位于新的独立目录。

1. 先执行 `stage --dry-run --json`。
2. 在本地验收脚本中注入 ENOSPC：首个 EXE 已完成复制，第二个文件写入 4,096 字节部分副本后报磁盘写满。没有实际填满磁盘，也没有修改产品中的复制函数。
3. stage 返回退出码 1，留下 INCOMPLETE 标记与恢复日志。对此目录 audit 返回退出码 2、BLOCKED，具体命中 `INCOMPLETE_STAGE` FAIL；目录中已有 EXE，阻断不只依赖缺少可执行文件。
4. 添加验收专用未知文件后，`stage-cleanup --dry-run` 返回退出码 1，并保留所有文件。移除验收脚本自己创建的该文件后，重新预览并执行 `stage-cleanup --yes`。
5. 清理结果为 CLEANED，发布副本目录为空，私有恢复日志仍在。原始 305 个构建文件的 SHA256 全部不变。

这是可重复故障注入与恢复验证，不是硬件断电或真实磁盘耗尽试验。

## 原生 GUI 与报告

在真实 Windows 用户桌面启动 Tk GUI，使用第二份独立工程副本，完成点击和视觉检查：

- 输入工程目录，运行检查，按钮恢复可用。
- 适配确认框显示准确引擎版本、三个待修改路径和不可取消写入提示。选择“否”后，167 个文件的 SHA256 不变。
- 再次预览并选择“是”，核对实际仅变更上述三个文件。
- 点击“回滚最近一次适配”，核对确认范围并执行；界面显示已回滚，副本恢复到原来的 167 个工程文件。
- 输入不存在的发布包路径，界面显示明确错误并恢复按钮。此时点击“打开检查报告”提示先执行检查，没有误开上一份报告。
- 清除错误输入后再次检查，点击打开报告；Edge 成功显示新的本地 HTML。标题、引擎版本、REQUIRES_MANUAL_REVIEW 和七项 REVIEW 均正常，未出现错误页。JSON 与 HTML 文件均保存，GUI stderr 为空。

实机发现并修复一处显示问题：最后的保存报告事件会将进度重置为空。现在新任务开始时清零，成功完成时设为 100%；失败分支保留错误状态，不标记成功。修复共两行，完整测试及上述 GUI 流程均已复验。

原生点击覆盖本节列出的路径；GUI 的构建脚本保存对话框、符号分离文件选择器以及工作中点击取消未在此次桌面流程中逐项点击验收。其底层命令/事务及现有 GUI 自动化测试结果见测试记录，不将自动化覆盖混称为原生点击覆盖。

## 证据与验收边界

本机 D 盘留存完整测试输出、逐命令 JSON/退出码、源文件私有哈希清单、回滚日志、失败暂存日志、GUI 前后核对结果、HTML/JSON 报告与 SHA256 清单。仓库仅提交本摘要和工具修复，不上传游戏源码、资源、原构建或私有清单。

最新 GUI 报告 HTML SHA256：`0e8f951b6c38da9d0d940635c715ccb06b540b5d73b998a1d430a540efdf656f`。

| 项目 | 状态 |
| --- | --- |
| 本机完整测试、工程副本往返、失败暂存/安全清理、本节 GUI/报告路径 | 已完成技术检查 |
| P0 人工验收与合并 | 等待用户验收；候选 PR 未合并 |
| Unity/Unreal 真实新构建、插件、存档、联机和 Steam 测试分支 | NOT_VERIFIED，不作为此次 P0 检查通过的推论 |
| Unity 深度保护 / P1—P4 | 未启动 |
| AI 客户端原生 Skill 发现 | 沿用 Markdown 兼容方案；未验证项继续保留 NOT_VERIFIED |

依原企划“P0 完成后……等待人工验收”和本次“验收后再合并 P0”，在用户确认本候选前保持待验收状态。P0 合并也不自动授权进入 Unity 深度保护。
