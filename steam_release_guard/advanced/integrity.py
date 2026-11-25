"""SHA256 release snapshots with an externally pinned manifest and build ID.

This detects changes against a trusted baseline; it is not anti-cheat, DRM or
an authenticated signature. Never ban players or delete files from this result.
"""
from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path

from .. import core as c
from ..operations import GuardError, Operation, check_space, writer
from ..project_backup import safe_path, relative_name
from .common import read_json, shape


def build_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", value):
        raise GuardError("Use a nonempty, bounded build ID (letters, digits, dot, dash, underscore).")
    return value


def patterns(values):
    if not isinstance(values, list) or len(values) > 100:
        raise GuardError("Invalid mutable-path list.")
    for value in values:
        relative_name(value)
        if value in {"*", "**"} or not any(char.isalnum() for char in value):
            raise GuardError("A whole-build mutable pattern would disable integrity checking.")
    return values


def inventory(build, mutable, *, operation=None):
    build = safe_path(build)
    if not build.is_dir():
        raise GuardError("Build directory is missing.")
    op = operation or Operation()
    files, ignored, seen = [], [], set()
    for path in sorted(c.walk_files(build)):
        op.check_cancel()
        name = relative_name(path.relative_to(build).as_posix())
        if name.casefold() in seen:
            raise GuardError("Case-colliding release paths are not portable.")
        seen.add(name.casefold())
        if any(fnmatch.fnmatchcase(name.casefold(), p.casefold()) for p in mutable):
            ignored.append(name)
            continue
        before = path.stat()
        checksum = c.file_digest(path)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
            raise GuardError("Build changed during hashing; stop the game/updater and retry.")
        files.append({"path": name, "bytes": before.st_size, "sha256": checksum})
    if not files:
        raise GuardError("No immutable build files selected.")
    return files, ignored


def create_preview(build, identifier, output, mutable=(), *, operation=None):
    identifier = build_id(identifier)
    mutable = patterns(list(mutable))
    build, output = safe_path(build), safe_path(output)
    if output.is_relative_to(build) or output == build or output.exists():
        raise GuardError("Manifest output must be a new file OUTSIDE the build.")
    files, ignored = inventory(build, mutable, operation=operation)
    return {"build_id": identifier, "output": str(output), "files": files,
            "mutable": mutable, "ignored": ignored, "authentication": "External manifest hash required; SHA256 is not a signature."}


def create(build, identifier, output, mutable=(), *, operation=None, expected_preview=None):
    with writer():
        preview = create_preview(build, identifier, output, mutable, operation=operation)
        if expected_preview is not None and preview != expected_preview:
            raise GuardError("Build changed after manifest preview.")
        second, _ = inventory(build, preview["mutable"], operation=operation)
        if second != preview["files"]:
            raise GuardError("Build changed during manifest creation.")
        manifest = {"schema": 1, "algorithm": "SHA256", "build_id": identifier,
                    "created_utc": c.utc_now(), "files": preview["files"], "mutable": preview["mutable"]}
        data = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        if len(data) > 64 * 1024 * 1024:
            raise GuardError("Manifest exceeds the supported 64 MiB limit; use smaller release/depot scopes.")
        target = safe_path(output)
        check_space([(target.parent, len(data))])
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as handle:
            handle.write(data)
            handle.flush()
            __import__("os").fsync(handle.fileno())
        return {"status": "CREATED", "build_id": identifier, "manifest": str(target),
                "manifest_sha256": c.file_digest(target), "file_count": len(manifest["files"]),
                "runtime": "NOT_VERIFIED", "instruction": "Pin this manifest hash outside the client (trusted CI/release record/server). Do not trust a hash stored beside replaceable files."}


def load_pinned(path, expected_hash, identifier):
    build_id(identifier)
    path = safe_path(path)
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash):
        raise GuardError("An externally trusted manifest SHA256 is required.")
    if c.file_digest(path) != expected_hash.lower():
        raise GuardError("Manifest hash does not match the trusted pin; no baseline trusted.")
    manifest = read_json(path, max_bytes=64 * 1024 * 1024)
    if c.file_digest(path) != expected_hash.lower():
        raise GuardError("Manifest changed during verification.")
    shape(manifest, {"schema", "algorithm", "build_id", "created_utc", "files", "mutable"})
    if manifest["schema"] != 1 or manifest["algorithm"] != "SHA256" or manifest["build_id"] != identifier:
        raise GuardError("Manifest schema/algorithm/build ID mismatch; updates require a new trusted baseline.")
    patterns(manifest["mutable"])
    if not isinstance(manifest["files"], list) or not manifest["files"]:
        raise GuardError("Invalid/empty release manifest.")
    seen = set()
    for item in manifest["files"]:
        shape(item, {"path", "bytes", "sha256"})
        name = relative_name(item["path"])
        if (name.casefold() in seen or type(item["bytes"]) is not int or item["bytes"] < 0
                or not isinstance(item["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
                or any(fnmatch.fnmatchcase(name.casefold(), p.casefold()) for p in manifest["mutable"])):
            raise GuardError("Invalid, duplicate or mutable entry in immutable manifest.")
        seen.add(name.casefold())
    return manifest


def verify(build, manifest_path, identifier, expected_hash, *, operation=None):
    manifest = load_pinned(manifest_path, expected_hash, identifier)
    actual, ignored = inventory(build, manifest["mutable"], operation=operation)
    expected = {f["path"]: f for f in manifest["files"]}
    current = {f["path"]: f for f in actual}
    missing = sorted(set(expected) - set(current))
    unexpected = sorted(set(current) - set(expected))
    changed = sorted(p for p in expected.keys() & current.keys() if expected[p] != current[p])
    matched = not (missing or unexpected or changed)
    return {"status": "INTEGRITY_MATCH" if matched else "INTEGRITY_MISMATCH", "build_id": identifier,
            "manifest_sha256": expected_hash.lower(), "missing": missing, "unexpected": unexpected,
            "changed": changed, "mutable_files_not_checked": ignored,
            "runtime": "NOT_VERIFIED", "protection": "NOT_VERIFIED",
            "scope": "File bytes/inventory only. Client checks can be patched; trust the manifest pin independently.",
            "action": "No action required for this file check." if matched else
                      "Pause this check during authorized updates. Offer Steam file verification/repair; preserve saves/mods; never delete files, auto-ban or accuse the player."}


def drm_inspect(original, wrapped, expected_original_hash):
    from .binary import pe_info
    original, wrapped = safe_path(original), safe_path(wrapped)
    if original == wrapped or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_original_hash):
        raise GuardError("Keep distinct original/wrapped executables and the original pre-wrapper SHA256.")
    if c.file_digest(original) != expected_original_hash.lower():
        raise GuardError("Original executable changed since the pre-wrapper checkpoint.")
    before, after = pe_info(original), pe_info(wrapped)
    changed = c.file_digest(original) != c.file_digest(wrapped)
    return {"status": "REVIEW" if changed else "NOT_VERIFIED", "original_preserved": True,
            "wrapped_pe_structure": "VALID", "bytes_changed": changed, "machine_matches": before["machine"] == after["machine"],
            "wrapped_sha256": c.file_digest(wrapped), "wrapper_success": "NOT_VERIFIED",
            "steam_launch": "NOT_VERIFIED", "offline_launch": "NOT_VERIFIED", "test_branch_reinstall": "NOT_VERIFIED",
            "scope": "PE structure/hash comparison does not prove Steam wrapping. Inspect authorized wrapper log and the actual Steam test branch. No executable run or upload occurred."}
