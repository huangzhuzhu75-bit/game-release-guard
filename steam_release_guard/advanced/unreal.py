"""UE CryptoKeys policy and separate official Pak / IoStore inspection."""
from __future__ import annotations

import base64
import binascii
import fnmatch
import re
from pathlib import Path

from .. import core as c, transactions
from ..operations import GuardError, writer
from ..project_backup import safe_path, disjoint, relative_name
from .common import ProtectionAdapter, changes, finding, new_output, private_run, read_json, result, shape

FLAGS = {"index": "bEncryptPakIndex", "ini": "bEncryptPakIniFiles", "uasset": "bEncryptUAssetFiles",
         "all_assets": "bEncryptAllAssetFiles", "signing": "bEnablePakSigning"}


def version_matches(project, exact):
    return bool(re.fullmatch(r"5\.[0-6](?:\.\d+)?", exact)) and (exact == project.version or exact.startswith(project.version + "."))


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
    shape(config, {"schema", "engine_version", "pak", "iostore", "assets"})
    if project.engine != "unreal" or config["schema"] != 1 or not version_matches(project, config["engine_version"]):
        raise GuardError("Reviewed UE 5.0–5.6 settings profile must match the project version; other versions need review.")
    shape(config["pak"], FLAGS)
    if type(config["iostore"]) is not bool or any(type(v) is not bool for v in config["pak"].values()):
        raise GuardError("Each Pak/IoStore option must be an explicit boolean.")
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
        if tool_path is None:
            return {"status": "MISSING", "reason": "Provide the exact UE installation root; nothing is installed automatically."}
        root = safe_path(tool_path)
        version_file = root / "Engine/Build/Build.version"
        if not version_file.is_file():
            raise GuardError("Engine/Build/Build.version not found in the selected UE installation.")
        data = read_json(version_file)
        try:
            version = ".".join(str(data[k]) for k in ("MajorVersion", "MinorVersion", "PatchVersion"))
        except (KeyError, TypeError):
            raise GuardError("Invalid UE Build.version.") from None
        if not version_matches(project, version):
            raise GuardError("UE tool installation version does not match the reviewed project profile.")
        tool = root / "Engine/Binaries/Win64/UnrealPak.exe"
        if not tool.is_file():
            raise GuardError("Matching official UnrealPak.exe is missing; do not substitute an unreviewed external unpacker.")
        return {"status": "DETECTED", "version": version, "tool": str(safe_path(tool)), "tool_sha256": c.file_digest(tool),
                "version_file_sha256": c.file_digest(version_file), "runtime": "NOT_VERIFIED"}

    def plan(self, project, config):
        validate(project, config)
        # Reuse only baseline .gitignore. Compose each INI once to avoid duplicate targets.
        values = [(x.path, x.data, x.purpose) for x in c.plan(project) if x.path == ".gitignore"]
        game = c.patch_ini(c.read_optional(project.root, "Config/DefaultGame.ini"), c.PACKAGING,
                           {"BuildConfiguration": "PPBC_Shipping", "IncludeDebugFiles": "False", "UsePakFile": "True",
                            "bUseIoStore": str(config["iostore"])})
        crypto = c.patch_ini(c.read_optional(project.root, "Config/DefaultCrypto.ini"), c.CRYPTO,
                             {FLAGS[k]: str(v) for k, v in config["pak"].items()})
        values += [("Config/DefaultGame.ini", game, "Shipping packaging; explicit IoStore choice"),
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


def verify(project, engine_root, build, evidence_dir, crypto_json=None, *, operation=None):
    with writer():
        preview = verify_preview(project, engine_root, build, evidence_dir, crypto_json)
        evidence = new_output(evidence_dir, project.root, build, engine_root, create=True)
        tool = preview["install"]["tool"]
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
        findings, checks = [], []
        # Store initial status before invoking even the help command.
        record = {**preview, "status": "INCOMPLETE", "checks": checks}
        c.write_json(evidence / "verification.json", record)
        help_dir = evidence / "help"
        help_dir.mkdir()
        private_run([tool, "-Help"], help_dir, secrets=secrets, operation=operation)
        help_text = (help_dir / "tool.log").read_text(encoding="utf-8").lower()
        for item in preview["files"]:
            path = c.local_path(Path(preview["build"]), item["path"])
            suffix = path.suffix.lower()
            if suffix not in {".pak", ".utoc"}:
                continue
            kind = "PAK" if suffix == ".pak" else "IOSTORE"
            commands = ["-Test", "-List"] if suffix == ".pak" else ["-Info", "-List"]
            for command in commands:
                if command.lower() not in help_text:
                    findings.append(finding(kind + "_TOOL_SYNTAX", "artifact", "NOT_VERIFIED", "Matching tool help does not advertise this check; inspect this version's official documentation.", [item["path"], command]))
                    continue
                private = evidence / (str(len(checks)) + "-" + kind.lower())
                private.mkdir()
                argv = [tool, str(path), command]
                if crypto_json:
                    argv.append("-cryptokeys=" + str(safe_path(crypto_json)))
                before = c.file_digest(path)
                run = private_run(argv, private, secrets=secrets, operation=operation)
                checks.append({"container": item["path"], "command": command, **run})
                if before != item["sha256"] or c.file_digest(path) != before:
                    raise GuardError("Container changed during verification; evidence invalid.")
                findings.append(finding(kind + "_OFFICIAL_CHECK", "artifact", "REVIEW" if run["exit_code"] == 0 else "FAIL",
                                        "Official tool completed; inspect contents/encryption/signing evidence in the private log. Exit zero alone does not prove protection."
                                        if run["exit_code"] == 0 else "Official container check failed; wrong keys, corruption or unsupported arguments require investigation.",
                                        [item["path"], command, {"log_sha256": run["log_sha256"]}]))
        for item in preview["files"]:
            if c.file_digest(c.local_path(Path(preview["build"]), item["path"])) != item["sha256"]:
                raise GuardError("Container/partition/signature changed during verification.")
        findings += [finding("PAK_ENCRYPTION_SIGNING", "artifact", "NOT_VERIFIED", "Review index/content flags and verify signing with trusted key in this UE version; a .sig file or settings alone is not proof."),
                     finding("IOSTORE_ENCRYPTION_SIGNING", "artifact", "NOT_VERIFIED", "Separate TOC/data encryption, signing and chunk integrity proof required; Pak index result is not transferable."),
                     finding("CONTAINER_RUNTIME", "runtime", "NOT_VERIFIED", "Test actual resource loads, DLC, patches, saves, offline startup and performance.")]
        record.update(status="FAIL" if any(f["status"] == "FAIL" for f in findings) else "REVIEW", findings=findings)
        c.write_json(evidence / "verification.json", record)
        return record
