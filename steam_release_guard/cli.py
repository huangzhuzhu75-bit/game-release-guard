"""Command-line entry points. No installs, uploads or engine execution on apply."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import (STATE, GuardError, apply, audit, atomic_write, build_script, detect_project,
                   plan, rollback, save_report, stage_release, validate_report_directory)


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Local Steam release hardening for Unity 6 / UE5 Windows projects.")
    root.add_argument("--version", action="version", version=__version__)
    sub = root.add_subparsers(dest="command", required=True)
    sub.add_parser("gui", help="Open the local desktop interface")
    for name in ("audit", "plan", "apply", "rollback", "build-script"):
        command = sub.add_parser(name)
        command.add_argument("project", type=Path, help="Project root or .uproject")
        if name in {"plan", "apply"}:
            command.add_argument("--encrypt-pak-index", action="store_true", help="UE only; requires an existing valid key")
        if name in {"audit", "apply"}:
            command.add_argument("--build", type=Path, help="Exact packaged depot folder, not the source project")
            command.add_argument("--report-dir", type=Path)
        if name == "audit":
            command.add_argument("--fail-on-warnings", action="store_true", help="CI gate on heuristic warnings too; manual review remains required")
        if name == "build-script":
            command.add_argument("--tool", type=Path, required=True, help="Exact Unity.exe or RunUAT.bat")
            command.add_argument("--output", type=Path, required=True, help="New build output directory")
            command.add_argument("--save", type=Path, help="Save a PowerShell script; it is not automatically executed")
    stage = sub.add_parser("stage", help="Copy a build into separate release / private-symbol folders; preserve originals")
    stage.add_argument("build", type=Path)
    stage.add_argument("--release", required=True, type=Path)
    stage.add_argument("--symbols", required=True, type=Path)
    return root


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "gui":
            from .gui import launch
            launch()
            return 0
        if args.command == "stage":
            result = stage_release(args.build, args.release, args.symbols)
            print(f"Copied and SHA256-verified {len(result['files'])} files. Original build preserved.")
            print("Run audit against the RELEASE folder before Steam upload.")
            return 0
        project = detect_project(args.project)
        if args.command == "plan":
            changes = plan(project, args.encrypt_pak_index)
            print(json.dumps({"engine": project.engine, "version": project.version,
                              "changes": [{"path": c.path, "purpose": c.purpose} for c in changes]}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "rollback":
            print(f"Restored: {rollback(project)}")
            return 0
        if args.command == "build-script":
            script = build_script(project, args.tool, args.output)
            if args.save:
                destination = args.save.expanduser().resolve()
                if destination.exists():
                    raise GuardError("Build script already exists; choose a new --save path.")
                # BOM makes Unicode paths readable by Windows PowerShell 5.1.
                atomic_write(destination, script.encode("utf-8-sig"))
                print(f"Build script saved (not executed): {destination}")
            else:
                print(script)
            return 0
        report_dir = args.report_dir or project.root / STATE / "reports" / "latest"
        validate_report_directory(report_dir)
        if args.command == "apply":
            # Validate report/build inputs before modifying any settings.
            if args.build:
                audit(project, args.build)
            result = apply(project, args.encrypt_pak_index)
            print(f"Backup and recovery journal: {result}" if result else "Already adapted; no project files changed.")
        report = audit(project, args.build)
        path = save_report(report, report_dir)
        for finding in report["findings"]:
            print(f"[{finding['status'].upper()}] {finding['id']}: {finding['title']}")
        print(f"{report['release_status']} | report: {path}")
        blocked = report["automated_gate"] == "failed"
        if getattr(args, "fail_on_warnings", False):
            blocked = blocked or any(f["status"] == "warn" for f in report["findings"])
        return 2 if blocked else 0
    except (GuardError, OSError, ValueError, UnicodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
