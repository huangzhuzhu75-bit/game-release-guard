"""Independent copy transaction and conservative cleanup of incomplete outputs."""
from __future__ import annotations

import json
import os
import re
import uuid
from pathlib import Path

from . import core as c
from .operations import GuardError, Operation, check_space, load_journal, seal, writer

MARKER = ".srg-stage.json"
JOURNAL = "srg-stage-journal.json"
SYMBOL_MANIFEST = "srg-symbol-manifest.json"


def _root(path):
    path = Path(path).expanduser().absolute()
    if any(c.linked(p) for p in (path, *path.parents)):
        raise GuardError("Staging paths must not contain symlinks or junctions.")
    return c.absolute_path(path)


def _disjoint(paths):
    for i, path in enumerate(paths):
        for other in paths[i + 1:]:
            if path == other or path.is_relative_to(other) or other.is_relative_to(path):
                raise GuardError("Build, release and private-symbol folders must be disjoint, not nested.")


def preview(build, destination, symbols, *, operation=None):
    build, destination, symbols = map(_root, (build, destination, symbols))
    _disjoint([build, destination, symbols])
    if not build.is_dir():
        raise GuardError("Build folder does not exist.")
    for folder in (destination, symbols):
        if folder.exists() and (not folder.is_dir() or any(folder.iterdir())):
            raise GuardError("Release and private-symbol folders must be new or empty. Existing builds are never overwritten.")
    op = operation or Operation()
    paths = list(c.walk_files(build))
    if not paths:
        raise GuardError("Cannot stage an empty build.")
    files = []
    for number, path in enumerate(paths):
        op.step("hashing source build", number, len(paths))
        relative = path.relative_to(build)
        if any(part.casefold() in {".git", c.STATE, MARKER, JOURNAL, SYMBOL_MANIFEST}
               or ".srg-part-" in part.casefold() for part in relative.parts):
            raise GuardError("Build contains source-control/private-state/staging data; select only original packaged content.")
        files.append({"path": relative.as_posix(), "sha256": c.file_digest(path), "bytes": path.stat().st_size,
                      "location": "private_symbols" if c.private_symbol(relative) else "release"})
    return {"build": str(build), "release": str(destination), "symbols": str(symbols), "files": files,
            "file_count": len(files), "bytes": sum(f["bytes"] for f in files)}


def _marker(journal, status):
    return {"schema": 2, "operation": "stage", "transaction": journal["transaction"],
            "status": status, "file_count": journal["file_count"], "release_approved": False}


def _part(target, journal):
    # Keep valid long source filenames below the filesystem's per-component limit.
    suffix = c.digest(target.name.encode("utf-8"))[:24]
    return target.with_name(".srg-part-" + journal["transaction"] + "-" + suffix)


def _copy(source, partial, operation, number, total):
    with source.open("rb") as reader, partial.open("xb") as output:
        while True:
            operation.step("copying verified files", number, total)
            block = reader.read(1024 * 1024)
            if not block:
                break
            output.write(block)
        output.flush()
        os.fsync(output.fileno())


