# 使用示例

先按 [INSTALL.md](INSTALL.md) 安装或指定 [SKILL.md](SKILL.md) 的真实路径。下面是可直接改路径使用的提示词；不是宣称已在你的游戏上执行。检查默认只在对话中回复，后续修改需要对应授权。

## 新 Unity 项目

> 使用 steam-release-guard。项目在 D:/Games/MyNewUnityGame，是刚初始化的 Unity 项目，面向 Windows/Steam 的离线单机。请先读取版本和已有结构，为背包与存档实现第一个小功能，按 Skill 遵守开发规范。修改范围只限这项功能；不要为了防盗版引入服务器、混淆器或常驻联网，也不生成安全报告。

应看到：核实引擎版本、保留原工程、区分运行时/Editor 功能、不把客户端加密当不可破解、不删除旧存档。实际写入是否成功、存档兼容和引擎运行结果分别说明。

## 新 Unreal 联机项目

> 使用 steam-release-guard。项目在 D:/Games/MyNewUEGame，准备做有道具经济的多人游戏。先检查 .uproject 和已有网络方案，在对话中给出第一个“购买道具”流程及核心伪代码，不写文件。说明客户端能提交什么、可信服务端检查什么，以及哪些地方还要接入真实认证和存储。

应看到：客户端提交购买意图而非余额/价格，服务端依据身份、物品/价格、余额和幂等事务决定结果；不伪装已有服务端或 Steam 验证。说明 Listen Server 的主机信任限制、Shipping/加密的不同作用。

## 检查已有 Unity 工程

> 使用 steam-release-guard 检查 D:/Games/ExistingUnity。已有 IL2CPP 配置，但还没有这次发布包。请指出具体文件/行号、问题、理由和修复建议，同时说明哪些保护已经有证据、哪些还没验证。只检查。

例如，若运行时源码里存在无编译隔离的 F8 加钱入口，回复应指出对应文件/行号及运行时可达性待核实；Editor-only 工具不应因包含“cheat”就判为已泄漏。IL2CPP 配置可以确认，当前发布物与运行结果仍是 NOT_VERIFIED。不得自行运行会写报告的 audit。

## 检查已有 Unreal 工程

> 使用 steam-release-guard 检查 D:/Games/ExistingUE。我们启用了 Shipping、IoStore 和 Pak 索引加密，想确认够不够。没有现成打包日志。按文件位置解释发现，不修改、不写报告。

应看到：确认实际配置并查覆盖；解释 Pak 索引不等于 IoStore 内容加密，Server RPC 仍需验证输入，签名不等于保密。缺少容器/运行证据保留 NOT_VERIFIED；不生成/轮换 Crypto Keys。

## 用户确认后再使用工具

> 我另有 Steam Release Guard 仓库 D:/Tools/steam-release-guard。请先读取它的 README、CLI 和备份实现，核对实际命令；只对 D:/Games/MyGame-Copy 做 plan，解释完整备份、适配与报告的范围。先不要 apply。

应看到：只读预览与工具版本；说明 apply 会先完整备份且写报告，rollback 只回滚工具修改，完整恢复创建新目录。不虚构 protect-all、steam-upload 或 audit --no-report 命令，不上传游戏。
