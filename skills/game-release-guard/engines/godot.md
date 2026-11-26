# Godot 4.x 安全开发与加固

先按核心 Skill 选择开发、只读检查或授权加固。本文件只在 Godot 工程加载。核对日期：2026-11-27；以下 **4.5 文档**是明确基线，不表示每个 4.x 小版本的参数相同。

## 识别与代码边界

- 读 `project.godot`、`export_presets.cfg`、实际 Editor 和导出模板版本/平台/架构；`config_version=5` 不是 Godot 5，`config/features` 不保证给出精确补丁号。另查 `.csproj`、`.gdextension`、原生库和构建记录，区分 GDScript、C#、GDExtension。
- 4.5 的 GDScript 导出模式包括 Text、Binary tokens、Compressed binary tokens；二进制 token 和压缩都不是原生机器码或加密。选项/数值以目标版本为准，不照搬旧版脚本导出选项。
- C# 程序集与 GDExtension 原生代码仍可分析，动态库/符号可能在 PCK 外。不能把秘密移进 C# / C++ 就视为安全，也不能删除必需的库。
- 检查运行时调试菜单、远程调试参数、Editor 插件和 Autoload。按版本使用 `OS.is_debug_build()` 等条件并核对 Release 模板；运行条件不等于相关代码从产物物理移除。多人敏感操作仍需服务端验证。

## PCK AES-256 前提与实施

1. 已授权加固时，先核对 preset、已有保护与密钥来源、资源加载和过滤规则，保留原配置并核验工程外备份。
2. **必须使用相同密钥自行编译匹配版本的 Export Templates**，在 preset 选择对应平台/架构的自定义模板。官方预编译模板不满足此流程；没有匹配模板时，不留下会破坏运行的加密配置，也不宣布加密成功。
3. 模板编译使用 `SCRIPT_AES256_ENCRYPTION_KEY`，与导出时的 AES-256 密钥一致。局部检查编码、长度和匹配关系但不显示值；经受控私有环境传入，不提交 Git、不写日志或聊天。不要自动生成/轮换生产密钥，不修改 Godot 引擎核心。模板编译只在已授权并具备工具链的环境进行。
4. 配置要加密的 include / exclude 过滤器，区分 PCK 文件内容与目录加密。4.5 官方说明 include 为空时不会加密任何文件；散装文件也不自动受保护。按模型、贴图、音频、脚本、场景的加载方式决定范围。
5. 密钥进入客户端模板后仍可被分析或通过运行时解密路径取得。PCK 加密不能代替来源签名、反篡改或服务端校验。

## 产物、补丁与回退

- 核对模板来源/构建证据、导出记录和实际 PCK，不凭开关、后缀或退出码下结论。验证最终游戏启动、首场景/切换、纹理/音频、C# / 扩展库、存档和目标平台；没执行就说明运行未验证。模板缺失时继续调试入口等适用静态加固，保留加密待办。
- PCK/ZIP 可以携带脚本与场景。`load_resource_pack` 成功不代表来源可信；同路径资源可覆盖已加载内容，加载顺序影响补丁。核对 `replace_files`、命名空间和既有 DLC/模组契约，不直接禁掉覆盖而破坏正常更新。
- 加载外来包前检查可信下载渠道、版本绑定与现有签名/来源验证。可一并替换的 hash 清单不是发布者认证；不要声称 Godot 自动验证所有 PCK 的签名。不发明加密器或擅自重写加载器，不删除用户模组功能。
- 比较包顺序、补丁体积、旧版升级、密钥延续、资源加载和耗时。回退时恢复原 preset 与匹配模板到新副本，保留旧构建和符号。

## 官方参考

- [4.5：PCK encryption key 与自定义模板](https://docs.godotengine.org/en/4.5/engine_details/development/compiling/compiling_with_script_encryption_key.html)
- [4.5：EditorExportPreset（脚本模式、加密过滤）](https://docs.godotengine.org/en/4.5/classes/class_editorexportpreset.html)
- [4.5：资源包、补丁与模组](https://docs.godotengine.org/en/4.5/tutorials/export/exporting_pcks.html)
- [4.5：OS](https://docs.godotengine.org/en/4.5/classes/class_os.html) · [导出工程](https://docs.godotengine.org/en/4.5/tutorials/export/exporting_projects.html)

导出总览页有可能过时的提示，具体参数交叉核对目标版本 API/编辑器。Context7 返回未锁定版本的索引，不能代替版本页；其他 4.x 版本通过官方文档选择器核对。
