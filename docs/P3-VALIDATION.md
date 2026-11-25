# P3 验证记录

基线 8ed5ebc，独立分支 `p3/advanced-protection`。P0 不合并，不改用户真实游戏。

## 阶段 1：混淆适配

- Windows 10 / Python 3.12.14：83 项，82 通过、1 个旧符号链接测试跳过。新增 9 项覆盖 opt-in、排除规则、错误配置、缺工具、完整备份/回滚、写入确认、真实子进程日志脱敏；这些是合成夹具，不能证明游戏保护效果。
- 用本机 Unity 6000.6.6f1 的 Roslyn/真实引用程序集编译 Obfuz.Runtime、Obfuz.Editor、P0 builder 和新增 bridge，成功。外部源码固定 b83c53d4，MIT，仅下载到隔离 D 盘作编译检查；没有安装进用户游戏。
- 供应商源码产生过时 UnsafeUtility API 和未使用字段警告；本次未修改第三方源码。编译脚本保留用于复现。
- 实际 Obfuz 构建、IL2CPP 游戏启动、存档/联机/性能：**NOT_VERIFIED**。字符串/控制流额外初始化尚未实现，拒绝启用。未加密 metadata。
