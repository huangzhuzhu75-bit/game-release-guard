"""Verified full project files, outside the project; restore only to a new folder."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import uuid
from pathlib import Path, PurePosixPath

from . import core as c
from .operations import Cancelled, GuardError, Operation, check_space, load_journal, safe_error, seal, writer

MANIFEST = "srg-project-backup.json"
PAYLOAD = "project"


def safe_path(value):
    # Inspect the spelling before resolve() can hide a linked ancestor.
    path = Path(value).expanduser().absolute()
    if any(c.linked(p) for p in (path, *path.parents)):
        raise GuardError("Full backup paths must not contain symlinks or junctions.")
    return c.absolute_path(path)


def disjoint(first, second):
    if first == second or first.is_relative_to(second) or second.is_relative_to(first):
        raise GuardError("Backup, original project and restored project must be in separate, non-nested directories.")


def backup_root(project, destination=None):
    source = safe_path(project.root)
    name = source.name if len(source.name) < 180 else source.name[:100] + "-" + c.digest(str(source).encode())[:8]
    root = safe_path(destination or source.parent / (name + ".srg-backups"))
    disjoint(source, root)
    if root.exists() and not root.is_dir():
        raise GuardError("Choose a directory for full project backups.")
    return root


def relative_name(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise GuardError("Invalid path in full project backup.")
    parts = value.split("/")
    if PurePosixPath(value).is_absolute() or any(p in {"", ".", ".."} for p in parts):
        raise GuardError("Invalid path in full project backup.")
    return value


def signature(info):
    # Windows stat infers executable bits from the filename; fstat does not.
    # Its ctime semantics can also differ. Compare stable fields there and rehash
    # contents on both sides; keep POSIX ctime/permissions as extra detectors.
    return (info.st_size, info.st_mtime_ns, info.st_ctime_ns if os.name != "nt" else 0,
            info.st_dev, info.st_ino, info.st_mode & ~0o111 if os.name == "nt" else info.st_mode)


def inventory(root, op):
    root = safe_path(root)
    if not root.is_dir():
        raise GuardError("Full backup source directory is missing.")
    files, directories, seen = {}, [], set()
    pending = [root]
    while pending:
        op.check_cancel()
        folder = pending.pop()
        safe_path(folder)
        with os.scandir(folder) as iterator:
            entries = sorted(iterator, key=lambda e: e.name)
        for item in entries:
            op.check_cancel()
            path = Path(item.path)
            name = relative_name(path.relative_to(root).as_posix())
            if name.casefold() in seen:
                raise GuardError("Case-colliding paths cannot be backed up portably.")
            seen.add(name.casefold())
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise GuardError("Full backup refuses symlinks/junctions; no files will be silently omitted.")
            if stat.S_ISDIR(info.st_mode):
                directories.append(name)
                pending.append(path)
            elif stat.S_ISREG(info.st_mode):
                files[name] = signature(info)
            else:
                raise GuardError("Full backup requires regular files and directories; special files are unsupported.")
    return dict(sorted(files.items())), sorted(directories)


def preview(project, destination=None, *, operation=None):
    op = operation or Operation()
    root = backup_root(project, destination)
    op.step("scanning full project backup")
    files, directories = inventory(project.root, op)
    return {"source": str(project.root), "backup_root": str(root), "file_count": len(files),
            "directory_count": len(directories), "total_bytes": sum(v[0] for v in files.values()),
            "scope": "All regular files, hidden files and empty directories inside the project; no exclusions.",
            "restore": "A new directory only; never overwrite the current project."}


def _copy(source, target, expected, op):
    safe_path(source)
    safe_path(target)
    digest = hashlib.sha256()
    with source.open("rb") as reader:
        if signature(os.fstat(reader.fileno())) != expected:
            raise GuardError("Project changed during full backup; close the editor and retry.")
        with target.open("xb") as output:
            while True:
                op.check_cancel()
                block = reader.read(1024 * 1024)
                if not block:
                    break
                output.write(block)
                digest.update(block)
            output.flush()
            os.fsync(output.fileno())
        if signature(os.fstat(reader.fileno())) != expected or signature(source.stat()) != expected:
            raise GuardError("Project changed during full backup; close the editor and retry.")
    os.utime(target, ns=(expected[1], expected[1]))
    os.chmod(target, stat.S_IMODE(expected[5]))
    return digest.hexdigest()


def _hash(path, op):
    safe_path(path)
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            op.check_cancel()
            result.update(block)
    return result.hexdigest()


def _record(path, journal, status):
    journal.update(schema=2, operation="project-backup", status=status,
                   file_count=len(journal["files"]), tool_version=c.__version__)
    c.write_json(path, seal(journal))


def _verify_payload(root, journal, op):
    files, directories = inventory(root, op)
    if set(files) != {f["path"] for f in journal["files"]} or directories != sorted(journal["directories"]):
        raise GuardError("Full backup inventory mismatch: missing or unexpected files/directories.")
    for index, entry in enumerate(journal["files"]):
        op.step("verifying full project files", index, len(files))
        if files[entry["path"]][0] != entry["size"] or _hash(c.local_path(root, entry["path"]), op) != entry["sha256"]:
            raise GuardError("Full backup file integrity check failed. Nothing will be restored or adapted.")


def create(project, destination=None, *, operation=None, expected_preview=None):
    op = operation or Operation()
    with writer():
        current = preview(project, destination, operation=op)
        if expected_preview is not None and current != expected_preview:
            raise GuardError("Full backup scope changed after preview; review it again.")
        files, directories = inventory(project.root, op)
        root = backup_root(project, destination)
        identities = list(dict.fromkeys([str(project.root), *restored_roots(project.root)]))
        check_space([(root, sum(v[0] for v in files.values()) + len(files) * 1024)])
        stamp = c.datetime.now(c.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
        snapshot = root / stamp
        snapshot.mkdir(parents=True, exist_ok=False)
        manifest = snapshot / MANIFEST
        payload = snapshot / PAYLOAD
        journal = {"source": str(project.root), "engine": project.engine, "engine_version": project.version,
                   "project_roots": identities,
                   "created_utc": c.utc_now(), "directories": directories,
                   "files": [{"path": name, "size": info[0], "mtime_ns": info[1],
                              "mode": stat.S_IMODE(info[5]), "sha256": None} for name, info in files.items()]}
        try:
            _record(manifest, journal, "INCOMPLETE")
            payload.mkdir()
            for name in directories:
                c.local_path(payload, name).mkdir(parents=True, exist_ok=True)
            for index, entry in enumerate(journal["files"]):
                op.step("copying full project backup", index, len(files))
                name = entry["path"]
                entry["sha256"] = _copy(c.local_path(project.root, name), c.local_path(payload, name), files[name], op)
            # Re-read both source and copy: a successful write alone is insufficient.
            _verify_payload(payload, journal, op)
            _verify_payload(project.root, journal, op)
            if inventory(project.root, op) != (files, directories):
                raise GuardError("Project changed during full backup verification; close the editor and retry.")
            op.step("committing verified full backup", len(files), len(files))
            _record(manifest, journal, "COMPLETE")
            op.progress({"phase": "full project backup verified", "current": len(files), "total": len(files),
                         "cancellable": True, "backup_path": str(snapshot)})
        except BaseException as error:
            try:
                _record(manifest, journal, "INCOMPLETE")
            except (OSError, GuardError):
                pass
            if isinstance(error, (Cancelled, KeyboardInterrupt)):
                raise Cancelled(f"Full backup cancelled; project untouched. Incomplete backup: {snapshot}") from None
            raise GuardError(f"Full backup failed ({safe_error(error)}). Project not adapted. Incomplete backup: {snapshot}") from None
        finally:
            op.cancellable = True
        return {**current, "status": "COMPLETE", "backup_path": str(snapshot), "manifest": str(manifest)}


def _load(value):
    snapshot = safe_path(value)
    manifest = snapshot / MANIFEST
    if not manifest.is_file():
        raise GuardError("Select a full backup directory containing srg-project-backup.json.")
    safe_path(manifest)
    journal = load_journal(manifest, "project-backup")
    if journal.get("status") != "COMPLETE":
        raise GuardError("Full backup is INCOMPLETE; it cannot be used for restoration.")
    if not isinstance(journal.get("source"), str) or not isinstance(journal.get("directories"), list):
        raise GuardError("Invalid full backup manifest.")
    roots = journal.get("project_roots", [journal["source"]])
    if not isinstance(roots, list) or not roots or any(not isinstance(p, str) or not Path(p).is_absolute() for p in roots):
        raise GuardError("Invalid full backup project identity.")
    seen, directories = set(), set()
    for name in journal["directories"]:
        key = relative_name(name).casefold()
        if key in seen:
            raise GuardError("Duplicate full backup path.")
        seen.add(key)
        directories.add(name)
    for entry in journal["files"]:
        if not isinstance(entry, dict):
            raise GuardError("Invalid full backup file record.")
        name = relative_name(entry.get("path"))
        if name.casefold() in seen:
            raise GuardError("Duplicate full backup path.")
        seen.add(name.casefold())
        if (type(entry.get("size")) is not int or entry["size"] < 0
                or not isinstance(entry.get("sha256"), str) or not re.fullmatch("[0-9a-f]{64}", entry["sha256"])):
            raise GuardError("Invalid full backup file record.")
    for name in [*directories, *(f["path"] for f in journal["files"])]:
        if any(str(parent) not in directories for parent in PurePosixPath(name).parents if str(parent) != "."):
            raise GuardError("Missing parent directory in full backup manifest.")
    return snapshot, journal


def verify(value, *, operation=None):
    op = operation or Operation()
    snapshot, journal = _load(value)
    _verify_payload(snapshot / PAYLOAD, journal, op)
    return {"status": "VERIFIED", "backup_path": str(snapshot), "file_count": len(journal["files"]),
            "directory_count": len(journal["directories"]), "total_bytes": sum(f["size"] for f in journal["files"])}


def restore_preview(value, output):
    snapshot, journal = _load(value)
    target = safe_path(output)
    disjoint(snapshot, target)
    # Original media need not be mounted to restore a verified independent copy.
    disjoint(Path(journal["source"]), target)
    if target.exists() or target.with_name(target.name + ".srg-restore.json").exists():
        raise GuardError("Full restore requires a NEW directory; existing directories will never be overwritten.")
    return {"backup_path": str(snapshot), "output": str(target), "file_count": len(journal["files"]),
            "total_bytes": sum(f["size"] for f in journal["files"]), "integrity_sha256": journal["integrity_sha256"]}


def restore(value, output, *, operation=None, expected_preview=None):
    op = operation or Operation()
    with writer():
        previewed = restore_preview(value, output)
        if expected_preview is not None and previewed != expected_preview:
            raise GuardError("Full restore scope changed after preview.")
        snapshot, journal = _load(value)
        _verify_payload(snapshot / PAYLOAD, journal, op)  # Verify everything before creating the destination.
        target = safe_path(output)
        check_space([(target, previewed["total_bytes"] + len(journal["files"]) * 1024)])
        receipt = target.with_name(target.name + ".srg-restore.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        record = {**previewed, "status": "INCOMPLETE"}
        # Never replace a receipt created by somebody else between preview and commit.
        with receipt.open("x", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, indent=2))
            handle.flush()
            os.fsync(handle.fileno())
        try:
            target.mkdir(exist_ok=False)
            source = snapshot / PAYLOAD
            files, directories = inventory(source, op)
            for name in directories:
                c.local_path(target, name).mkdir(parents=True, exist_ok=True)
            for index, entry in enumerate(journal["files"]):
                op.step("restoring full project to new directory", index, len(files))
                name = entry["path"]
                checksum = _copy(c.local_path(source, name), c.local_path(target, name), files[name], op)
                if checksum != entry["sha256"]:
                    raise GuardError("Backup changed during restore. Keep the partial output for inspection.")
            _verify_payload(target, journal, op)
            op.step("committing verified restoration", len(files), len(files), cancellable=False)
            record["status"] = "COMPLETE"
            c.write_json(receipt, record)
        except BaseException as error:
            if isinstance(error, (Cancelled, KeyboardInterrupt)):
                raise Cancelled(f"Full restore cancelled; original preserved. Incomplete output: {target}") from None
            raise GuardError(f"Full restore incomplete ({safe_error(error)}). Original preserved; partial output: {target}") from None
        finally:
            op.cancellable = True
        return {**record, "receipt": str(receipt)}


def restored_roots(root):
    """Recognize transaction histories carried by a verified whole-project restore."""
    root = c.absolute_path(root)
    receipt = root.with_name(root.name + ".srg-restore.json")
    if not receipt.exists():
        return []
    try:
        safe_path(receipt)
        record = json.loads(receipt.read_text(encoding="utf-8"))
        if record["status"] != "COMPLETE" or c.absolute_path(record["output"]) != root:
            raise ValueError
        _, journal = _load(record["backup_path"])
        if record["integrity_sha256"] != journal["integrity_sha256"]:
            raise ValueError
        return journal.get("project_roots", [journal["source"]])
    except (OSError, ValueError, KeyError, TypeError, GuardError):
        raise GuardError("Full project restoration is incomplete or its receipt/backup is invalid. Preserve it and restore to another new directory.") from None
