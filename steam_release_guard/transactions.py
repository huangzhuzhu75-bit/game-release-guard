"""Project transactions. Legacy schema 1 recovery remains supported."""
from __future__ import annotations

import re
import uuid
from pathlib import Path

from . import core as c
from .operations import GuardError, Operation, check_space, load_journal, seal, writer

STATES = {"prepared", "applying", "applied", "apply_incomplete", "rolling_back", "rollback_incomplete", "rolled_back"}


def record(path, journal, status):
    journal.update(schema=2, operation="apply", file_count=len(journal["files"]), status=status,
                   tool_version=c.__version__)
    c.write_json(path, seal(journal))


def read_manifest(project, manifest):
    from .project_backup import restored_roots
    journal = load_journal(manifest, "apply", allow_legacy=True)
    allowed_roots = {project.root, *(c.absolute_path(p) for p in restored_roots(project.root))}
    if not isinstance(journal.get("root"), str) or c.absolute_path(journal["root"]) not in allowed_roots or journal.get("status") not in STATES:
        raise GuardError("Backup belongs to a different project or has an invalid status. No files restored.")
    seen = set()
    if not journal["files"]:
        raise GuardError("Empty recovery journal. No files restored.")
    for number, entry in enumerate(journal["files"]):
        if (not isinstance(entry, dict) or not isinstance(entry.get("path"), str)
                or not {"path", "before_sha256", "after_sha256", "backup"}.issubset(entry)):
            raise GuardError("Invalid recovery entry. No files restored.")
        target = c.local_path(project.root, entry["path"])
        key = str(target).casefold()
        if key in seen or target.is_relative_to(project.root / c.STATE):
            raise GuardError("Duplicate or private recovery target. No files restored.")
        seen.add(key)
        for field in ("before_sha256", "after_sha256"):
            value = entry.get(field)
            if not (field == "before_sha256" and value is None) and not (
                    isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value)):
                raise GuardError("Invalid recovery hash. No files restored.")
        expected = f"{number:03d}.bak" if entry["before_sha256"] is not None else None
        if entry.get("backup") != expected:
            raise GuardError("Invalid backup path. No files restored.")
    return journal


def manifests(project):
    root = c.local_path(project.root, f"{c.STATE}/backups")
    if root.exists():
        for folder in sorted(root.iterdir(), reverse=True):
            manifest = c.local_path(project.root, (folder.relative_to(project.root) / "manifest.json").as_posix())
            if manifest.is_file():
                yield manifest


def pending(project):
    for path in manifests(project):
        try:
            journal = read_manifest(project, path)
        except GuardError:
            return True
        if journal["status"] not in {"applied", "rolled_back"}:
            return True
    return False


def apply(project, encrypt_index=False, *, operation=None, expected_plan=None, backup_dir=None,
          expected_backup_preview=None, planner=None):
    from . import project_backup
    make_plan = planner or (lambda: c.plan(project, encrypt_index))
    make_plan()
    op = operation or Operation()
    # Full snapshot precedes even the project lock/state-directory writes.
    with writer():
        if pending(project):
            raise GuardError("An incomplete project transaction needs rollback before a new apply.")
        changes = make_plan()
        if expected_plan is not None and changes != expected_plan:
            raise GuardError("Project changed after the preview. Review a fresh plan before applying.")
        if not changes:
            return None
        full = project_backup.create(project, backup_dir, operation=op, expected_preview=expected_backup_preview)
        op.check_cancel()
        return _apply(project, encrypt_index, operation=op, expected_plan=changes, full_backup=full, planner=make_plan)


