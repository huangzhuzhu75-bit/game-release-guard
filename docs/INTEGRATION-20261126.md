# V2 integration and public-launch preparation / V2 整合与公开准备

This record separates software integration from real-game acceptance. It contains no user game data or private audit logs.

## Integration / 整合顺序

1. PR #2 HEAD `3c452865bd611d7afdfad5991cfedb911ba4b56a` contained the targeted Pak/IoStore and explicit-container fixes. Both four-environment CI runs passed; no unresolved review threads or blocking reviews were present.
2. PR #2 was merged into `v2/p0-and-ai-guides` using merge commit `dbb4fb11fe6df71eeb43376d3e5a46e21e1341b9`.
3. PR #1 was rechecked at that new HEAD. Its [PR matrix](https://github.com/huangzhuzhu75-bit/game-release-guard/actions/runs/45837401017) and [branch matrix](https://github.com/huangzhuzhu75-bit/game-release-guard/actions/runs/45837388460) both passed Windows/Linux × Python 3.10/3.12. No unresolved review or conflict was present.
4. PR #1 was merged into main with `71ce52b51a25a077e8d655953a24222cbc93ae6f`. Both merge commits retain their parents. The integrated tree is `a324da18c0e157f7acf49566bbaa30529a789fa7`, exactly the reviewed P3 tree: 72 tracked files, including P0, Skill and all P3 modules/tests.

按 PR #2 → PR #1 的依赖顺序合并，未用 P3 覆盖 main、未压缩或删除开发历史。整合提交的代码树与已验收候选一致。

## Homepage / 首页

Chinese and English READMEs provide matching commands, installation paths, feature status and safety limits. The original detailed usage remains in `USAGE.zh-CN.md`; native AI support is not inferred from an installation path. The canonical Skill changes only its integration-status sentence, not its security rules. Earlier four-scenario Codex evidence is retained, not represented as a new AI-client test.

首页采用本仓库原创 SVG 横幅、GitHub 支持的 Markdown 和静态语言入口；没有脚本、遥测、下载量/Stars 造假或新保护模块。新增双语命令一致性检查，保留所有旧测试。MIT 许可不变，第三方引擎/保护器不随仓库分发。

Local Windows 10 / Python 3.12.14: **126 tests, 125 passed and 1 existing symlink-permission skip**. All four PowerShell entry points parsed successfully. Both READMEs and both installation guides have matching section structure; their CLI examples are checked against the real parser, and README commands are compared across languages. Runtime Python modules, Unity bridges, scripts and the CI workflow are byte-identical to the integrated baseline. Final main CI is authoritative for the published commit.

## Public-content review / 公开内容检查

- Before integration, all three retained branch histories covered 16 reachable commits, 142 distinct file blobs and 72 historical paths. Gitleaks 8.30.1 scanned them with default rules, redaction and allow-comment bypass disabled; no credential finding was reported. Separate inventory checks found no binary blobs, private game/assets/build/backup/symbol files, LFS pointers, tracked real Crypto configuration, personal directories or content email addresses.
- The two integration commits contain the same reviewed tree. There were no remote tags or releases. The initial 21 Actions runs had no artifacts; all 84 job logs were retrieved and scanned (approximately 2.31 MB), with no credential finding. Subsequent documentation commits and runs require the same final review before visibility changes.
- Standard commit-author contact metadata exists in history. It is a separate privacy decision for the owner before public exposure; it is not silently erased or described as a credential leak. No actual address is copied into this document.
- These are bounded inspection results, not a guarantee that no secret can ever be present. Repository visibility, final commit CI and anonymous access must be checked at the final publication step. No game, private backup or private audit log is included in the source distribution.

所有保留分支、历史内容、工作流日志和附件都纳入公开检查；不是只检查当前目录或依赖 `.gitignore`。未发现需要撤销/轮换的实际凭据，未重写正常源代码历史。作者联系方式需在最终公开前单独确认；没有因此擅自更改 GitHub 全局身份设置。

## Remaining acceptance / 仍未完成的验收

Real Obfuz builds, IL2CPP gameplay, reflection/serialization, existing saves, RPC/plugins, UE encryption/signing/resource loads, DLC/patches, Steam online/offline/test-branch behavior and actual performance measurements remain **NOT_VERIFIED**. String/control-flow extensions, metadata encryption, automatic asset chunks/per-grade encryption and automatic in-game integrity integration remain **NOT_IMPLEMENTED**. No Stable / Production Ready release is created by this integration.

真实引擎和游戏效果继续未验证；公开源码与通过工具测试，不等于这些效果已经通过验收。