def _new_json(path, data):
    with path.open("xb") as handle:
        handle.write((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        handle.flush()
        os.fsync(handle.fileno())


def stage_release(build, destination, symbols, *, operation=None, project=None, expected_preview=None):
    op = operation or Operation()
    with writer(project):
        planned = preview(build, destination, symbols, operation=op)
        if expected_preview is not None and planned != expected_preview:
            raise GuardError("Build changed after preview; review again before staging.")
        build, destination, symbols = (Path(planned[k]) for k in ("build", "release", "symbols"))
        check_space([(destination, sum(f["bytes"] for f in planned["files"] if f["location"] == "release")),
                     (symbols, sum(f["bytes"] for f in planned["files"] if f["location"] == "private_symbols"))])
        journal = {**planned, "schema": 2, "operation": "stage", "tool_version": c.__version__,
                   "transaction": uuid.uuid4().hex, "created_utc": c.utc_now(), "status": "INCOMPLETE",
                   "originals_untouched": True}
        manifest = symbols / JOURNAL
        # The private record and public INCOMPLETE marker precede every payload copy.
        for folder in (destination, symbols):
            folder.mkdir(parents=True, exist_ok=True)
        # Exclusive creation outside recovery handling: never overwrite another owner's record.
        _new_json(manifest, seal(journal))
        try:
            _new_json(destination / MARKER, _marker(journal, "INCOMPLETE"))
            for number, entry in enumerate(journal["files"]):
                source = c.local_path(build, entry["path"])
                target = c.local_path(symbols if entry["location"] == "private_symbols" else destination, entry["path"])
                target.parent.mkdir(parents=True, exist_ok=True)
                partial = _part(target, journal)
                if target.exists() or partial.exists():
                    raise GuardError("An output file appeared during staging; no existing file will be overwritten.")
                if c.file_digest(source) != entry["sha256"]:
                    raise GuardError("Source build changed after staging preflight.")
                _copy(source, partial, op, number, journal["file_count"])
                if c.file_digest(partial) != entry["sha256"] or c.file_digest(source) != entry["sha256"]:
                    raise GuardError("Source/copy SHA256 mismatch.")
                # Hard-link commit fails if target appeared, including on POSIX where rename replaces.
                # Both names are on the same filesystem; no copy is silently overwritten.
                os.link(partial, target)
                partial.unlink()
            op.step("verifying staged inventory", 0, journal["file_count"])
            expected_sources = {f["path"] for f in journal["files"]}
            if {p.relative_to(build).as_posix() for p in c.walk_files(build)} != expected_sources:
                raise GuardError("Source inventory changed while staging.")
            for entry in journal["files"]:
                target = c.local_path(symbols if entry["location"] == "private_symbols" else destination, entry["path"])
                if c.file_digest(target) != entry["sha256"] or c.file_digest(c.local_path(build, entry["path"])) != entry["sha256"]:
                    raise GuardError("Final staging verification failed.")
            expected_outputs = {manifest, destination / MARKER} | {
                c.local_path(symbols if f["location"] == "private_symbols" else destination, f["path"])
                for f in journal["files"]}
            if set(c.walk_files(destination)) | set(c.walk_files(symbols)) != expected_outputs:
                raise GuardError("Unexpected files appeared in stage output; preserve them for manual review.")
            op.step("ready to finalize stage", journal["file_count"], journal["file_count"])
            # From here cancellation is disabled: finish both records before presenting completion.
            op.step("finalizing stage (cannot cancel)", journal["file_count"], journal["file_count"], cancellable=False)
            _new_json(symbols / SYMBOL_MANIFEST, {"schema": 2, "created_utc": journal["created_utc"],
                                                   "files": journal["files"], "originals_untouched": True})
            journal["status"] = "COMPLETE"
            c.write_json(manifest, seal(journal))
            c.write_json(destination / MARKER, _marker(journal, "COMPLETE"))
        except BaseException as error:
            # Initial marker remains INCOMPLETE even if ENOSPC prevents recording the error.
            journal["status"] = "INCOMPLETE"
            try:
                c.write_json(manifest, seal(journal))
            except (OSError, GuardError):
                pass
            from .operations import Cancelled
            kind = Cancelled if isinstance(error, (Cancelled, KeyboardInterrupt)) else GuardError
            raise kind(f"Stage INCOMPLETE ({type(error).__name__}). Original build preserved. Use stage-cleanup with the private journal: {manifest}") from None
        return journal


def _is_prefix(partial, source, sha256):
    if c.file_digest(source) != sha256 or partial.stat().st_size > source.stat().st_size:
        return False
    with partial.open("rb") as left, source.open("rb") as right:
        while True:
            block = left.read(1024 * 1024)
            if not block:
                return True
            if block != right.read(len(block)):
                return False


def cleanup_preview(manifest):
    manifest = _root(manifest)
    journal = load_journal(manifest, "stage")
    try:
        build, release, symbols = (_root(journal[k]) for k in ("build", "release", "symbols"))
        _disjoint([build, release, symbols])
        if manifest != symbols / JOURNAL or not re.fullmatch(r"[0-9a-f]{32}", journal["transaction"]):
            raise ValueError
        if journal["status"] not in {"INCOMPLETE", "COMPLETE", "CLEANING", "CLEANED"}:
            raise ValueError
        marker_path = release / MARKER
        if marker_path.exists():
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            if marker == _marker(journal, "COMPLETE"):
                raise GuardError("A completed release cannot be cleaned by stage-cleanup.")
            if marker != _marker(journal, "INCOMPLETE"):
                raise ValueError
        elif journal["status"] == "COMPLETE":
            raise GuardError("Missing completion marker; preserve this ambiguous output for manual inspection.")
        targets, allowed = [], {manifest, marker_path, symbols / SYMBOL_MANIFEST}
        seen = set()
        for entry in journal["files"]:
            if entry["location"] not in {"private_symbols", "release"} or not re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]):
                raise ValueError
            target = c.local_path(symbols if entry["location"] == "private_symbols" else release, entry["path"])
            if str(target).casefold() in seen or target in allowed:
                raise ValueError
            seen.add(str(target).casefold())
            partial = _part(target, journal)
            allowed.update((target, partial))
            if target.exists():
                if c.file_digest(target) != entry["sha256"]:
                    raise GuardError("Cleanup conflict: a copied file was modified. No files removed.")
                targets.append(target)
            if partial.exists():
                if not _is_prefix(partial, c.local_path(build, entry["path"]), entry["sha256"]):
                    raise GuardError("Cleanup cannot verify a partial copy. No files removed.")
                targets.append(partial)
        if (symbols / SYMBOL_MANIFEST).exists():
            saved = json.loads((symbols / SYMBOL_MANIFEST).read_text(encoding="utf-8"))
            if saved != {"schema": 2, "created_utc": journal["created_utc"], "files": journal["files"], "originals_untouched": True}:
                raise GuardError("Private symbol manifest changed. No files removed.")
            targets.append(symbols / SYMBOL_MANIFEST)
        for folder in (release, symbols):
            if folder.exists() and any(path not in allowed for path in c.walk_files(folder)):
                raise GuardError("Cleanup found unrecognized output files. Preserve them; no files removed.")
        return journal, targets
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise GuardError("Invalid stage recovery record/marker; no files removed.") from None


