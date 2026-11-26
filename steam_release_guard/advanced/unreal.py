"""UE CryptoKeys policy and separate official Pak / IoStore inspection."""
from __future__ import annotations

import base64
import binascii
import fnmatch
import re
from pathlib import Path

from .. import core as c, transactions
from ..operations import Cancelled, GuardError, writer
from ..project_backup import safe_path, disjoint, relative_name
from .common import ProtectionAdapter, changes, finding, new_output, private_run, read_json, shape

FLAGS = {"index": "bEncryptPakIndex", "ini": "bEncryptPakIniFiles", "uasset": "bEncryptUAssetFiles",
         "all_assets": "bEncryptAllAssetFiles", "signing": "bEnablePakSigning"}
CONTAINERS = {"pak-only": (True, False), "iostore-only": (False, True), "pak+iostore": (True, True)}


def version_matches(project, exact):
    return isinstance(exact, str) and bool(re.fullmatch(r"5\.[0-6](?:\.\d+)?", exact)) and (exact == project.version or exact.startswith(project.version + "."))


def signing_shape(values):
    """Encoding/nonzero checks only. UE must validate actual RSA material/signatures."""
    for name in ("signingmodulus", "signingprivateexponent", "signingpublicexponent"):
        raw = values.get(name, "").strip().strip('"')
        try:
            data = bytes.fromhex(raw[2:]) if raw.startswith("0x") else base64.b64decode(raw, validate=True)
        except (ValueError, binascii.Error):
            raise GuardError("Existing signing material has an unsupported encoding; validate it in the exact UE Editor.") from None
        if not data or len(data) > 1024 or not any(data):
            raise GuardError("Existing signing material is missing, zero or malformed; no keys are generated.")


def validate(project, config):
    if isinstance(config, dict) and config.get("schema") == 1:
        raise GuardError("UE policy schema 1 does not explicitly select Pak. Review and migrate to schema 2 with container_policy: pak-only, iostore-only or pak+iostore; no automatic conversion or changes.")
    shape(config, {"schema", "engine_version", "pak", "container_policy", "assets"})
    if project.engine != "unreal" or type(config["schema"]) is not int or config["schema"] != 2 or not version_matches(project, config["engine_version"]):
        raise GuardError("Reviewed UE 5.0–5.6 settings profile must match the project version; other versions need review.")
    shape(config["pak"], FLAGS)
    if not isinstance(config["container_policy"], str) or config["container_policy"] not in CONTAINERS:
        raise GuardError("Explicitly select container_policy: pak-only, iostore-only or pak+iostore.")
    if config["container_policy"] == "iostore-only":
        raise GuardError("IoStore-only is NOT_VERIFIED for this Windows/UAT profile. Official Zen Loader staging also uses companion Pak files; no validated standalone combination is available. No files changed and Pak will not be enabled automatically.")
    if any(type(v) is not bool for v in config["pak"].values()):
        raise GuardError("Each CryptoKeys option must be an explicit boolean.")
    crypto_bytes = c.read_optional(project.root, "Config/DefaultCrypto.ini")
    crypto = c.ini_values(crypto_bytes, c.CRYPTO)
    if any(config["pak"][k] for k in ("index", "ini", "uasset", "all_assets")) and not c.valid_crypto_key(crypto_bytes):
        raise GuardError("Encryption requires an existing valid nonzero 32-byte AES key; no key changes are made.")
    if config["pak"]["signing"]:
        signing_shape(crypto)
    rules = config["assets"]
    if not isinstance(rules, list) or len(rules) > 1000:
        raise GuardError("Invalid resource classification list.")
    for rule in rules:
        shape(rule, {"path", "grade", "loading"})
        relative_name(rule["path"])
        if not rule["path"].startswith("Content/") or rule["grade"] not in {"A", "B", "C"} or rule["loading"] not in {"startup", "streamed", "dlc", "public"}:
            raise GuardError("Asset rules require Content/... paths, A/B/C grade and a documented loading mode.")
    return config


