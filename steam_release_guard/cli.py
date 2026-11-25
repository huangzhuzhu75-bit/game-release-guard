"""Local CLI: preview, explicit write consent and stable JSON envelopes."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .core import (STATE, GuardError, apply, audit, atomic_write, build_script, detect_project,
                   plan, rollback, save_report, stage_release, validate_report_directory)
from .operations import Cancelled, Operation, safe_error, writer
from .staging import cleanup_preview, cleanup_stage, preview as stage_preview
from .transactions import rollback_preview
from . import project_backup


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise GuardError("Invalid command or arguments. Run --help for the supported syntax.")


def parser() -> argparse.ArgumentParser:
    root = Parser(description="Local Steam release hardening for Unity 6 / UE5 Windows projects.")
    root.add_argument("--version", action="version", version=__version__)
    root.add_argument("--json", action="store_true", help="Emit one structured JSON result; never prompts")
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
        if name == "apply":
            command.add_argument("--backup-dir", type=Path, help="Full backup parent outside project; default sibling <project>.srg-backups")
        if name == "audit":
            command.add_argument("--fail-on-warnings", action="store_true")
        if name == "build-script":
            command.add_argument("--tool", type=Path, required=True, help="Exact Unity.exe or RunUAT.bat")
            command.add_argument("--output", type=Path, required=True, help="New build output directory")
            command.add_argument("--save", type=Path, help="Save a script; never execute it")
    stage = sub.add_parser("stage", help="Copy a build into disjoint release/private-symbol folders")
    stage.add_argument("build", type=Path)
    stage.add_argument("--release", required=True, type=Path)
    stage.add_argument("--symbols", required=True, type=Path)
    stage.add_argument("--project", type=Path, help="Optional project identity for the project lock")
    cleanup = sub.add_parser("stage-cleanup", help="Verify and remove only unchanged failed stage copies")
    cleanup.add_argument("journal", type=Path, help="Private srg-stage-journal.json")
    backup = sub.add_parser("backup", help="Copy and verify ALL project files outside the project")
    backup.add_argument("project", type=Path)
    backup.add_argument("--backup-dir", type=Path, help="Parent for a new dated backup; default sibling <project>.srg-backups")
    verify = sub.add_parser("backup-verify", help="Verify full backup contents without changing the project")
    verify.add_argument("backup", type=Path, help="Dated backup folder containing srg-project-backup.json")
    restore = sub.add_parser("backup-restore", help="Restore full backup into a NEW directory; never overwrite")
    restore.add_argument("backup", type=Path)
    restore.add_argument("--output", type=Path, required=True, help="A new project directory that does not exist")
    for name, command in sub.choices.items():
        command.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
        command.add_argument("--progress", action="store_true", help="Write phase progress to stderr")
        if name in {"apply", "rollback", "build-script", "stage", "stage-cleanup", "backup", "backup-restore"}:
            command.add_argument("--dry-run", action="store_true", help="Validate and preview only; no writes")
            command.add_argument("--yes", action="store_true", help="Explicit consent to the reviewed write operation")
    return root


def plan_result(project, changes):
    return {"engine": project.engine, "version": project.version,
            "changes": [{"path": c.path, "purpose": c.purpose, "before_sha256": c.before_sha256} for c in changes]}


def main(argv=None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    json_mode = "--json" in raw
    command = None

    def emit(status, result=None, error=None, code=0):
        if json_mode:
            print(json.dumps({"schema": 1, "tool_version": __version__, "command": command,
                              "status": status, "result": result, "error": error}, ensure_ascii=False, indent=2))
        elif error:
            print("ERROR: " + error, file=sys.stderr)
        elif isinstance(result, str):
            print(result)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return code

    def confirm(args, preview):
        if args.dry_run:
            return emit("PREVIEW", preview)
        if args.yes:
            return None
        if not json_mode and sys.stdin.isatty():
            print(json.dumps(preview, ensure_ascii=False, indent=2))
            if input("Apply this reviewed operation? [y/N] ").strip().lower() == "y":
                return None
        return emit("CONFIRMATION_REQUIRED", preview, code=3)

    try:
        args = parser().parse_args(raw)
        command = args.command
        if command == "gui":
            if json_mode:
                raise GuardError("gui does not support JSON mode; use a CLI command.")
            from .gui import launch
            launch()
            return 0

        def progress(event):
            if args.progress:
                print(json.dumps(event, ensure_ascii=False), file=sys.stderr)
        op = Operation(progress)
        if command == "backup-verify":
            return emit("VERIFIED", project_backup.verify(args.backup, operation=op))
        if command == "backup-restore":
            preview = project_backup.restore_preview(args.backup, args.output)
            decision = confirm(args, preview)
            if decision is not None:
                return decision
            return emit("COMPLETE", project_backup.restore(args.backup, args.output, operation=op, expected_preview=preview))
        if command == "stage":
            project = detect_project(args.project) if args.project else None
            preview = stage_preview(args.build, args.release, args.symbols, operation=op)
            decision = confirm(args, preview)
            if decision is not None:
                return decision
            result = stage_release(args.build, args.release, args.symbols, operation=op,
                                   project=project, expected_preview=preview)
            return emit("COMPLETE", result)
        if command == "stage-cleanup":
            journal, targets = cleanup_preview(args.journal)
            preview = {"status": journal["status"], "remove": [str(p) for p in targets],
                       "preserve": [journal["build"], str(args.journal)]}
            decision = confirm(args, preview)
            if decision is not None:
                return decision
            return emit("COMPLETE", cleanup_stage(args.journal, operation=op, expected_integrity=journal["integrity_sha256"]))
        project = detect_project(args.project)
        if command == "backup":
            preview = project_backup.preview(project, args.backup_dir, operation=op)
            decision = confirm(args, preview)
            if decision is not None:
                return decision
            return emit("COMPLETE", project_backup.create(project, args.backup_dir, operation=op, expected_preview=preview))
        if command == "plan":
            return emit("PREVIEW", plan_result(project, plan(project, args.encrypt_pak_index)))
        if command == "rollback":
            preview = rollback_preview(project)
            decision = confirm(args, preview)
            if decision is not None:
                return decision
            return emit("COMPLETE", {"restored": str(rollback(project, operation=op, expected_preview=preview))})
        if command == "build-script":
            script = build_script(project, args.tool, args.output)
            if not args.save:
                return emit("PREVIEW", {"script": script} if json_mode else script)
            destination = args.save.expanduser().resolve()
            if destination.exists():
                raise GuardError("Build script already exists; choose a new --save path.")
            decision = confirm(args, {"save": str(destination), "script": script, "execute": False})
            if decision is not None:
                return decision
            with writer(project):
                # Exclusive creation avoids overwriting a file that appeared after preview.
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as handle:
                    handle.write(script.encode("utf-8-sig"))
            return emit("COMPLETE", {"saved": str(destination), "executed": False})
        report_dir = args.report_dir or project.root / STATE / "reports" / "latest"
        validate_report_directory(report_dir)
        if args.build:
            audit(project, args.build, operation=op)  # Validate before any mutation, including consent prompts.
        backup = None
        changes = None
        full_preview = None
        if command == "apply":
            changes = plan(project, args.encrypt_pak_index)
            full_preview = project_backup.preview(project, args.backup_dir, operation=op) if changes else None
            decision = confirm(args, {**plan_result(project, changes), "full_backup": full_preview})
            if decision is not None:
                return decision
        # Keep apply and its resulting report in one serialized operation.
        with writer():
            if command == "apply":
                backup = apply(project, args.encrypt_pak_index, operation=op, expected_plan=changes,
                               backup_dir=args.backup_dir, expected_backup_preview=full_preview)
            op.step("auditing configuration and artifact", cancellable=False if backup else True)
            report = audit(project, args.build, operation=op if command == "audit" else None)
            op.step("writing local report", cancellable=False)
            path = save_report(report, report_dir)
        blocked = report["automated_gate"] == "failed"
        if getattr(args, "fail_on_warnings", False):
            blocked = blocked or any(f["status"] == "warn" for f in report["findings"])
        return emit("BLOCKED" if blocked else "REQUIRES_MANUAL_REVIEW",
                    {"backup": str(backup) if backup else None,
                     "full_backup": json.loads(backup.read_text(encoding="utf-8")).get("full_backup") if backup else None,
                     "report_path": str(path), "report": report}, code=2 if blocked else 0)
    except (KeyboardInterrupt, Cancelled) as error:
        return emit("CANCELLED", error=safe_error(error) if isinstance(error, Cancelled) else "Cancelled before completion; inspect recovery records.", code=130)
    except Exception as error:
        return emit("ERROR", error=safe_error(error), code=1)


if __name__ == "__main__":
    raise SystemExit(main())