def cleanup_stage(manifest, *, operation=None, expected_integrity=None):
    op = operation or Operation()
    with writer():
        op.step("verifying cleanup")
        journal, targets = cleanup_preview(manifest)
        if expected_integrity is not None and journal["integrity_sha256"] != expected_integrity:
            raise GuardError("Stage journal changed after preview. Review cleanup again.")
        if journal["status"] == "CLEANED":
            return {"status": "CLEANED", "removed": 0, "journal": str(manifest)}
        fingerprints = {path: c.file_digest(path) for path in targets}
        op.step("ready to clean failed copies", 0, len(targets))
        journal["status"] = "CLEANING"
        c.write_json(Path(manifest), seal(journal))
        # Keep the INCOMPLETE marker until all copied payload is removed, including after a crash.
        for number, path in enumerate(targets):
            op.step("cleaning failed copies (cannot cancel)", number, len(targets), cancellable=False)
            if c.linked(path) or c.file_digest(path) != fingerprints[path]:
                raise GuardError("Cleanup conflict during removal; remaining copies and journal preserved.")
            path.unlink()
        release = Path(journal["release"])
        # Never recursively delete directories; remove only empty parents of our known payload paths.
        directories = set()
        for path in targets:
            stop = Path(journal["symbols"]) if path.is_relative_to(Path(journal["symbols"])) else release
            parent = path.parent
            while parent != stop:
                directories.add(parent)
                parent = parent.parent
        for directory in sorted(directories, key=lambda p: len(p.parts), reverse=True):
            if directory.exists() and not any(directory.iterdir()):
                directory.rmdir()
        marker = release / MARKER
        remaining = set(c.walk_files(release)) | set(c.walk_files(Path(journal["symbols"])))
        if remaining - {c.absolute_path(manifest), marker}:
            raise GuardError("New output files appeared during cleanup; preserved for manual review.")
        if marker.exists():
            if json.loads(marker.read_text(encoding="utf-8")) != _marker(journal, "INCOMPLETE"):
                raise GuardError("Stage marker changed during cleanup; preserved for manual inspection.")
            marker.unlink()
        journal["status"] = "CLEANED"
        c.write_json(Path(manifest), seal(journal))
        return {"status": "CLEANED", "removed": len(targets), "journal": str(manifest)}
