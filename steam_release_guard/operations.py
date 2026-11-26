"""Local cooperative locking, progress and safe error presentation (stdlib only)."""
from __future__ import annotations

import errno
import functools
import hashlib
import json
import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path


class GuardError(Exception):
    """A safe, actionable message; never include configuration contents."""


class Cancelled(GuardError):
    pass


class Operation:
    def __init__(self, progress=None):
        self.cancel = threading.Event()
        self.progress = progress or (lambda event: None)
        self.cancellable = True

    def step(self, phase, current=0, total=1, *, cancellable=True):
        self.cancellable = cancellable
        self.check_cancel()
        self.progress({"phase": phase, "current": current, "total": total, "cancellable": cancellable})

    def check_cancel(self):
        if self.cancellable and self.cancel.is_set():
            raise Cancelled("Operation cancelled; originals preserved. Inspect any recovery journal before retrying.")


def safe_error(error):
    if isinstance(error, GuardError):
        return str(error)
    if isinstance(error, OSError):
        if error.errno == errno.ENOSPC:
            return "Insufficient disk space. Preserve recovery records, free space, then retry recovery."
        if isinstance(error, PermissionError):
            return "File access denied or file in use. Close the editor and check permissions before retrying."
        return "Filesystem operation failed. Check paths, free space and recovery records."
    if isinstance(error, (ValueError, UnicodeError)):
        return "Invalid data or encoding. Check the input and recovery record; no secret values are logged."
    return f"Unexpected {type(error).__name__}. Preserve recovery records; operation did not complete."


_held = threading.local()


@contextmanager
def _file_lock(path):
    from .core import linked
    if any(linked(p) for p in (path, *path.parents)):
        raise GuardError("Lock path must not contain symlinks or junctions.")
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+b")
    acquired = False
    try:
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            acquired = True
        except OSError:
            raise GuardError("Another write task holds the operation lock. Wait for it to finish; do not delete lock files.") from None
        yield
    finally:
        try:
            if acquired:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            handle.close()


@contextmanager
def writer(project=None):
    """Serialize this host's writers, including legacy stage calls without a project.

    Keep lock files forever: unlinking a locked inode would allow a second lock.
    OS locks are released when the owning process exits. Thread-local reentrancy
    allows apply + report to share one outer operation, but not two GUI workers.
    """
    lock_root = Path(os.environ.get("SRG_LOCK_DIRECTORY", Path(tempfile.gettempdir()) / "steam-release-guard-locks"))
    paths = [lock_root / "writer.lock"]
    if project is not None:
        from .core import STATE, local_path
        paths.append(local_path(project.root, f"{STATE}/operation.lock"))

    @contextmanager
    def enter(index):
        if index == len(paths):
            yield
            return
        key = str(paths[index].absolute())
        held = getattr(_held, "paths", set())
        _held.paths = held
        if key in held:
            with enter(index + 1):
                yield
        else:
            with _file_lock(paths[index]):
                held.add(key)
                try:
                    with enter(index + 1):
                        yield
                finally:
                    held.remove(key)
    with enter(0):
        yield


def serialized(function):
    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        with writer():
            return function(*args, **kwargs)
    return wrapped


def check_space(requirements):
    """Group estimates by filesystem; reserve metadata space. Still handle ENOSPC."""
    volumes = {}
    for destination, size in requirements:
        existing = Path(destination)
        while not existing.exists():
            existing = existing.parent
        device = existing.stat().st_dev
        previous, needed = volumes.get(device, (existing, 0))
        volumes[device] = (previous, needed + size)
    for path, needed in volumes.values():
        if shutil.disk_usage(path).free < needed + 2 * 1024 * 1024:
            raise GuardError("Insufficient disk space for verified copies and recovery records; no payload files changed.")


def seal(journal):
    payload = {k: v for k, v in journal.items() if k != "integrity_sha256"}
    journal["integrity_sha256"] = hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return journal


def load_journal(path, operation, *, allow_legacy=False):
    try:
        journal = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(journal, dict) or not isinstance(journal.get("files"), list):
            raise ValueError
        if journal.get("schema") == 1 and allow_legacy:
            if any(key in journal for key in ("integrity_sha256", "operation", "file_count")):
                raise ValueError  # A damaged schema 2 record must not silently downgrade.
            return journal
        if journal.get("schema") != 2 or journal.get("operation") != operation:
            raise ValueError
        expected = journal.get("integrity_sha256")
        if seal(dict(journal))["integrity_sha256"] != expected:
            raise ValueError
        if type(journal.get("file_count")) is not int or journal["file_count"] != len(journal["files"]) or not journal["files"]:
            raise ValueError
        return journal
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise GuardError("Transaction journal integrity/schema check failed. Preserve it for manual recovery.") from None
