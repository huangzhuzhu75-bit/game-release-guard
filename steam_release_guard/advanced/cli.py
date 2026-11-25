"""Additive CLI namespace; no existing command is replaced."""
from pathlib import Path

from .. import core as c
from . import obfuscation
from .common import read_json


def add_parser(sub):
    root = sub.add_parser("advanced", help="Opt-in P3 protection and evidence tools")
    commands = root.add_subparsers(dest="advanced_command", required=True)
    detect = commands.add_parser("obfuscator-detect", help="Inspect an optional local Obfuz package without executing it")
    detect.add_argument("project", type=Path)
    detect.add_argument("--tool-path", type=Path)
    for name in ("unity-plan", "unity-apply", "unity-build"):
        cmd = commands.add_parser(name)
        cmd.add_argument("project", type=Path)
        cmd.add_argument("--config", required=True, type=Path)
        if name == "unity-apply":
            cmd.add_argument("--backup-dir", type=Path)
        if name == "unity-build":
            cmd.add_argument("--editor", required=True, type=Path)
            cmd.add_argument("--output", required=True, type=Path)
            cmd.add_argument("--evidence-dir", required=True, type=Path)
            cmd.add_argument("--timeout", type=int, default=3600)
        if name != "unity-plan":
            cmd.add_argument("--yes", action="store_true")
            cmd.add_argument("--dry-run", action="store_true")
    for cmd in commands.choices.values():
        cmd.add_argument("--json", action="store_true", default=__import__("argparse").SUPPRESS)
    return commands


def run(args, confirm, emit, operation):
    command = args.advanced_command
    project = c.detect_project(args.project)
    adapter = obfuscation.ObfuzAdapter()
    if command == "obfuscator-detect":
        return emit("INSPECTED", adapter.detect(project, args.tool_path))
    config = read_json(args.config)
    if command == "unity-build":
        preview = obfuscation.build_preview(project, config, args.editor, args.output, args.evidence_dir)
        decision = confirm(args, preview)
        if decision is not None:
            return decision
        record = obfuscation.build(project, config, args.editor, args.output, args.evidence_dir,
                                   operation=operation, timeout=args.timeout)
        return emit(record["status"], record, code=2 if record["status"] == "FAIL" else 0)
    planned = adapter.plan(project, config)
    preview = {"engine": project.engine, "engine_version": project.version,
               "changes": [{"path": x.path, "purpose": x.purpose, "before_sha256": x.before_sha256} for x in planned],
               "configuration": "REVIEW", "artifact": "NOT_VERIFIED", "runtime": "NOT_VERIFIED"}
    if command == "unity-plan":
        return emit("PREVIEW", preview)
    decision = confirm(args, preview)
    if decision is not None:
        return decision
    found = adapter.detect(project)
    if not any(x["api_supported"] for x in found["installed_candidates"]):
        raise c.GuardError("Install reviewed Obfuz 4.0.0 in the project before applying its bridge; no files changed.")
    manifest = obfuscation.apply(project, config, expected_plan=planned, backup_dir=args.backup_dir, operation=operation)
    return emit("APPLIED", {**preview, "journal": str(manifest) if manifest else None})
