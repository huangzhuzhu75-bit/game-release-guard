# GameMaker / GML 安全开发与加固

先按核心 Skill 选择行为。本文件只在 GameMaker 工程加载。官方 monthly 手册核对：2026-11-27；它是滚动文档，不是某个 Runtime 的兼容认证。

## 区分 IDE、Runtime 和目标

- 读取 `.yyp`、`.yy`、GML、options、目标配置和构建记录。MetaData.IDEVersion 不等于 Runtime 版本；记录实际 Runtime 版本/通道、平台和 Output。
- 当前产品名 GameMaker 不代表项目已经使用新 **GMRT**。传统 GMS2 Runtime、旧 GameMaker Studio 2 与 GMRT 分开判断；旧菜单、序列化字段和编译器配置不能直接套入新运行时。
- 当前 Runtime/目标确实提供 YYC 时，优先评估发行价值；GMRT 或其他目标使用不同流程时，依据相应官方资料处理，不虚构 YYC 开关或强制转换 Runtime。

## VM、YYC 与调试

- VM 使用平台 runner 执行游戏代码；YYC（YoYo Compiler）将 GML 经 C++ 编译为目标原生代码，增加直接分析成本。**YYC 不是加密**，不自动保护字符串、资源、接口和客户端秘密；优化/剥离也不是加密。
- 核对用户许可对应的目标、Runtime YYC 模块和 SDK/C++ 工具链；缺失就说明，不代购或下载。按实际项目评估性能和编译时间，不承诺固定提升倍数。
- 在支持的目标选择 YYC Output 和发行配置，通过 Create Executable 生成新产物；核对 Runtime、构建日志与编译证据。`code_is_compiled()` 返回 true 不足以证明 YYC，官方说明 JS 目标也可返回 true。
- 检查作弊按键、调试菜单、命令入口、敏感日志和发行配置。`debug_mode` 反映当前是否在调试运行，不证明开发代码已物理移除。Debug 操作可能回落到 VM，不能拿 Debug Run 充当 YYC 验证。
- GML、扩展和 Included Files 不保存服务端凭据。客户端余额、物品、奖励及 INI/JSON 存档仍可修改；重要联网结果由已有可信端校验，不擅自改后端或强制单机联网。

## 资源与授权加固

1. 核验工程外备份与用户已有修改，检查 GML/扩展、Included Files、动态资源、纹理/音频组、配置和存档引用。
2. 实施已核实的调试隔离、输入校验或发行文件过滤。Included Files 会随游戏分发，逐项确认平台导出范围；调整打包规则时保留原文件和运行依赖，不删除未知资源包、`.yy` 或存档。
3. 普通压缩、打包、改扩展名都不保密。没有经当前 Runtime/目标核验的官方或成熟第三方加密方案时，明确资源保护限制，不发明加密器或修改运行时加载器。
4. 检查语法、配置和相关测试；有条件时对比 VM/YYC 的启动、动态资源、扩展、旧存档、更新、联网和性能，注意求值顺序/未定义行为等兼容问题，不以优化名义改变游戏规则。
5. 缺少 IDE/Runtime/许可证时完成可核实的静态修改，说明 YYC 产物和运行无法验证，不声称已经生成原生发行包。回退使用备份和旧构建，保留玩家数据。

## 官方参考

- [Compiling：VM、YYC、JS 与 Runtime](https://manual.gamemaker.io/monthly/en/Introduction/Compiling.htm)
- [YoYo Compiler：平台 SDK 与 YYC 模块](https://manual.gamemaker.io/monthly/en/Settings/YoYo_Compiler.htm)
- [debug_mode](https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Debugging/debug_mode.htm)
- [code_is_compiled](https://manual.gamemaker.io/monthly/en/GameMaker_Language/GML_Reference/Debugging/code_is_compiled.htm)
- [Included Files](https://manual.gamemaker.io/monthly/en/Settings/Included_Files.htm)

Context7 给出官方手册 develop 分支，已与 monthly 页面核对。旧版/LTS/GMRT 项目仍需对应的本地帮助、发布记录及实际构建设置。
