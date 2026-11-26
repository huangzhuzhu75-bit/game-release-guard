# 完整工程文件备份与恢复

先读 [统一操作说明](../skills/steam-release-guard/SKILL.md)，核实工程目录和引擎版本，再运行 plan 或 audit。关闭引擎、版本控制写任务和同步工具。命令在工具仓库根目录执行，占位路径需替换为实际路径。

## 首次试用

先完整备份，再恢复出一个新工程副本，对这个副本进行适配。备份/恢复只在本地执行，原工程保留。

```powershell
python -m steam_release_guard plan 'D:/Games/MyGame' --json
python -m steam_release_guard backup 'D:/Games/MyGame' --backup-dir 'D:/PrivateBackups/MyGame' --dry-run --json
```

解释文件数、总字节数、源目录和备份存放位置。备份范围是工程目录内所有普通文件和空目录，包括隐藏文件、`.git`、`.meta`、缓存和已有构建；不根据 `.gitignore` 省略文件。用户已授权复制范围后：

```powershell
python -m steam_release_guard backup 'D:/Games/MyGame' --backup-dir 'D:/PrivateBackups/MyGame' --yes --progress --json
```

从 JSON 的 `result.backup_path` 取得真正的时间目录，将下面占位的“时间编号”替换成该路径。检查 `status=COMPLETE` 后再核验；不能自行把 INCOMPLETE 改成 COMPLETE。

```powershell
python -m steam_release_guard backup-verify 'D:/PrivateBackups/MyGame/时间编号' --json
python -m steam_release_guard backup-restore 'D:/PrivateBackups/MyGame/时间编号' --output 'D:/Games/MyGame-Trial' --dry-run --json
```

解释恢复目标，确认是工程和备份之外的全新目录。用户已授权后：

```powershell
python -m steam_release_guard backup-restore 'D:/PrivateBackups/MyGame/时间编号' --output 'D:/Games/MyGame-Trial' --yes --progress --json
python -m steam_release_guard plan 'D:/Games/MyGame-Trial' --json
python -m steam_release_guard apply 'D:/Games/MyGame-Trial' --backup-dir 'D:/PrivateBackups/MyGame-Trial' --dry-run --json
python -m steam_release_guard apply 'D:/Games/MyGame-Trial' --backup-dir 'D:/PrivateBackups/MyGame-Trial' --yes --json
```

每次实际有修改的 apply 都创建新的完整备份并核验，再进入原有逐文件事务。没有跳过开关；无配置变更时不重复备份。后续适配失败仍用 [rollback](rollback.md) 撤销这次修改，完整备份继续保留。

GUI 对应入口：“备份位置…”选择存放父目录，“完整备份”创建时间目录，“恢复完整备份…”选择时间目录和恢复父目录；程序自动创建新的 `RestoredProject-<时间>`。一键适配的确认框同时显示备份位置，成功后在界面与日志显示实际备份路径。

## 故障与边界

- 备份目录必须在工程外且互不嵌套；默认同级 `<工程名>.srg-backups/`。可选其他磁盘，不默认上传云端，也不会自动删除历史备份。
- 文件占用、写满、取消、进程强退、文件在复制中变化、校验不符都会阻止适配。失败副本保留为 INCOMPLETE，不能恢复；排除原因后创建新的备份。
- 完整恢复先核验全部备份，再复制到新目录，最后核对全部文件和空目录。拒绝已存在的目标，包括空目录；不提供强制覆盖。失败时保留部分输出，相邻 `<新工程目录>.srg-restore.json` 为 INCOMPLETE。不要把部分输出作为恢复完成的工程；改用新的目录重试。
- 保留恢复目录旁的 `.srg-restore.json` 和对应完整备份；工具据此识别恢复副本中原有的回滚记录。INCOMPLETE 或损坏的恢复凭据会阻断适配和审计，不能删除凭据来绕过。完整恢复可离线读取备份，不要求原工程仍然存在。
- 完整工程文件备份保留文件内容和目录结构，不承诺文件系统镜像：ACL、所有者、NTFS 备用流等元数据不保证保留，链接/连接点与特殊文件拒绝。工程根目录外的依赖和玩家存档需另外保留。大缓存也会复制，请预留空间。
- 本机锁只协调工具自身，不阻止编辑器或同步软件写入；源/副本双重校验能检测已观察到的变化，不是跨文件系统的瞬时快照。SHA256 用于检测意外损坏，不是加密或认证签名。
- 备份包含源码、资源和可能的密钥，保持私有。CLI 的 COMPLETE/VERIFIED 只说明文件复制/校验完成；引擎实际打开、构建、插件、存档和联机仍待验收。

交付时给出完整备份路径、文件数/大小、校验结果、恢复新目录、恢复记录和未验证项，不能只说“已备份”。