class UnrealAdapter(ProtectionAdapter):
    def detect(self, project, tool_path=None):
        # IoStoreUtilities is an official Developer module hosted by UnrealPak,
        # not a documented standalone IoStoreUtilities.exe. Detect entry points
        # independently; module help must confirm capabilities before execution.
        tools = {"pak": {"module": "PakFileUtilities", "prefix": []},
                 "iostore": {"module": "IoStoreUtilities", "prefix": ["IoStore"]}}
        record = {"status": "NOT_VERIFIED", "tools": tools, "runtime": "NOT_VERIFIED"}
        def unavailable(reason):
            for entry in tools.values():
                entry.update(status="NOT_VERIFIED", reason=reason)
            record["reason"] = reason
            return record
        if tool_path is None:
            return unavailable("Provide the exact UE installation root; nothing is installed automatically.")
        root = safe_path(tool_path)
        version_file = root / "Engine/Build/Build.version"
        if not version_file.is_file():
            return unavailable("Engine/Build/Build.version is missing; neither tool version can be established.")
        try:
            data = read_json(version_file)
            numbers = [data[k] for k in ("MajorVersion", "MinorVersion", "PatchVersion")]
            if any(type(n) is not int or n < 0 for n in numbers):
                return unavailable("Invalid UE Build.version components.")
        except (GuardError, KeyError, TypeError):
            return unavailable("Cannot establish the tool version from Build.version.")
        version = ".".join(map(str, numbers))
        record.update(version=version, version_file_sha256=c.file_digest(version_file))
        if project.engine != "unreal" or not version_matches(project, version):
            return unavailable("UE installation version is unsupported or does not match the project; no tools executed.")
        tool = root / "Engine/Binaries/Win64/UnrealPak.exe"
        if not tool.is_file():
            return unavailable("Matching official UnrealPak host is missing. A DLL or undocumented IoStoreUtilities.exe is not a verified CLI substitute.")
        for entry in tools.values():
            entry.update(status="DETECTED", executable=str(safe_path(tool)), tool_sha256=c.file_digest(tool),
                         version=version, capability="NOT_VERIFIED")
        # Only the 5.6 keyword-list/CSV interface has been reviewed here.
        if numbers[:2] != [5, 6]:
            tools["iostore"].update(status="NOT_VERIFIED", reason="IoStoreUtilities command profile is reviewed for UE 5.6 only; this version needs its own documentation/help review.")
        record["status"] = "DETECTED"
        return record

    def plan(self, project, config):
        validate(project, config)
        # Reuse only baseline .gitignore. Compose each INI once to avoid duplicate targets.
        values = [(x.path, x.data, x.purpose) for x in c.plan(project) if x.path == ".gitignore"]
        pak, iostore = CONTAINERS[config["container_policy"]]
        game = c.patch_ini(c.read_optional(project.root, "Config/DefaultGame.ini"), c.PACKAGING,
                           {"BuildConfiguration": "PPBC_Shipping", "IncludeDebugFiles": "False", "UsePakFile": str(pak),
                            "bUseIoStore": str(iostore)})
        crypto = c.patch_ini(c.read_optional(project.root, "Config/DefaultCrypto.ini"), c.CRYPTO,
                             {FLAGS[k]: str(v) for k, v in config["pak"].items()})
        values += [("Config/DefaultGame.ini", game, "Shipping packaging; explicit " + config["container_policy"] + " choice"),
                   ("Config/DefaultCrypto.ini", crypto, "Independent CryptoKeys switches; preserve existing key bytes/values")]
        return changes(project, values)


def apply(project, config, **kwargs):
    return transactions.apply(project, planner=lambda: UnrealAdapter().plan(project, config), **kwargs)


def asset_plan(project, config):
    validate(project, config)
    rows = []
    content = c.local_path(project.root, "Content")
    for path in c.walk_files(content) if content.is_dir() else []:
        name = path.relative_to(project.root).as_posix()
        matched = [r for r in config["assets"] if fnmatch.fnmatchcase(name, r["path"])]
        if len(matched) != 1:
            rows.append({"path": name, "status": "REVIEW", "reason": "No rule" if not matched else "Ambiguous rules"})
            continue
        rule = matched[0]
        advice = {"A": "Use an explicitly reviewed chunk/container and existing key; verify actual assets and DLC dependencies.",
                  "B": "Measure loading/patch cost before selecting content encryption.",
                  "C": "Keep required public/direct-load content usable; encryption may offer little benefit."}[rule["grade"]]
        rows.append({"path": name, "grade": rule["grade"], "loading": rule["loading"], "status": "REVIEW", "advice": advice})
    return {"resources": rows, "status": "REVIEW", "scope": "Classification only. No chunks, secondary keys, AssetManager rules or content files are changed.",
            "all_asset_encryption": config["pak"]["all_assets"],
            "tradeoff": "All-asset encryption is a global switch, not per-grade protection. Benchmark startup, memory, loading, patch size and DLC."}


