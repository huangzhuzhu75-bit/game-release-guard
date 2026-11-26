# Cocos Creator 3.x / 4.x 安全开发与加固

先按核心 Skill 选择行为。本文件只在 Creator 工程加载。核对日期：2026-11-27；分别核对了 **3.8 LTS / 4.0 LTS** Native 文档，其他版本查各自官方资料，不套用 2.x 菜单或 API。

## 识别与代码检查

- 读 package.json 的 Creator 信息、实际编辑器/构建版本、settings/profiles 和导出配置；包自身 version 不是可靠的 Creator 版本。区分 Native（Windows、Android、iOS 等）、Web 和小游戏，不能只看 TypeScript 判断平台。
- TypeScript 转 JS、压缩和 MD5 命名不是加密。检查项目/Bundle 脚本、启动引导文件、source maps、日志和原生插件；并非全部 JS 都应该消失。
- 3.8 的 `cc/env` 提供 `DEBUG` / `DEV` 等构建常量；核对对应版本及真实 debug 构建选项，再隔离测试菜单和刷物品入口。隐藏 UI 或降低日志级别不能移除调用能力。4.x 查当前 API/引擎声明，不照搬旧的 `cc` 全局访问。
- 不将服务端密钥、权限或经济逻辑放在 JS/JSC 中作为可信依据。原生插件也能分析，保留 ABI、SDK 初始化、运行依赖和私有符号。

## Native Encrypt JS

1. 已授权加固时先核验备份、已有修改、打包流程和密钥来源。通过当前版本的 Native 构建配置启用 **Encrypt JS**；使用既有获准的 JS Encryption Key，不自动更换、打印或提交。
2. 3.8/4.0 官方说明会生成 `.jsc`，原始脚本备份在 `script-backup`，正常不会进入发行包。实际路径随构建布局变化，必须检查真实产物和自定义复制脚本。
3. 不删除原工程 JS/TS 或私有脚本备份。若发行流程误包含 `script-backup`，修正已确认的打包/排除规则并保留原始文件；运行仍需要的 bootstrap JS 不能误删。
4. Zip compression 仅减小体积；`.jsc` 后缀不能单独证明正确加密。JS 加密不意味着模型、纹理、音频、配置或全部 Bundle 都已加密。
5. **不要把 Native Encrypt JS 套到 Web。** Web 脚本、资源请求和运行内存可被读取；聚焦秘密移出客户端、开发功能隔离、资源授权和可维护构建，不编造通用 Web 资源加密功能。

## 资源、热更新与验证

- 核对 `settings.json`、Bundle `config.json`、构建清单、远程根目录、缓存和动态加载路径。这些文件影响启动与加载，不能为隐藏信息删除或乱改标识。远程 Bundle 不自动私有，散列命名不等于访问授权。
- 检查热更新清单来源、HTTPS、版本/回退策略、已有可信签名及完整性链；下载内容和可一起替换的 MD5 清单不能证明来源。不擅自改写更新协议/加载器，不上传私有代码、资源或密钥。
- 在用户实际目标平台检查编译结果、JSC 和排除清单，再启动最终应用验证脚本、场景、资源、热更新、存档、SDK/插件及性能。Windows 测试不能替代 Android/iOS 设备验证，工具链与宿主要求按平台核实。
- 缺少 Creator 或目标环境时，备份后完成有依据的代码/发行清单修改，说明产物与运行待验证；不安装引擎或伪造 JSC。失败恢复原配置/脚本，保留原始 JS 和密钥。

## 官方参考

- [3.8：Native Build Options / Encrypt JS](https://docs.cocos.com/creator/3.8/manual/en/editor/publish/native-options.html)
- [4.0：Native Build Options / Encrypt JS](https://docs.cocos.com/creator/4.0/manual/en/editor/publish/native-options.html)
- [3.8：构建过程与清单](https://docs.cocos.com/creator/3.8/manual/en/editor/publish/build-guide.html)
- [3.8：Engine Modules / cc/env](https://docs.cocos.com/creator/3.8/manual/en/scripting/modules/engine.html)
- [3.8：命令行构建与配置导出](https://docs.cocos.com/creator/3.8/manual/en/editor/publish/publish-in-command-line.html)

Context7 索引未锁定版本，4.0 Native 页面已单独核对；不能因此声称 4.x 的其他 API 都已经验证。
