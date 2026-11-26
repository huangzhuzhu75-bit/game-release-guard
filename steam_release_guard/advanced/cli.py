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
    native = commands.add_parser("unity-inspect", help="Read-only PE, metadata and native-plugin evidence")
    native.add_argument("project", type=Path)
    native.add_argument("--build", type=Path, required=True)
    security = commands.add_parser("security-inspect", help="Read-only source/config risk candidates; no report file")
    security.add_argument("project", type=Path)
    for name in ("unreal-plan", "unreal-apply", "asset-plan"):
        cmd = commands.add_parser(name)
        cmd.add_argument("project", type=Path)
        cmd.add_argument("--config", type=Path, required=True)
        if name == "unreal-apply":
            cmd.add_argument("--backup-dir", type=Path)
            cmd.add_argument("--yes", action="store_true")
            cmd.add_argument("--dry-run", action="store_true")
    verify = commands.add_parser("unreal-verify", help="Run matching UE official tools on Pak and IoStore separately")
    verify.add_argument("project", type=Path)
    verify.add_argument("--engine-root", type=Path, required=True)
    verify.add_argument("--build", type=Path, required=True)
    verify.add_argument("--evidence-dir", type=Path, required=True)
    verify.add_argument("--crypto-json", type=Path)
    verify.add_argument("--yes", action="store_true")
    verify.add_argument("--dry-run", action="store_true")
    create = commands.add_parser("integrity-create", help="Create a release SHA256 manifest outside the build")
    create.add_argument("build", type=Path)
    create.add_argument("--build-id", required=True)
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--mutable", action="append", default=[])
    create.add_argument("--yes", action="store_true")
    create.add_argument("--dry-run", action="store_true")
    integrity = commands.add_parser("integrity-verify", help="Check files against an externally pinned manifest")
    integrity.add_argument("build", type=Path)
    integrity.add_argument("--manifest", type=Path, required=True)
    integrity.add_argument("--build-id", required=True)
    integrity.add_argument("--expected-manifest-sha256", required=True)
    drm = commands.add_parser("drm-inspect", help="Check retained original and wrapped PE; never upload")
    drm.add_argument("--original", type=Path, required=True)
    drm.add_argument("--wrapped", type=Path, required=True)
    drm.add_argument("--expected-original-sha256", required=True)
    commands.add_parser("acceptance-template", help="Print an unverified performance/runtime record template; no file writes")
    acceptance = commands.add_parser("acceptance-check", help="Compare metrics and bind evidence to exact baseline/candidate builds")
    acceptance.add_argument("record", type=Path)
    for arg in ("baseline-build", "candidate-build", "baseline-manifest", "candidate-manifest", "evidence-root"):
        acceptance.add_argument("--" + arg, type=Path, required=True)
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
    if command.startswith("acceptance-"):
        from . import acceptance
        if command == "acceptance-template":
            return emit("TEMPLATE", acceptance.template())
        record = acceptance.check(read_json(args.record), args.baseline_build, args.candidate_build,
                                  args.baseline_manifest, args.candidate_manifest, args.evidence_root)
        return emit("INSPECTED", record, code=2 if record["release_status"] == "BLOCKED" else 0)
    if command.startswith("integrity-") or command == "drm-inspect":
        return run_integrity(args, confirm, emit, operation)
    project = c.detect_project(args.project)
    if command == "security-inspect":
        from .security import audit
        return emit("INSPECTED", audit(project, operation=operation))
    if command.startswith("unreal-") or command == "asset-plan":
        return run_unreal(args, project, confirm, emit, operation)
    if command == "unity-inspect":
        from .binary import unity_audit
        inspected = unity_audit(project, args.build)
        return emit("INSPECTED", inspected, code=2 if inspected["release_status"] == "BLOCKED" else 0)
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


def run_unreal(args, project, confirm, emit, operation):
    from . import unreal
    command = args.advanced_command
    if command == "unreal-verify":
        preview = unreal.verify_preview(project, args.engine_root, args.build, args.evidence_dir, args.crypto_json)
        decision = confirm(args, preview)
        if decision is not None:
            return decision
        record = unreal.verify(project, args.engine_root, args.build, args.evidence_dir, args.crypto_json, operation=operation)
        return emit(record["status"], record, code=2 if record["status"] == "FAIL" else 0)
    config = read_json(args.config)
    if command == "asset-plan":
        return emit("PREVIEW", unreal.asset_plan(project, config))
    planned = unreal.UnrealAdapter().plan(project, config)
    preview = {"engine": project.engine, "engine_version": project.version,
               "changes": [{"path": x.path, "purpose": x.purpose, "before_sha256": x.before_sha256} for x in planned],
               "requested_switches": config["pak"], "container_policy": config["container_policy"],
               "pak_requested": unreal.CONTAINERS[config["container_policy"]][0],
               "iostore_requested": unreal.CONTAINERS[config["container_policy"]][1],
               "signing_key_validity": "NOT_VERIFIED" if config["pak"]["signing"] else "NOT_REQUESTED",
               "artifact": "NOT_VERIFIED", "runtime": "NOT_VERIFIED",
               "tradeoff": "Disabling a switch reduces its corresponding protection. All-asset encryption increases IO/patch cost; grade rules do not automatically create chunks."}
    if command == "unreal-plan":
        return emit("PREVIEW", preview)
    decision = confirm(args, preview)
    if decision is not None:
        return decision
    journal = unreal.apply(project, config, expected_plan=planned, backup_dir=args.backup_dir, operation=operation)
    return emit("APPLIED", {**preview, "journal": str(journal) if journal else None})


def run_integrity(args, confirm, emit, operation):
    from . import integrity
    if args.advanced_command == "drm-inspect":
        return emit("INSPECTED", integrity.drm_inspect(args.original, args.wrapped, args.expected_original_sha256))
    if args.advanced_command == "integrity-verify":
        record = integrity.verify(args.build, args.manifest, args.build_id, args.expected_manifest_sha256, operation=operation)
        return emit(record["status"], record, code=2 if record["status"] == "INTEGRITY_MISMATCH" else 0)
    preview = integrity.create_preview(args.build, args.build_id, args.output, args.mutable, operation=operation)
    decision = confirm(args, preview)
    if decision is not None:
        return decision
    return emit("CREATED", integrity.create(args.build, args.build_id, args.output, args.mutable,
                                           operation=operation, expected_preview=preview))
