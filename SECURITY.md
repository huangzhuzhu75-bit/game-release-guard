# Security and privacy boundaries

Steam Release Guard is a local release review aid. It does not claim to prevent copying, reverse engineering, resource extraction or piracy, and it is not anti-cheat software.

- `plan`, `apply`, `audit`, `stage` and `rollback` make no network calls. Opening an HTML report uses the local browser and a self-contained page without scripts or remote assets.
- `Invoke-SteamDrm.ps1` is the explicit exception: it invokes the user's SteamCMD and uploads the input EXE to Valve after `-AcknowledgeExecutableUpload` is supplied. It does not include credentials or upload a depot.
- A generated engine build script invokes the locally installed engine. Engines, plugins and custom build hooks have their own behavior and may contact services. Inspect those separately.
- Reports omit source snippets and key values, but file names can still be confidential. Keep reports and backups private. Backups may contain original crypto configuration; they are not encrypted at rest.
- The tool excludes its state from Git, and stops on backup corruption, path traversal, symlinks/junctions during inspection, conflicting later edits or occupied staging directories.
- Source inspection is heuristic. Do not interpret a match as proof of a vulnerability or an absence of matches as proof of safety. The tool does not parse Blueprint bytecode or binary plugins.
- Project files and transactions are intended to be used sequentially with the editor closed. Do not run simultaneous writers or edit configuration while a transaction is in progress.
- Always retain your own project version control and off-machine recovery plan. Local recovery journals do not replace a complete project backup.

If reporting a defect, provide the tool version, command, sanitized file layout and a minimal synthetic reproduction. Do not post game assets, Steam secrets, private symbols or encryption keys in issues.
