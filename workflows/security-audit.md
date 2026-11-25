# 安全检查与发布包检查

先阅读 [统一操作规则](../skills/steam-release-guard/SKILL.md)，核实项目和引擎版本。在工具仓库根目录执行，替换占位目录。

## 工程检查

```powershell
python -m steam_release_guard plan 'D:/Games/MyGame' --json
python -m steam_release_guard audit 'D:/Games/MyGame' --report-dir 'D:/PrivateReports/MyGame-project-v1' --json
```

plan 只预览；audit 保存本地 HTML/JSON。报告目录必须是新的空目录或工具已有专用目录。报告列出路径/行号/规则，不输出源码片段或密钥值。源码候选扫描不覆盖所有 Blueprint、Prefab、二进制或服务端权限；没有命中不能证明不存在问题。

## 原始构建与符号分离

原始构建必须来自成功的实际引擎打包；不能提供工程根目录代替发布包。先检查，再预览复制范围：

```powershell
python -m steam_release_guard audit 'D:/Games/MyGame' --build 'D:/Builds/MyGame-v1' --report-dir 'D:/PrivateReports/MyGame-build-v1' --json
python -m steam_release_guard stage 'D:/Builds/MyGame-v1' --project 'D:/Games/MyGame' --release 'D:/Release/MyGame-v1' --symbols 'D:/PrivateSymbols/MyGame-v1' --dry-run --json
```

发布目录与私有符号目录必须新建/为空，且与原构建互不嵌套。stage 只复制并分离已知符号，不自动删除其他候选风险文件。用户已授权该复制范围后：

```powershell
python -m steam_release_guard stage 'D:/Builds/MyGame-v1' --project 'D:/Games/MyGame' --release 'D:/Release/MyGame-v1' --symbols 'D:/PrivateSymbols/MyGame-v1' --yes --progress --json
python -m steam_release_guard audit 'D:/Games/MyGame' --build 'D:/Release/MyGame-v1' --report-dir 'D:/PrivateReports/MyGame-release-v1' --json
```

复制前后与最终库存会验证 SHA256。私有符号目录保存事务日志与清单；发布目录 `.srg-stage.json` 标记 COMPLETE 或 INCOMPLETE，不包含密钥或私有绝对路径。COMPLETE 只表示复制事务完成，不能作为上线批准。INCOMPLETE 或损坏标记会阻断 audit；用 [安全清理](rollback.md) 处理，不能删除标记伪装完成。

## 人工检查结果

- 代码：IL2CPP/原生指标与 Managed DLL 分开记录；不声称原生代码无法反编译。
- 调试入口：运行最终 EXE，检查菜单、控制台、跳关、开发快捷键；保留符号供私有崩溃排查。
- 资源：分别审查散装音频/模型/贴图、Pak、IoStore、Bundle；打包/压缩不代表加密。资源提取与加载/补丁测试需要真实工具和产物证据。
- 私有文件：检查源码、备份、DefaultCrypto.ini、steam_appid.txt、凭据候选，明确归档后再由用户决定处理；不因文件名相似自动删除。
- 玩家体验：启动、存档、插件、联机、离线、Steam 启动和更新均需真实结果。测试分支安装/上传必须单独授权。

每项记录状态、证据位置、版本与原因：PASS 有限于已验证事实；WARN 是候选风险；FAIL 是阻断；REVIEW 需人工判断；NOT_VERIFIED 缺少证据；NOT_APPLICABLE 需注明不适用理由。P0 自动报告沿用 pass/warn/fail/review 小写格式，其余状态可在人工验收表记录。禁止把待验证改写为 PASS。

退出码 2 代表发现阻断，1 代表操作失败；0 仍可能存在 REVIEW。最终报告为 BLOCKED 或 REQUIRES_MANUAL_REVIEW。人类审批前不得声称 RELEASE_APPROVED。
