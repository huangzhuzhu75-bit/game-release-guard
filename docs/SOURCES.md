# Sources and reuse review

Checked 2026-11-25 (Asia/Tokyo). No third-party implementation was copied, bundled or installed. Runtime uses Python's standard library; the Unity adapter calls Unity's own Editor API. No art, audio, game assets or Steam SDK binaries are redistributed.

## Official references

- [Unity 6000.0 SetScriptingBackend](https://docs.unity.com/en-us/engine/6000.0/script-reference/unityeditor/playersettings/setscriptingbackend): `NamedBuildTarget.Standalone` and IL2CPP API.
- [Unity 6000.0 BuildOptions](https://docs.unity.com/en-us/engine/6000.0/script-reference/unityeditor/buildoptions): release/debug/test build flags.
- [Unity 6000.0 custom build scripts](https://docs.unity.com/en-us/engine/6000.0/manual/building-and-publishing/build-customize-build-pipeline/build-script-build): `BuildPlayerOptions` and enabled scenes.
- [Unity 6000.0 command line](https://docs.unity.com/en-us/engine/6000.0/manual/unity-editor/command-line-arguments/editor): batch builds, target and executeMethod.
- [Unity 6000.6 GetActiveBuildProfile](https://docs.unity.com/en-us/engine/6000.6/script-reference/unityeditor/build/profile/buildprofile/getactivebuildprofile): platform profile versus custom profile.
- [Unity 6000.6 deep profiling setting](https://docs.unity.com/en-us/engine/6000.6/script-reference/unityeditor/editoruserbuildsettings/buildwithdeepprofilingsupport).
- [UE 5.6 packaging](https://dev.epicgames.com/documentation/en-us/unreal-engine/packaging-your-project?application_version=5.6): build configuration and staged output.
- [UE 5.6 project settings](https://dev.epicgames.com/documentation/en-us/unreal-engine/project-section-of-the-unreal-engine-project-settings?application_version=5.6).
- [UProjectPackagingSettings](https://dev.epicgames.com/documentation/unreal-engine/API/Developer/DeveloperToolSettings/UProjectPackagingSettings): `BuildConfiguration`, `IncludeDebugFiles`, `UsePakFile` (no `b` prefix).
- [UCryptoKeysSettings](https://dev.epicgames.com/documentation/unreal-engine/API/Plugins/CryptoKeys/UCryptoKeysSettings): `Config=Crypto`, encryption flags, private key handling and patch/IO tradeoffs.
- [Epic BuildCookRun example](https://dev.epicgames.com/documentation/en-us/unreal-engine/quick-start-guide-for-using-container-images-in-unreal-engine): Shipping, nodebuginfo, cook/stage/pak/archive command design. The documented example uses Linux; this tool adapts platform and launcher to Windows, with engine execution still requiring per-project validation.
- [Valve Steam DRM](https://partner.steamgames.com/doc/features/drm): server-side EXE wrapping, `drm_wrap`, tool name, flags, limitations and compatibility.
- [Valve Steamworks API overview](https://partner.steamgames.com/doc/sdk/api): development `steam_appid.txt` should not ship with the build.

Context7 was queried first using the official Unity and Epic documentation indexes. Unity resolution exposed 6000.6; UE's index was unversioned. Unity 6000.0 / 6000.6 and UE 5.6 versioned pages were consulted directly. Versioned Epic API pages were not retrievable through the browser fetch, so field names were checked against the current official API index via Context7. **This does not establish every UE 5.x release as tested.** See VALIDATION.md for the local compiler version and unverified engine behavior.

## Existing open-source candidates

| Candidate | Snapshot | Assessment |
| --- | --- | --- |
| [game-ci/unity-builder](https://github.com/game-ci/unity-builder) | 1,115 stars; pushed 2026-11-15; commit `107e018f9df656df4d66d24cff5eb903171214e3`; [MIT license](https://github.com/game-ci/unity-builder/blob/107e018f9df656df4d66d24cff5eb903171214e3/LICENSE) | Active Unity CI building. Manifest examined: Node >=24, Actions libraries, Unity licensing/runner setup. Useful integration reference; not an offline Unity+UE hardening tool. Not installed, copied or runtime-tested here. |
| [superunitybuild/buildtool](https://github.com/superunitybuild/buildtool) | 1,341 stars; last pushed 2025-01-07; commit `3b5cc7f7139f9f200f6371507e4b67bd925d102e`; [MIT license](https://github.com/superunitybuild/buildtool/blob/3b5cc7f7139f9f200f6371507e4b67bd925d102e/LICENSE.md) | Unity Editor build tooling; maintenance recency did not meet the active-project preference. No UE adapter. Not installed, copied or runtime-tested here. |

Repository searches used `unity build automation stars:>500` and `unreal build automation stars:>500`; the latter returned no matching repository in the connected search. This is a bounded search result, not a claim that no such software exists. No candidate was adopted as a dependency because that would introduce a separate build environment without solving the cross-engine inspection / recovery scope.

The project therefore implements a small standard-library orchestration layer and uses each engine's documented settings. It does not bundle extraction / decompilation tools, invent asset encryption, or redistribute proprietary engine components.

## CI sources

- `actions/checkout` v4: pinned to `11d5960a326750d5838078e36cf38b85af677262` after resolving the official tag.
- `actions/setup-python` v5: pinned to `a26af69be951a213d495a4c3e4e4022e16d87065` after resolving the official tag.

These actions run only on GitHub CI. Python 3.10 / 3.12 are requested there; local validation used 3.12.14. No test needs a Steam account, game source, engine license, API key, or external service.

## Full project backup addition

Reviewed 2026-11-25. [restic/restic](https://github.com/restic/restic) (37,443 stars, pushed 2026-11-24, BSD-2-Clause) and [borgbackup/borg](https://github.com/borgbackup/borg) (13,950 stars, pushed 2026-11-24, BSD-3-Clause verified from LICENSE) were evaluated as mature backup candidates. Restic's [repository design](https://github.com/restic/restic/blob/master/doc/design.rst) and Borg's [data verification](https://borgbackup.readthedocs.io/en/stable/usage/check.html) informed the review of completion and integrity requirements. Neither tool was installed, run, bundled or adopted; no implementation was copied. External repository formats/runtimes would add deployment work to the existing dependency-free desktop tool. This addition instead uses the existing local locks, progress and transaction helpers, plus standard-library file I/O and SHA256, with independent failure and restore tests.

Context7 exposed CPython 3.12.3/3.12.16 but not installed 3.12.14. The versioned 3.12.3 index and [official Python 3.12 documentation](https://docs.python.org/3.12/library/shutil.html) were consulted, then the exact [CPython v3.12.14 shutil documentation](https://github.com/python/cpython/blob/v3.12.14/Doc/library/shutil.rst) was successfully retrieved through the GitHub connector after web fetch failed. The Windows metadata limitations are explicit: file owners, ACLs and alternate data streams are not covered by ordinary copying. This feature promises file contents and directory structure, refuses links/special files, and does not claim a filesystem image or live VSS snapshot. Implementation remains compatible with Python 3.10+; the local minimum running result is the repository's full-backup/restore test suite on 3.12.14.

The Windows CI Tk cleanup failure used CPython 3.10.11. Context7 did not expose that exact release; its threading-model guidance was cross-checked against the retrieved [v3.10.11 Tkinter documentation](https://github.com/python/cpython/blob/v3.10.11/Doc/library/tkinter.rst#threading-model). GUI test teardown now collects destroyed test interpreters on their creating thread, before later tests launch workers.

## README navigation reference (2026-11-27)

The clickable AI-name navigation was inspired by [nexu-io/opengame's README](https://github.com/nexu-io/opengame/blob/73f8215a480a040613c06979fc1605ab734f2da0/README.md) at commit `73f8215a480a040613c06979fc1605ab734f2da0` ([Apache-2.0 license](https://github.com/nexu-io/opengame/blob/73f8215a480a040613c06979fc1605ab734f2da0/LICENSE)). Our text-only SVG buttons and universal prompts were authored for this repository. No OpenGame code, logos, MCP configuration or installation commands were copied; it is not a dependency. Every button opens the same Markdown instructions, without implying a native integration or endorsement. Skill contents and historical validation records remain separate from this navigation.