def verify_preview(project, engine_root, build, evidence_dir, crypto_json=None):
    install = UnrealAdapter().detect(project, engine_root)
    build = safe_path(build)
    disjoint(project.root, build)
    if not build.is_dir():
        raise GuardError("Packaged build directory is missing.")
    files = list(c.walk_files(build))
    containers = [p for p in files if p.suffix.lower() in {".pak", ".utoc"}]
    if not containers:
        raise GuardError("No Pak or IoStore TOC found; configuration alone is not evidence.")
    for path in containers:
        if path.suffix.lower() == ".utoc" and not path.with_suffix(".ucas").is_file():
            raise GuardError("IoStore TOC has no corresponding .ucas; preserve the incomplete build.")
    if crypto_json:
        crypto_json = safe_path(crypto_json)
        if crypto_json.is_relative_to(build):
            raise GuardError("Crypto.json must remain outside the distributed build.")
        read_json(crypto_json)
    evidence = new_output(evidence_dir, project.root, build, Path(engine_root))
    selected = [p for p in files if p.suffix.lower() in {".pak", ".utoc", ".ucas", ".sig"}]
    return {"install": install, "build": str(build), "evidence": str(evidence),
            "files": [{"path": p.relative_to(build).as_posix(), "sha256": c.file_digest(p), "bytes": p.stat().st_size} for p in selected],
            "crypto_reference": str(crypto_json) if crypto_json else None,
            "runtime": "NOT_VERIFIED", "protection": "NOT_VERIFIED",
            "scope": "Official read/test commands on actual containers; logs are private. No extraction, packaging or key changes."}


def _supports(help_text, flag, *, value=False):
    suffix = r"\s*=" if value else r"(?![A-Za-z0-9_-])"
    return re.search(r"(?<![A-Za-z0-9_-])" + re.escape(flag) + suffix, help_text, re.IGNORECASE) is not None


def _verify_group(kind, entry, items, build, folder, crypto_json, secrets, operation):
    group = {"kind": kind, "module": entry["module"], "status": "NOT_VERIFIED", "checks": [],
             "entrypoint": entry, "protection": "NOT_VERIFIED", "runtime": "NOT_VERIFIED"}
    if not items:
        group.update(status="NOT_REQUESTED", reason="No containers of this kind in the selected build.")
        return group
    if entry["status"] != "DETECTED":
        group["reason"] = entry["reason"]
        return group
    tool, prefix = entry["executable"], entry["prefix"]
    help_dir = folder / "help"
    help_dir.mkdir()
    try:
        group["help"] = private_run([tool, *prefix, "-Help"], help_dir, secrets=secrets, operation=operation)
    except Cancelled:
        raise
    except (GuardError, OSError):
        group.update(status="FAIL", reason="Tool help could not execute; preserve its private log.")
        return group
    if group["help"]["exit_code"] != 0:
        group["reason"] = "This entry point did not accept its help request; command compatibility is NOT_VERIFIED."
        return group
    help_text = (help_dir / "tool.log").read_text(encoding="utf-8")
    if kind == "iostore" and (not re.search(r"\bIoStore(?:Utilities)?\b", help_text, re.IGNORECASE)
                              or not _supports(help_text, "-List", value=True)
                              or not _supports(help_text, "-Csv", value=True)):
        group["reason"] = "IoStoreUtilities must independently advertise IoStore, -List=<container> and -Csv=<output>; Pak help cannot establish this interface."
        return group
    commands = ("-Test", "-List") if kind == "pak" else ("-List",)
    for item in items:
        path = c.local_path(build, item["path"])
        for command in commands:
            check = {"container": item["path"], "module": entry["module"], "command": command,
                     "status": "NOT_VERIFIED", "tool_sha256": entry["tool_sha256"]}
            group["checks"].append(check)
            if (kind == "pak" and not _supports(help_text, command)) or (crypto_json and not _supports(help_text, "-CryptoKeys", value=True)):
                check["reason"] = "Required argument is absent from this entry point's help; no container command executed."
                continue
            private = folder / str(len(group["checks"]))
            private.mkdir()
            listing = private / "contents.csv"
            argv = ([tool, str(path), command] if kind == "pak" else
                    [tool, *prefix, "-List=" + str(path), "-Csv=" + str(listing)])
            if crypto_json:
                argv.append("-CryptoKeys=" + str(safe_path(crypto_json)))
            if c.file_digest(path) != item["sha256"]:
                raise GuardError("Container changed before verification; evidence invalid.")
            try:
                execution = private_run(argv, private, secrets=secrets, operation=operation)
                check.update(execution, status="REVIEW" if execution["exit_code"] == 0 else "FAIL")
                if kind == "iostore" and execution["exit_code"] == 0:
                    listing = safe_path(listing)
                    if not listing.is_file() or not listing.stat().st_size:
                        check.update(status="NOT_VERIFIED", reason="IoStoreUtilities returned zero without the requested listing; no artifact result established.")
                    else:
                        check.update(listing=str(listing), listing_sha256=c.file_digest(listing))
            except Cancelled:
                raise
            except (GuardError, OSError):
                check.update(status="FAIL", reason="Container tool failed; preserve the private log and original container.")
            if c.file_digest(path) != item["sha256"]:
                raise GuardError("Container changed during verification; evidence invalid.")
    statuses = {row["status"] for row in group["checks"]}
    group["status"] = "FAIL" if "FAIL" in statuses else "NOT_VERIFIED" if "NOT_VERIFIED" in statuses else "REVIEW"
    group["scope"] = "This container type only. Exit zero/listing is not encryption or signature proof."
    return group