def _apply(project, encrypt_index=False, *, operation=None, expected_plan=None, full_backup=None, planner=None):
    # Invalid versions/keys must not even create a project state directory.
    make_plan = planner or (lambda: c.plan(project, encrypt_index))
    make_plan()
    op = operation or Operation()
    with writer(project):
        if pending(project):
            raise GuardError("An incomplete project transaction needs rollback before a new apply.")
        changes = make_plan()
        if expected_plan is not None and changes != expected_plan:
            raise GuardError("Project changed after the preview. Review a fresh plan before applying.")
        if not changes:
            return None
        op.step("backup preflight", 0, len(changes))
        check_space([(project.root, sum(len(x.data) * 2 for x in changes) + sum(
            c.local_path(project.root, x.path).stat().st_size * 2 for x in changes if x.before_sha256 is not None))])
        tx = c.datetime.now(c.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
        folder = c.local_path(project.root, f"{c.STATE}/backups/{tx}")
        manifest = folder / "manifest.json"
        entries = []
        try:
            c.atomic_write(c.local_path(project.root, f"{c.STATE}/.gitignore"), b"*\n")
            for number, change in enumerate(changes):
                op.step("verifying backups", number, len(changes))
                target = c.local_path(project.root, change.path)
                before = target.read_bytes() if target.exists() else None
                if (c.digest(before) if before is not None else None) != change.before_sha256:
                    raise GuardError("Project changed during planning. No project files changed; review a fresh plan.")
                backup = f"{number:03d}.bak" if before is not None else None
                if backup:
                    c.atomic_write(folder / backup, before)
                    if c.file_digest(folder / backup) != change.before_sha256:
                        raise GuardError("Backup integrity check failed; no project files changed.")
                entries.append({"path": change.path, "before_sha256": change.before_sha256,
                                "after_sha256": c.digest(change.data), "backup": backup})
            journal = {"root": str(project.root), "created_utc": c.utc_now(), "files": entries,
                       "full_backup": full_backup}
            record(manifest, journal, "prepared")
            # Preflight every destination before the first mutation, not only as we go.
            for entry in entries:
                target = c.local_path(project.root, entry["path"])
                if (c.file_digest(target) if target.exists() else None) != entry["before_sha256"]:
                    raise GuardError("Project changed during backup preparation; no project files changed.")
            op.step("ready to commit", len(changes), len(changes))
        except BaseException:
            # Only our newly created, flat preparation directory is eligible. No recursive delete.
            if folder.exists():
                try:
                    for path in folder.iterdir():
                        if path.is_file() and not c.linked(path) and (
                                path.name == "manifest.json" or re.fullmatch(r"\d+\.bak", path.name)):
                            path.unlink()
                    folder.rmdir()
                except OSError:
                    raise GuardError("Backup preparation failed; no project files changed. Retain the incomplete backup folder for manual inspection.") from None
            raise
        try:
            record(manifest, journal, "applying")
            for number, (change, entry) in enumerate(zip(changes, entries)):
                op.step("committing project (cannot cancel)", number, len(changes), cancellable=False)
                target = c.local_path(project.root, change.path)
                if (c.file_digest(target) if target.exists() else None) != entry["before_sha256"]:
                    raise GuardError("Project changed during commit.")
                c.atomic_write(target, change.data)
                if c.file_digest(target) != entry["after_sha256"]:
                    raise GuardError("Project write verification failed.")
            record(manifest, journal, "applied")
            op.step("project committed", len(changes), len(changes), cancellable=False)
        except BaseException as error:
            try:
                record(manifest, journal, "apply_incomplete")
            except (OSError, GuardError):
                pass  # Last prepared/applying record is sufficient for conflict-aware rollback.
            raise GuardError(f"Apply interrupted ({type(error).__name__}). Close the editor and run rollback. Recovery: {manifest}") from None
        return manifest


def prepare_rollback(project):
    for manifest in manifests(project):
        journal = read_manifest(project, manifest)
        if journal["status"] == "rolled_back":
            continue
        prepared = []
        for entry in journal["files"]:
            target = c.local_path(project.root, entry["path"])
            current = c.file_digest(target) if target.exists() else None
            if current not in (entry["before_sha256"], entry["after_sha256"]):
                raise GuardError(f"Rollback conflict: {entry['path']} changed after adaptation. No files restored.")
            before = None
            if entry["before_sha256"] is not None:
                before = c.local_path(manifest.parent, entry["backup"]).read_bytes()
                if c.digest(before) != entry["before_sha256"]:
                    raise GuardError("Backup integrity check failed. No files restored.")
            prepared.append((target, before, current))
        return manifest, journal, prepared
    raise GuardError("No pending release-guard backup exists; all recorded changes may already be rolled back.")


def rollback_preview(project):
    manifest, journal, _ = prepare_rollback(project)
    return {"journal": str(manifest), "legacy_journal": journal["schema"] == 1,
            "files": [entry["path"] for entry in journal["files"]]}


def rollback(project, *, operation=None, expected_preview=None):
    op = operation or Operation()
    with writer(project):
        op.step("verifying rollback")
        if expected_preview is not None and rollback_preview(project) != expected_preview:
            raise GuardError("Recovery target changed after preview. Review again before rollback.")
        manifest, journal, prepared = prepare_rollback(project)
        check_space([(project.root, sum(len(data) for _, data, _ in prepared if data is not None))])
        op.step("ready to restore")
        try:
            record(manifest, journal, "rolling_back")
            for number, (target, before, expected) in enumerate(reversed(prepared)):
                op.step("restoring project (cannot cancel)", number, len(prepared), cancellable=False)
                c.local_path(project.root, target.relative_to(project.root).as_posix())
                if (c.file_digest(target) if target.exists() else None) != expected:
                    raise GuardError("Rollback conflict during restore.")
                if before is None:
                    if target.exists():
                        target.unlink()
                else:
                    c.atomic_write(target, before)
                if (c.file_digest(target) if target.exists() else None) != (c.digest(before) if before is not None else None):
                    raise GuardError("Restore verification failed.")
            journal["restored_utc"] = c.utc_now()
            record(manifest, journal, "rolled_back")
            op.step("rollback completed", len(prepared), len(prepared), cancellable=False)
        except BaseException as error:
            try:
                record(manifest, journal, "rollback_incomplete")
            except (OSError, GuardError):
                pass
            raise GuardError(f"Rollback interrupted ({type(error).__name__}). Preserve the journal and retry rollback after resolving file access/disk space: {manifest}") from None
        return manifest
