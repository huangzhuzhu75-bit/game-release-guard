# Validation record

Validation date: **2026-11-25 (Asia/Tokyo)**. This record distinguishes the tool's tests from shipping a real game.

## Verified locally

| Check | Result |
| --- | --- |
| Python runtime | CPython **3.12.14**, Windows; standard library only |
| Behavioral tests | **33 discovered; 32 passed; 1 skipped**. No failures. |
| Recovery tests | Byte-exact restoration, duplicate apply, interrupted apply recovery, corrupt-backup rejection, later-edit conflict rejection |
| Configuration tests | Unicode / spaces, UTF-16 BOM, CRLF, duplicate scalar sections, preserved UE array entries, valid / invalid / zero encryption keys, IoStore preservation |
| Artifact checks | Managed DLLs, symbols, Unity debug boot flags, private config / Steam development files, source, loose assets, container uncertainty, empty output |
| File handling | Disjoint staging, no overwrite of existing outputs, SHA256 copy verification, source preservation, path traversal rejection, report directory ownership |
| Desktop application | Tk 8.6 interface construction and asynchronous one-click apply callback completed against a synthetic UE project; generated a manual-review report and restored button availability |
| Unity adapter API compilation | **Passed**, compiled against installed **Unity 6000.6.6f1** Editor API assemblies with its bundled C# compiler; no new packages installed |
| PowerShell | Launch, Steam DRM and Unity compile scripts parsed successfully; the DRM script rejected missing upload acknowledgment before touching input files or running SteamCMD |
| GitHub workflow syntax | Validated by actionlint **1.7.12** |
| Secret scanning | Gitleaks **8.30.1** found no secrets in the tool source tree |

The skipped local test creates a symbolic link, which this Windows account could not create. It remains enabled on CI hosts with that capability. Linux CI intentionally skips the desktop GUI test without a display.

Synthetic `.exe`, `.dll`, `.pak` and asset fixtures are **not real games or valid engine packages**. They validate classification, safety and control flow; they do not validate decompilation resistance, encryption strength or gameplay.

## Not established by this validation

- A complete Unity IL2CPP game build: the installed Windows player variations contained Mono, with no Windows IL2CPP variation found. The adapter compiled successfully, but a real IL2CPP build requires the matching module and compiler toolchain.
- Actual Unity Editor callback execution, plugin compatibility or runtime game behavior. Normal API compilation is not a runtime integration test.
- Unreal Editor / UAT execution: configuration and command-generation behavior were tested using synthetic UE 5.6 project files. No installed Unreal engine was used.
- Pak or IoStore encryption in a produced archive, actual extraction difficulty, full-asset encryption performance or patch-size impact.
- Steam DRM wrapping, authentication, depot upload or testing from a Steam branch. No executable was sent to Valve during development.
- Full visual desktop review or validation on every Python / engine / Windows version. The GUI's programmatic smoke test is not manual usability approval.

The repository workflow runs the tool tests on Windows / Linux with Python 3.10 / 3.12. Inspect the actual GitHub Actions run for its status; a checked-in workflow is not evidence that a remote run passed.

## Reproduce

```powershell
python -m unittest discover -s tests -v
python -m compileall -q steam_release_guard
./scripts/Test-UnityAdapter.ps1 -UnityEditor 'D:/Engines/Unity/Editor/Unity.exe'
```

For game release acceptance, use [RELEASE-CHECKLIST.md](RELEASE-CHECKLIST.md) against the exact packaged build and the Steam test branch. `release_status` intentionally remains `BLOCKED` or `REQUIRES_MANUAL_REVIEW` until an external human release review is recorded.