def verify(project, engine_root, build, evidence_dir, crypto_json=None, *, operation=None):
    with writer():
        preview = verify_preview(project, engine_root, build, evidence_dir, crypto_json)
        evidence = new_output(evidence_dir, project.root, build, engine_root, create=True)
        secrets = []
        if crypto_json:
            def collect(value):
                if isinstance(value, dict):
                    for v in value.values(): collect(v)
                elif isinstance(value, list):
                    for v in value: collect(v)
                elif isinstance(value, str) and len(value) >= 8:
                    secrets.append(value)
            collect(read_json(crypto_json))
        findings, checks, groups = [], [], {}
        # Store initial status before invoking even the help command.
        record = {**preview, "status": "INCOMPLETE", "checks": checks, "groups": groups}
        c.write_json(evidence / "verification.json", record)
        for kind, suffix in (("pak", ".pak"), ("iostore", ".utoc")):
            folder = evidence / kind
            folder.mkdir()
            c.write_json(folder / "verification.json", {"kind": kind, "status": "INCOMPLETE"})
            items = [x for x in preview["files"] if Path(x["path"]).suffix.lower() == suffix]
            group = _verify_group(kind, preview["install"]["tools"][kind], items,
                                  Path(preview["build"]), folder, crypto_json, secrets, operation)
            groups[kind] = group
            checks.extend(group["checks"])
            c.write_json(folder / "verification.json", group)
            if items:
                findings.append(finding(kind.upper() + "_OFFICIAL_CHECK", "artifact", group["status"],
                                        group.get("reason", group.get("scope", "Review this container type's private tool records.")),
                                        [x["path"] for x in items]))
        for item in preview["files"]:
            if c.file_digest(c.local_path(Path(preview["build"]), item["path"])) != item["sha256"]:
                raise GuardError("Container/partition/signature changed during verification.")
        if UnrealAdapter().detect(project, engine_root) != preview["install"]:
            raise GuardError("UE tool installation/version changed during verification; evidence invalid.")
        findings += [finding("PAK_ENCRYPTION_SIGNING", "artifact", "NOT_VERIFIED", "Review index/content flags and verify signing with trusted key in this UE version; a .sig file or settings alone is not proof."),
                     finding("IOSTORE_ENCRYPTION_SIGNING", "artifact", "NOT_VERIFIED", "Separate TOC/data encryption, signing and chunk integrity proof required; Pak index result is not transferable."),
                     finding("CONTAINER_RUNTIME", "runtime", "NOT_VERIFIED", "Test actual resource loads, DLC, patches, saves, offline startup and performance.")]
        statuses = {group["status"] for group in groups.values()}
        record.update(status="FAIL" if "FAIL" in statuses else "NOT_VERIFIED" if "NOT_VERIFIED" in statuses else "REVIEW", findings=findings)
        c.write_json(evidence / "verification.json", record)
        return record
