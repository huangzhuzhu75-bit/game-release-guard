"""Bounded PE/CLI structure inspection. Never load or execute inspected modules."""
from __future__ import annotations

import re
import struct

from .. import core as c
from ..operations import GuardError
from ..project_backup import safe_path, disjoint
from .common import finding, result


def pe_info(path):
    path = safe_path(path)
    size = path.stat().st_size
    with path.open("rb") as handle:
        def at(offset, length):
            if offset < 0 or length < 0 or length > 65536 or offset + length > size:
                raise GuardError("Malformed/truncated PE bounds.")
            handle.seek(offset)
            value = handle.read(length)
            if len(value) != length:
                raise GuardError("Binary changed during inspection.")
            return value

        def u16(offset):
            return struct.unpack("<H", at(offset, 2))[0]

        def u32(offset):
            return struct.unpack("<I", at(offset, 4))[0]

        if at(0, 2) != b"MZ":
            raise GuardError("Not a PE executable.")
        pe = u32(0x3c)
        if at(pe, 4) != b"PE\0\0":
            raise GuardError("Invalid PE signature.")
        machine, sections = u16(pe + 4), u16(pe + 6)
        optional_size, optional = u16(pe + 20), pe + 24
        if not 1 <= sections <= 96 or optional_size < 96:
            raise GuardError("Invalid PE section/optional header count.")
        magic = u16(optional)
        if magic not in (0x10b, 0x20b):
            raise GuardError("Unsupported PE optional header.")
        data_offset = 96 if magic == 0x10b else 112
        if optional_size < data_offset:
            raise GuardError("Truncated optional header.")
        count = u32(optional + data_offset - 4)
        if count > (optional_size - data_offset) // 8:
            raise GuardError("Invalid PE data directory count.")
        directories = [struct.unpack("<II", at(optional + data_offset + n * 8, 8)) for n in range(min(count, 16))]
        table = []
        for n in range(sections):
            pos = optional + optional_size + n * 40
            header = at(pos, 40)
            virtual_size, rva, raw_size, raw_pos = struct.unpack_from("<IIII", header, 8)
            if raw_size and raw_pos + raw_size > size:
                raise GuardError("PE section extends beyond file.")
            table.append((rva, raw_pos, raw_size))

        def locate(rva, length):
            for start, raw, length_raw in table:
                if start <= rva and rva + length <= start + length_raw:
                    return raw + rva - start
            raise GuardError("PE directory has no backed section.")

        def directory(index):
            return directories[index] if index < len(directories) else (0, 0)

        def string(rva):
            value = bytearray()
            for n in range(256):
                byte = at(locate(rva + n, 1), 1)
                if byte == b"\0":
                    try:
                        return value.decode("ascii")
                    except UnicodeError:
                        raise GuardError("Non-ASCII PE import name.") from None
                value += byte
            raise GuardError("Unterminated PE import name.")

        cli, cli_size = directory(14)
        managed = bool(cli)
        if managed:
            if cli_size < 0x48:
                raise GuardError("Truncated CLR header.")
            cli_pos = locate(cli, 0x48)
            metadata, metadata_size = struct.unpack("<II", at(cli_pos + 8, 8))
            if metadata_size < 16 or at(locate(metadata, 16), 4) != b"BSJB":
                raise GuardError("Invalid CLR metadata signature.")
        imports, imports_size = directory(1)
        dependencies = []
        if imports:
            for n in range(min(imports_size // 20, 4096)):
                descriptor = at(locate(imports + n * 20, 20), 20)
                if descriptor == bytes(20):
                    break
                name = string(struct.unpack_from("<I", descriptor, 12)[0])
                if not re.fullmatch(r"[A-Za-z0-9_.+-]{1,255}", name):
                    raise GuardError("Invalid PE import basename.")
                dependencies.append(name)
            else:
                raise GuardError("Unterminated/oversized PE import table.")
        exports, export_size = directory(0)
        export_names = u32(locate(exports, 40) + 24) if exports and export_size >= 40 else 0
        debug_rva, debug_size = directory(6)
        return {"machine": hex(machine), "format": "PE32+" if magic == 0x20b else "PE32",
                "managed": managed, "dependencies": sorted(set(dependencies)), "export_name_count": export_names,
                "debug_directory_present": bool(debug_rva and debug_size), "bytes": size}


def literal_candidates(path):
    """Search ASCII key assignments and private key headers without emitting values."""
    patterns = [("PRIVATE_KEY_HEADER", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
                ("SECRET_ASSIGNMENT", re.compile(rb"(?i)(?:api[_-]?key|client[_-]?secret|password|access[_-]?token)\s*[:=]\s*[\"']?[A-Za-z0-9_+/=-]{8,}"))]
    matches, offset, carry = [], 0, b""
    with safe_path(path).open("rb") as handle:
        while True:
            block = handle.read(65536)
            if not block:
                break
            text = carry + block
            for rule, pattern in patterns:
                for match in pattern.finditer(text):
                    matches.append({"rule": rule, "byte_offset": offset - len(carry) + match.start()})
            # Explicitly document ASCII coverage; UTF16/encoded/runtime secrets need manual review.
            offset += len(block)
            carry = text[-512:]
            if len(matches) >= 100:
                break
    return list({(m["rule"], m["byte_offset"]): m for m in matches}.values())[:100]


def unity_audit(project, build):
    if project.engine != "unity":
        raise GuardError("Unity metadata inspection requires a Unity project.")
    build = safe_path(build)
    disjoint(project.root, build)
    if not build.is_dir():
        raise GuardError("Packaged build directory is missing.")
    paths = list(c.walk_files(build))
    findings = [finding("METADATA_PROTECTOR", "configuration", "NOT_VERIFIED",
                        "No metadata encryption provider approved for this exact Unity version. Engine/loader patches are not performed.")]
    for path in paths:
        name = path.relative_to(build).as_posix()
        if path.suffix.lower() in {".exe", ".dll"}:
            try:
                info = pe_info(path)
            except GuardError:
                findings.append(finding("PE_STRUCTURE", "artifact", "FAIL", "Invalid/truncated executable or DLL; do not delete dependencies to hide it.", [name]))
                continue
            findings.append(finding("MANAGED_MODULE" if info["managed"] else "NATIVE_MODULE", "artifact", "REVIEW",
                                    "Managed code exposes IL; native code remains reversible. Import names are dependencies, not a deletion list.",
                                    [{"path": name, "sha256": c.file_digest(path), **info}]))
            candidates = literal_candidates(path)
            if candidates:
                findings.append(finding("BINARY_SECRET_CANDIDATE", "artifact", "REVIEW", "Potential sensitive literals; confirm locally, never copy values to reports.",
                                        [{"path": name, **m} for m in candidates]))
        if path.name.lower() == "global-metadata.dat":
            with path.open("rb") as handle:
                header = handle.read(8)
            plain = len(header) == 8 and header[:4] == b"\xaf\x1b\xb1\xfa"
            findings.append(finding("IL2CPP_METADATA", "artifact", "REVIEW" if plain else "NOT_VERIFIED",
                                    "Standard metadata header visible; metadata is not encrypted." if plain else
                                    "Unknown/missing metadata header is not proof of encryption; it may be corrupted or a different layout.",
                                    [{"path": name, "sha256": c.file_digest(path), "header_version": struct.unpack("<I", header[4:])[0] if plain else None}]))
        if c.private_symbol(path.relative_to(build)):
            findings.append(finding("PRIVATE_SYMBOL", "artifact", "FAIL", "Separate debug symbols into private storage using stage; retain crash diagnostics.", [name]))
    if not any(p.name.lower() == "global-metadata.dat" for p in paths):
        findings.append(finding("IL2CPP_METADATA", "artifact", "NOT_VERIFIED", "Metadata file not found. Absence does not establish protection."))
    findings.append(finding("NATIVE_RUNTIME", "runtime", "NOT_VERIFIED", "Verify plugin loads, saves, reflection, RPC and exact distributed game. No modules modified. UTF16/encoded/runtime secrets need separate review."))
    return result(project.engine, project.version, findings)
