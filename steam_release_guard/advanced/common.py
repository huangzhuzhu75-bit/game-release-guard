"""Shared local adapter contracts, strict input and private tool execution."""
from __future__ import annotations

import json
import os
import re
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path

from .. import core as c
from ..operations import GuardError, Operation, check_space
from ..project_backup import safe_path, disjoint, relative_name


class ProtectionAdapter(ABC):
    """Tools are optional. Detection must never install or execute them."""
    @abstractmethod
    def detect(self, project, tool_path=None):
        raise NotImplementedError

    @abstractmethod
    def plan(self, project, config):
        raise NotImplementedError


def read_json(path):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result
    try:
        path = safe_path(path)
        if path.stat().st_size > 4 * 1024 * 1024:
            raise ValueError("oversized config")
        return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
    except (OSError, ValueError, UnicodeError):
        raise GuardError("Cannot read a bounded, valid JSON document (duplicate keys are forbidden).") from None


def shape(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise GuardError("Configuration has missing or unknown fields; use the documented schema.")


def names(values, *, patterns=False, empty=False):
    if not isinstance(values, list) or (not values and not empty) or len(values) > 1000:
        raise GuardError("Expected a bounded list of explicit names.")
    regex = r"[A-Za-z_][A-Za-z0-9_.`/+-]*(?:\*)?" if patterns else r"[A-Za-z_][A-Za-z0-9_.`/+-]*"
    if any(not isinstance(v, str) or len(v) > 256 or not re.fullmatch(regex, v) for v in values):
        raise GuardError("Use explicit type/assembly names; exclusions may end in a wildcard.")
    if len(set(v.casefold() for v in values)) != len(values):
        raise GuardError("Duplicate names are not allowed.")
    return values


def changes(project, values):
    # Preserve P0's version and incomplete-full-restore preflight.
    from ..project_backup import restored_roots
    c.require_supported(project)
    restored_roots(project.root)
    result, seen = [], set()
    for name, data, purpose in values:
        relative_name(name)
        target = c.local_path(project.root, name)
        if name.casefold() in seen or target.is_relative_to(project.root / c.STATE):
            raise GuardError("Duplicate/private transaction target.")
        seen.add(name.casefold())
        before = target.read_bytes() if target.exists() else None
        if before != data:
            result.append(c.Change(name, data, purpose, c.digest(before) if before is not None else None))
    return result


def new_output(value, *inputs, create=False, bytes_needed=0):
    folder = safe_path(value)
    for source in inputs:
        disjoint(safe_path(source), folder)
    if folder.exists():
        raise GuardError("Choose a NEW private output directory; existing paths are never reused.")
    check_space([(folder, bytes_needed)])
    if create:
        folder.mkdir(parents=True, exist_ok=False)
        (folder / ".gitignore").write_bytes(b"*\n")
    return folder


def private_run(argv, folder, *, timeout=600, secrets=(), operation=None, cwd=None):
    """No shell. Explicit local executable; bounded/redacted log, hidden Windows window.

    This is not a sandbox for third party code. Only run a trusted, reviewed tool.
    Do not pass secrets in argv. Their local reference files are read by the tool.
    """
    executable = safe_path(argv[0])
    if not executable.is_file() or (os.name == "nt" and executable.suffix.lower() != ".exe"):
        raise GuardError("An installed executable is required; shell scripts are not accepted.")
    if not 1 <= timeout <= 86400:
        raise GuardError("Tool timeout must be between 1 and 86400 seconds.")
    op = operation or Operation()
    log = folder / "tool.log"
    spool = folder / "tool-output.private"
    started = time.monotonic()
    # File-backed output avoids an unbounded in-memory PIPE or pipe deadlock.
    process = None
    try:
        with spool.open("xb") as output:
            process = subprocess.Popen(list(map(str, argv)), cwd=cwd, stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=subprocess.STDOUT, shell=False,
                                       creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            while process.poll() is None:
                op.check_cancel()
                if time.monotonic() - started > timeout or spool.stat().st_size > 16 * 1024 * 1024:
                    raise GuardError("Tool exceeded time/log limit; partial output retained, no protection approved.")
                time.sleep(.1)
        code = process.returncode
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        if spool.exists():
            raw = spool.read_bytes()[:16 * 1024 * 1024].decode("utf-8", errors="replace")
            for value in sorted((v for v in secrets if v), key=len, reverse=True):
                raw = raw.replace(value, "[REDACTED]")
            raw = re.sub(r"(?im)((?:key|secret|password|token|exponent|modulus)\s*[:=]\s*)[^\r\n]+", r"\1[REDACTED]", raw)
            with log.open("xb") as handle:
                handle.write(raw.encode("utf-8"))
            spool.unlink()  # Only our own bounded temporary log; no game file deletion.
    return {"exit_code": code, "log": str(log), "log_sha256": c.file_digest(log),
            "tool_sha256": c.file_digest(executable), "elapsed_seconds": round(time.monotonic() - started, 3)}


def result(engine, version, findings):
    return {"schema": 1, "engine": engine, "engine_version": version,
            "release_status": "BLOCKED" if any(f["status"] == "FAIL" for f in findings) else "REQUIRES_MANUAL_REVIEW",
            "findings": findings}


def finding(identifier, layer, status, detail, evidence=()):
    if layer not in {"configuration", "artifact", "runtime"} or status not in {"PASS", "FAIL", "REVIEW", "NOT_VERIFIED"}:
        raise ValueError("Invalid evidence classification")
    return {"id": identifier, "layer": layer, "status": status, "detail": detail, "evidence": list(evidence)}
