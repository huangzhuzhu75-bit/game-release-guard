"""Dependency-free project adapters, transactional changes and release inspection."""
from __future__ import annotations

import base64
import hashlib
import html
import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import __version__

STATE = ".steam-release-guard"
PACKAGING = "/Script/UnrealEd.ProjectPackagingSettings"
CRYPTO = "/Script/CryptoKeys.CryptoKeysSettings"
UNITY_ADAPTER = "Assets/SteamReleaseGuard/Editor/SteamReleaseGuardBuild.cs"
REPO = Path(__file__).resolve().parent.parent
SYMBOL_EXTENSIONS = {".pdb", ".mdb", ".debug", ".sym"}
RAW_EXTENSIONS = {
    ".wav", ".ogg", ".mp3", ".flac", ".aiff", ".fbx", ".obj", ".blend", ".gltf",
    ".glb", ".png", ".jpg", ".jpeg", ".tga", ".psd", ".exr", ".tif", ".dds",
}
SOURCE_EXTENSIONS = {".cs", ".cpp", ".c", ".h", ".hpp", ".py", ".lua"}
SOURCE_RULES = {
    "debug-menu": re.compile(r"\b(debugmenu|devmenu|debugconsole|devconsole)\b", re.I),
    "cheat-command": re.compile(r"\b(godmode|noclip|enablecheats|skip_level|levelskip|skipLevel)\b", re.I),
    "shipping-override": re.compile(r"\b(ALLOW_CONSOLE_IN_SHIPPING|bUseLoggingInShipping|bUseChecksInShipping)\b"),
    "unreal-exec": re.compile(r"UFUNCTION\s*\(\s*Exec\b|\bConsoleKeys\s*=", re.I),
}


class GuardError(Exception):
    """An actionable input, compatibility or recovery error."""


@dataclass(frozen=True)
class Project:
    root: Path
    engine: str
    version: str
    descriptor: Path


@dataclass(frozen=True)
class Change:
    path: str
    data: bytes
    purpose: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def linked(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def local_path(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or any(p in {"..", "."} for p in rel.parts):
        raise GuardError(f"Unsafe relative path: {relative}")
    current = root
    for part in rel.parts:
        current = current / part
        if linked(current):
            raise GuardError(f"Refusing a symlink/junction: {relative}")
    if not current.resolve().is_relative_to(root.resolve()):
        raise GuardError(f"Path escapes project: {relative}")
    return current


def detect_project(value: str | Path) -> Project:
    candidate = Path(value).expanduser().resolve()
    chosen = candidate if candidate.suffix.lower() == ".uproject" and candidate.is_file() else None
    root = chosen.parent if chosen else candidate
    if not root.is_dir():
        raise GuardError("Select an existing project root or .uproject file.")
    unity = root / "ProjectSettings/ProjectVersion.txt"
    unreal = [chosen] if chosen else list(root.glob("*.uproject"))
    if unity.is_file() and unreal:
        raise GuardError("Both engines found. Select a single engine project root.")
    if unity.is_file() and (root / "Assets").is_dir():
        match = re.search(r"m_EditorVersion:\s*(\S+)", unity.read_text(encoding="utf-8-sig"))
        return Project(root, "unity", match.group(1) if match else "unknown", unity)
    if len(unreal) != 1:
        raise GuardError("Expected one Unity project or one .uproject; choose the .uproject explicitly if needed.")
    data = json.loads(unreal[0].read_text(encoding="utf-8-sig"))
    return Project(root, "unreal", str(data.get("EngineAssociation", "unknown")), unreal[0])


def require_supported(project: Project) -> None:
    if project.engine == "unity" and not project.version.startswith("6000."):
        raise GuardError("This adapter targets Unity 6 (6000.x). Other versions are audit-only.")
    if project.engine == "unreal" and not re.match(r"^5\.\d+(?:\.\d+)?$", project.version):
        raise GuardError("This adapter targets UE 5.x. A custom/GUID engine association needs manual version review.")


def decode_config(data: bytes) -> tuple[str, str]:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16"), "utf-16"
    encoding = "utf-8-sig" if data.startswith(b"\xef\xbb\xbf") else "utf-8"
    return data.decode(encoding), encoding


def ini_values(data: bytes, section: str) -> dict[str, str]:
    text, _ = decode_config(data)
    current = ""
    values = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped[1:-1].casefold()
        elif current == section.casefold() and "=" in stripped and not stripped.startswith((";", "#")):
            key, value = stripped.split("=", 1)
            values[key.strip().casefold()] = value.strip()
    return values


def patch_ini(data: bytes, section: str, changes: dict[str, str]) -> bytes:
    """Preserve unrelated settings/comments/newlines, including repeated UE array entries."""
    text, encoding = decode_config(data)
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.splitlines(keepends=True)
    current = ""
    found_section = False
    seen = set()
    end_of_section = len(lines)
    replacements = {key.casefold(): (key, value) for key, value in changes.items()}
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if current == section.casefold():
                end_of_section = i
            current = stripped[1:-1].casefold()
            if current == section.casefold():
                found_section = True
                end_of_section = len(lines)
        elif current == section.casefold() and "=" in stripped and not stripped.startswith((";", "#")):
            key = stripped.split("=", 1)[0].strip().casefold()
            if key in replacements:
                original, value = replacements[key]
                lines[i] = f"{original}={value}{newline}"
                seen.add(key)
    missing = [f"{key}={value}{newline}" for lower, (key, value) in replacements.items() if lower not in seen]
    if not found_section:
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] += newline
        lines.extend([newline, f"[{section}]{newline}"] + missing)
    elif missing:
        if end_of_section and not lines[end_of_section - 1].endswith(("\n", "\r")):
            lines[end_of_section - 1] += newline
        lines[end_of_section:end_of_section] = missing
    return "".join(lines).encode(encoding)


def read_optional(root: Path, relative: str) -> bytes:
    path = local_path(root, relative)
    return path.read_bytes() if path.is_file() else b""


def valid_crypto_key(data: bytes) -> bool:
    value = ini_values(data, CRYPTO).get("encryptionkey", "").strip('"')
    try:
        key = base64.b64decode(value, validate=True)
        return len(key) == 32 and any(key)
    except ValueError:
        return False


def plan(project: Project, encrypt_index: bool = False) -> list[Change]:
    require_supported(project)
    changes = []
    ignore_data = read_optional(project.root, ".gitignore")
    ignore_text, ignore_encoding = decode_config(ignore_data)
    if f"/{STATE}/" not in ignore_text.splitlines() and f"{STATE}/" not in ignore_text.splitlines():
        newline = "\r\n" if "\r\n" in ignore_text else "\n"
        updated = ignore_text + (newline if ignore_text and not ignore_text.endswith("\n") else "")
        updated += f"# Local release reports, backups and logs; may contain private project data{newline}/{STATE}/{newline}"
        changes.append(Change(".gitignore", updated.encode(ignore_encoding), "Exclude private local state from Git"))
    if project.engine == "unity":
        if encrypt_index:
            raise GuardError("Pak-index encryption is an Unreal option, not a Unity asset encryption feature.")
        changes.append(Change(UNITY_ADAPTER, (REPO / "adapters/unity/SteamReleaseGuardBuild.cs").read_bytes(),
                              "Install the Unity 6 Windows IL2CPP release builder"))
        changes.append(Change("Assets/SteamReleaseGuard/Editor/SteamReleaseGuard.Editor.asmdef",
                              (REPO / "adapters/unity/SteamReleaseGuard.Editor.asmdef").read_bytes(),
                              "Keep the build adapter Editor-only"))
    else:
        game = "Config/DefaultGame.ini"
        changes.append(Change(game, patch_ini(read_optional(project.root, game), PACKAGING, {
            "BuildConfiguration": "PPBC_Shipping", "IncludeDebugFiles": "False",
        }), "Set Shipping and exclude debug files from the staged build"))
        if encrypt_index:
            crypto_path = "Config/DefaultCrypto.ini"
            crypto = read_optional(project.root, crypto_path)
            if not valid_crypto_key(crypto):
                raise GuardError("Generate a nonzero 256-bit key in Unreal Project Settings > Encryption first. No changes applied.")
            changes.append(Change(game, patch_ini(changes[-1].data, PACKAGING, {"UsePakFile": "True"}),
                                  "Use Pak packaging; preserve the existing IoStore setting"))
            changes.append(Change(crypto_path, patch_ini(crypto, CRYPTO, {"bEncryptPakIndex": "True"}),
                                  "Encrypt the Pak index using the existing key; not asset contents"))
    unique = {change.path: change for change in changes}
    return [change for change in unique.values() if read_optional(project.root, change.path) != change.data]


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".srg-" + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def write_json(path: Path, value: dict) -> None:
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def apply(project: Project, encrypt_index: bool = False) -> Path | None:
    changes = plan(project, encrypt_index)
    if not changes:
        return None
    transaction_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid.uuid4().hex[:8]
    folder = local_path(project.root, f"{STATE}/backups/{transaction_id}")
    atomic_write(local_path(project.root, f"{STATE}/.gitignore"), b"*\n")
    entries = []
    # Prepare and verify ALL originals before touching a project file.
    for number, change in enumerate(changes):
        target = local_path(project.root, change.path)
        before = target.read_bytes() if target.exists() else None
        backup_name = f"{number:03d}.bak" if before is not None else None
        if before is not None:
            atomic_write(folder / backup_name, before)
            if file_digest(folder / backup_name) != digest(before):
                raise GuardError("Backup verification failed; project has not been changed.")
        entries.append({"path": change.path, "before_sha256": digest(before) if before is not None else None,
                        "after_sha256": digest(change.data), "backup": backup_name})
    journal = {"schema": 1, "root": str(project.root), "created_utc": utc_now(), "status": "prepared", "files": entries}
    manifest = folder / "manifest.json"
    write_json(manifest, journal)
    try:
        for change, entry in zip(changes, entries):
            target = local_path(project.root, change.path)
            actual = file_digest(target) if target.exists() else None
            if actual != entry["before_sha256"]:
                raise GuardError(f"File changed during planning: {change.path}")
            atomic_write(target, change.data)
            if file_digest(target) != entry["after_sha256"]:
                raise GuardError(f"Write verification failed: {change.path}")
        journal["status"] = "applied"
        write_json(manifest, journal)
    except (OSError, GuardError):
        # Keep the prepared journal for conflict-aware recovery; never hide a failed transaction.
        raise GuardError(f"Apply interrupted. Close the editor and run rollback. Recovery: {manifest}") from None
    return manifest


def rollback(project: Project) -> Path:
    backup_root = local_path(project.root, f"{STATE}/backups")
    if not backup_root.is_dir():
        raise GuardError("No release-guard backup exists for this project.")
    for folder in sorted(backup_root.iterdir(), reverse=True):
        manifest = local_path(project.root, str(folder.relative_to(project.root) / "manifest.json"))
        if not manifest.is_file():
            continue
        journal = json.loads(manifest.read_text(encoding="utf-8"))
        if journal.get("status") == "rolled_back":
            continue
        if journal.get("schema") != 1 or journal.get("root") != str(project.root):
            raise GuardError("Backup belongs to a different project or schema. No files restored.")
        prepared = []
        for entry in journal["files"]:
            target = local_path(project.root, entry["path"])
            current = file_digest(target) if target.exists() else None
            if current not in (entry["before_sha256"], entry["after_sha256"]):
                raise GuardError(f"Rollback conflict: {entry['path']} changed after adaptation. No files restored.")
            before = None
            if entry["before_sha256"] is not None:
                backup = local_path(folder, entry["backup"])
                before = backup.read_bytes()
                if digest(before) != entry["before_sha256"]:
                    raise GuardError("Backup integrity check failed. No files restored.")
            prepared.append((target, before))
        for target, before in reversed(prepared):
            if before is None:
                if target.exists():
                    target.unlink()
            else:
                atomic_write(target, before)
        journal["status"] = "rolled_back"
        journal["restored_utc"] = utc_now()
        write_json(manifest, journal)
        return manifest
    raise GuardError("All recorded changes have already been rolled back.")


def walk_files(root: Path, excluded: set[str] | None = None):
    """Never follow symlinks/junctions or silently ignore unreadable directories."""
    excluded = {item.casefold() for item in (excluded or set())}

    def on_error(error):
        raise GuardError(f"Cannot fully inspect directory: {error.filename}")

    for base, directories, filenames in os.walk(root, followlinks=False, onerror=on_error):
        directories.sort()
        filenames.sort()
        for directory in list(directories):
            if directory.casefold() in excluded:
                directories.remove(directory)
            elif linked(Path(base) / directory):
                raise GuardError("Inspection is incomplete: a directory is a symlink/junction.")
        for filename in filenames:
            path = Path(base) / filename
            if linked(path):
                raise GuardError("Inspection is incomplete: a file is a symlink.")
            yield path


def private_symbol(relative: Path) -> bool:
    return relative.suffix.lower() in SYMBOL_EXTENSIONS or any(
        part.lower().endswith(".dsym") or "_backupthisfolder_butdontshipitwithyourgame" in part.lower()
        or "_burstdebuginformation_donotship" in part.lower() for part in relative.parts)


def source_candidates(project: Project) -> list[dict]:
    roots = [project.root / "Assets"] if project.engine == "unity" else [project.root / p for p in ("Source", "Plugins", "Config")]
    results = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in walk_files(root, {".git", STATE, "Library", "Intermediate", "Binaries", "Editor", "node_modules"}):
            if path.suffix.lower() not in SOURCE_EXTENSIONS | {".ini"}:
                continue
            if path.stat().st_size > 2_000_000:
                results.append({"file": path.relative_to(project.root).as_posix(), "line": 0, "rule": "too-large-to-scan"})
                continue
            text = path.read_text(encoding="utf-8-sig", errors="replace")
            for number, line in enumerate(text.splitlines(), 1):
                for name, pattern in SOURCE_RULES.items():
                    if pattern.search(line):
                        # Do not put code, credentials or config values in reports.
                        results.append({"file": path.relative_to(project.root).as_posix(), "line": number, "rule": name})
    return results


def audit(project: Project, build: Path | None = None) -> dict:
    findings = []

    def add(rule, status, category, title, detail, evidence=None):
        findings.append({"id": rule, "status": status, "category": category, "title": title,
                         "detail": detail, "evidence": evidence or []})

    try:
        require_supported(project)
    except GuardError as error:
        add("ENGINE_VERSION", "review", "configuration", "Engine version needs review", str(error))
    if project.engine == "unity":
        add("UNITY_ADAPTER", "pass" if (project.root / UNITY_ADAPTER).is_file() else "review", "configuration",
            "Unity release adapter", "Installing the adapter does not change PlayerSettings or prove a release build. Use its Windows release build command.")
        settings = read_optional(project.root, "ProjectSettings/ProjectSettings.asset").decode("utf-8", errors="replace")
        match = re.search(r"(?m)^  scriptingBackend:\s*\r?\n((?:[ \t]+[^\r\n]*\r?\n)*)", settings)
        backend = re.search(r"(?m)^\s+Standalone:\s*(\d+)\s*$", match.group(1)) if match else None
        add("UNITY_BACKEND_CONFIG", "pass" if backend and backend.group(1) == "1" else "review", "code",
            "Global Standalone backend setting", "The global YAML hint is not build evidence; custom Build Profiles can override it. The adapter selects IL2CPP at build time and restores the previous settings.")
        add("UNITY_ASSET_LIMIT", "review", "assets", "Unity assets remain extractable",
            "IL2CPP changes code compilation, not asset encryption. AssetBundles/Addressables and compression are not encryption. Review shipped StreamingAssets and third-party plugins.")
    else:
        game = ini_values(read_optional(project.root, "Config/DefaultGame.ini"), PACKAGING)
        shipping = game.get("buildconfiguration", "").casefold() == "ppbc_shipping"
        debug_off = game.get("includedebugfiles", "").casefold() in {"false", "0"}
        add("UE_SHIPPING", "pass" if shipping else "fail", "configuration", "Shipping packaging configuration",
            "DefaultGame.ini requests Shipping." if shipping else "Set BuildConfiguration=PPBC_Shipping before distribution.")
        add("UE_DEBUG_FILES", "pass" if debug_off else "review", "debug", "Exclude packaged debug files",
            "IncludeDebugFiles=False is explicit; retain private symbols." if debug_off else "Set IncludeDebugFiles=False explicitly and inspect the staged output.")
        crypto = read_optional(project.root, "Config/DefaultCrypto.ini")
        values = ini_values(crypto, CRYPTO)
        encrypt = values.get("bencryptpakindex", "").casefold() in {"true", "1"}
        valid_key = valid_crypto_key(crypto)
        add("UE_PAK_INDEX", "fail" if encrypt and not valid_key else "review", "assets", "Pak-index encryption policy",
            "Enabled without a valid nonzero 256-bit key." if encrypt and not valid_key else
            ("Requested with a valid-length key. Verify packaged Pak behavior; this does not encrypt asset contents." if encrypt else "Optional index encryption is not enabled. Decide based on compatibility and protection needs."))
        if values.get("bencryptallassetfiles", "").casefold() in {"true", "1"}:
            add("UE_ALL_ASSETS", "review", "assets", "Full asset encryption is enabled",
                "Benchmark loading, patch size, DLC and updates with this setting. The tool never enables it automatically.")
        if game.get("buseiostore", "").casefold() in {"true", "1"}:
            add("UE_IOSTORE_CONFIG", "review", "assets", "IoStore is enabled",
                "Pak-index policy alone cannot establish protection of .utoc/.ucas containers; verify with this engine's tools.")
        config = project.root / "Config"
        overrides = []
        if config.is_dir():
            for path in walk_files(config):
                if path.suffix.lower() == ".ini" and path != config / "DefaultGame.ini":
                    values = ini_values(path.read_bytes(), PACKAGING)
                    if any(key in values for key in ("buildconfiguration", "includedebugfiles", "usepakfile", "buseiostore")):
                        overrides.append(path.relative_to(project.root).as_posix())
        if overrides:
            add("UE_CONFIG_LAYERS", "review", "configuration", "Other packaging config layers found",
                "Platform configuration, launch profiles and command-line flags can override defaults. Inspect the actual Shipping build.", overrides)
    candidates = source_candidates(project)
    if candidates:
        add("DEBUG_SOURCE_CANDIDATES", "warn", "debug", "Potential developer commands",
            "Heuristic matches only: comments and correctly guarded code can match. Binary plugins and Blueprints are not analyzed. Review each location and test the packaged game.", candidates)
    add("RUNTIME_DEBUG_REVIEW", "review", "debug", "Run the actual release build",
        "Try test menus, cheat consoles, level skipping and developer shortcuts. A clean text scan cannot establish their absence, including in Blueprints, scenes, prefabs and plugins.")
    inventory = {}
    if build is None:
        add("BUILD_REQUIRED", "review", "artifact", "No packaged build supplied", "Select the exact Steam depot content folder for post-build inspection.")
    else:
        build = build.expanduser().resolve()
        if not build.is_dir():
            raise GuardError("The packaged build folder does not exist.")
        if build == project.root or project.root.is_relative_to(build):
            raise GuardError("Select a packaged build folder, not the source project or its parent.")
        files = list(walk_files(build))
        relative = [path.relative_to(build) for path in files]
        names = [path.as_posix() for path in relative]
        inventory = {"file_count": len(files), "bytes": sum(path.stat().st_size for path in files)}
        exes = [p.as_posix() for p in relative if p.suffix.lower() == ".exe"]
        add("BUILD_EXECUTABLE", "pass" if exes else "fail", "artifact", "Windows executable inventory",
            "Executable presence is not proof the game starts or uses release flags.", exes)
        sensitive = [p.as_posix() for p in relative if p.name.lower() in {"steam_appid.txt", "defaultcrypto.ini", "crypto.json", ".env"}
                     or any(part.lower() in {".git", STATE} for part in p.parts)]
        if sensitive:
            add("PRIVATE_BUILD_FILES", "fail", "artifact", "Development/private files in the depot",
                "Remove these from the distribution staging folder after retaining any required private copies. No secret values are included in this report.", sensitive)
        symbols = [p.as_posix() for p in relative if private_symbol(p)]
        add("BUILD_SYMBOLS", "fail" if symbols else "pass", "debug", "Debug symbols and Unity debug folders",
            "Use stage to create separate release and private-symbol copies; never delete the originals." if symbols else "No known debug-symbol files or Unity do-not-ship folders were found.", symbols)
        raw = [p.as_posix() for p in relative if p.suffix.lower() in RAW_EXTENSIONS and not private_symbol(p)]
        if raw:
            add("LOOSE_ASSETS", "warn", "assets", "Directly accessible audio, models or textures",
                "These files can be copied directly. Some may be intentional (icons, mods, streaming audio); review rather than blindly remove or rename.", raw)
        source = [p.as_posix() for p in relative if p.suffix.lower() in SOURCE_EXTENSIONS and not private_symbol(p)]
        if source:
            add("SOURCE_IN_BUILD", "warn", "code", "Source/script files in the depot",
                "Review whether these are intentionally shipped scripts or accidental source. This tool does not obfuscate or rewrite them.", source)
        archives = [p.as_posix() for p in relative if p.suffix.lower() in {".pak", ".utoc", ".ucas", ".bundle", ".assets"}]
        add("ARCHIVE_REVIEW", "review", "assets", "Container extraction needs a separate test",
            "Archive names and extensions cannot prove encryption. Test your own build with version-matched engine tools; review index access and asset-content access separately.", archives)
        if any(p.suffix.lower() in {".utoc", ".ucas"} for p in relative):
            add("IOSTORE_ARTIFACT", "review", "assets", "IoStore containers detected",
                "No IoStore encryption verification is performed. A Pak index setting does not attest these containers.")
        if project.engine == "unity":
            managed = [p.as_posix() for p in relative if p.suffix.lower() == ".dll" and any(x.lower() == "managed" for x in p.parts)]
            native = any(p.name.lower() == "gameassembly.dll" for p in relative)
            metadata = any(p.name.lower() == "global-metadata.dat" for p in relative)
            add("UNITY_BUILD_CODE", "fail" if managed else ("pass" if native and metadata else "review"), "code",
                "Unity compiled-code indicators", "Managed DLLs remain readily inspectable." if managed else
                ("GameAssembly.dll and IL2CPP metadata are present. Native code and metadata can still be reverse engineered." if native and metadata else "Could not establish an IL2CPP layout. Check the actual build and adapter log."), managed)
            debug_boot = []
            for path in files:
                if path.name.lower() == "boot.config":
                    text = path.read_text(encoding="utf-8-sig", errors="replace")
                    if re.search(r"(?mi)^\s*(player-connection-debug|wait-for-managed-debugger|profiler-enable|development)\s*=\s*(1|true)\s*$", text):
                        debug_boot.append(path.relative_to(build).as_posix())
            if debug_boot:
                add("UNITY_DEBUG_BOOT", "fail", "debug", "Player debugging/profiling flags found",
                    "Rebuild with development, debugging and profiling disabled.", debug_boot)
        else:
            nonshipping = [p.as_posix() for p in relative if re.search(r"-(debug|debuggame|development|test)(?:\.|-)", p.name, re.I)]
            if nonshipping:
                add("UE_NONSHIPPING_BINARY", "fail", "debug", "Non-Shipping binary name found",
                    "Check the build configuration and actual executable. Renaming a binary is not a fix.", nonshipping)
            add("UE_BUILD_PROOF", "review", "configuration", "Verify the packaged configuration",
                "File names and project settings are not proof of the executable's configuration. Retain the UAT log/receipt showing Shipping and test runtime console behavior.")
    add("STEAM_DRM", "review", "steam", "Optional Steam DRM wrapper",
        "Wrapping uploads the executable to Valve. Use the separate opt-in script only with your Steamworks authorization, then reinstall from a test branch. It cannot prevent piracy.")
    add("PLAYER_COMPATIBILITY", "review", "runtime", "Compatibility and paying-player checks",
        "Retest plugins, old/new saves, multiplayer, offline startup, Steam restart behavior, controllers, loading time and patch size using the distributed build.")
    failed = sum(f["status"] == "fail" for f in findings)
    return {"schema": 1, "tool_version": __version__, "created_utc": utc_now(), "engine": project.engine,
            "engine_version": project.version, "project_name": project.root.name, "inventory": inventory,
            "automated_gate": "failed" if failed else "no_detected_blocker",
            "release_status": "BLOCKED" if failed else "REQUIRES_MANUAL_REVIEW", "findings": findings}


def validate_report_directory(directory: Path) -> Path:
    directory = directory.expanduser().resolve()
    if directory.exists():
        if not directory.is_dir():
            raise GuardError("Report output must be a directory.")
        marker = directory / ".srg-report-directory"
        if any(directory.iterdir()) and (not marker.is_file() or marker.read_bytes() != b"Steam Release Guard report v1\n"):
            raise GuardError("Report directory is not empty and was not created by this tool. Choose a new dedicated report directory.")
    return directory


def save_report(report: dict, directory: Path) -> Path:
    directory = validate_report_directory(directory)
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write(directory / ".srg-report-directory", b"Steam Release Guard report v1\n")
    atomic_write(directory / ".gitignore", b"*\n")
    write_json(directory / "report.json", report)
    cards = []
    for finding in report["findings"]:
        evidence = ""
        if finding["evidence"]:
            lines = [html.escape(item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)) for item in finding["evidence"]]
            evidence = "<details><summary>Evidence / 证据位置 (" + str(len(lines)) + ")</summary><pre>" + "\n".join(lines) + "</pre></details>"
        cards.append(f'<article class="{finding["status"]}"><span>{finding["status"].upper()}</span>'
                     f'<h2>{html.escape(finding["title"])}</h2><p>{html.escape(finding["detail"])}</p>{evidence}</article>')
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    page += '<title>Steam Release Guard report</title><style>body{font:16px/1.6 system-ui,sans-serif;background:#0e1420;color:#e7eef8;margin:0 auto;padding:40px 24px;max-width:1080px}h1{font-size:36px;margin-bottom:4px}header p{color:#abc0d6}article{background:#172235;border-left:4px solid #7194b5;border-radius:8px;padding:18px 24px;margin:16px 0}article.fail{border-color:#ff6868}article.warn{border-color:#eec05a}article.pass{border-color:#42cfa4}span{font-size:12px;letter-spacing:2px;color:#9dc6f0}h2{font-size:19px;margin:6px 0}p{margin:6px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}summary{cursor:pointer}footer{color:#abc0d6;margin-top:28px}</style><header><p>LOCAL RELEASE REVIEW / 本地发布检查</p><h1>Steam Release Guard</h1>'
    page += f'<p>{html.escape(report["project_name"])} · {html.escape(report["engine"])} {html.escape(report["engine_version"])}</p>'
    page += f'<h2>{html.escape(report["release_status"])}</h2><p>Configuration, artifact evidence and manual verification are separate. This is not a piracy-proof certificate.</p></header>'
    page += "".join(cards) + f'<footer>v{__version__} · {html.escape(report["created_utc"])} · No network requests; no source snippets or key values in this report.</footer></html>'
    atomic_write(directory / "report.html", page.encode("utf-8"))
    return directory / "report.html"


def stage_release(build: Path, destination: Path, symbols: Path) -> dict:
    paths = [p.expanduser().resolve() for p in (build, destination, symbols)]
    build, destination, symbols = paths
    if not build.is_dir():
        raise GuardError("Build folder does not exist.")
    for i, path in enumerate(paths):
        for other in paths[i + 1:]:
            if path == other or path.is_relative_to(other) or other.is_relative_to(path):
                raise GuardError("Build, release and private-symbol folders must be disjoint, not nested.")
    for folder in (destination, symbols):
        if folder.exists() and (not folder.is_dir() or any(folder.iterdir())):
            raise GuardError("Release and private-symbol folders must be new or empty. Existing builds are never overwritten.")
    files = list(walk_files(build))
    if not files:
        raise GuardError("Cannot stage an empty build.")
    entries = []
    for path in files:
        relative = path.relative_to(build)
        if any(part.casefold() in {".git", STATE} for part in relative.parts):
            raise GuardError("Build contains source-control/private-state data; select only packaged content.")
    for folder in (destination, symbols):
        folder.mkdir(parents=True, exist_ok=True)
    for path in files:
        relative = path.relative_to(build)
        private = private_symbol(relative)
        target = local_path(symbols if private else destination, relative.as_posix())
        target.parent.mkdir(parents=True, exist_ok=True)
        before = file_digest(path)
        shutil.copy2(path, target)
        if file_digest(target) != before or file_digest(path) != before:
            raise GuardError("Build changed during copy; staging is incomplete. Keep the original and rerun into new folders.")
        entries.append({"path": relative.as_posix(), "sha256": before, "location": "private_symbols" if private else "release"})
    manifest = {"schema": 1, "created_utc": utc_now(), "files": entries, "originals_untouched": True}
    write_json(symbols / "srg-symbol-manifest.json", manifest)
    return manifest


def powershell_literal(value: str) -> str:
    # Batch files ultimately use cmd.exe on Windows. Reject shell expansion characters there.
    if re.search(r'[\r\n"&|<>^%!]', value):
        raise GuardError("Build command paths must not contain shell metacharacters (including %, !, &, quotes or newlines).")
    return "'" + value.replace("'", "''") + "'"


def build_script(project: Project, tool: Path, output: Path) -> str:
    require_supported(project)
    tool, output = tool.expanduser().resolve(), output.expanduser().resolve()
    if not tool.is_file():
        raise GuardError("Choose the installed Unity.exe or Unreal Engine/Build/BatchFiles/RunUAT.bat.")
    if output == project.root or project.root.is_relative_to(output):
        raise GuardError("Build output cannot be the project root or its parent.")
    if project.engine == "unity":
        if not (project.root / UNITY_ADAPTER).is_file():
            raise GuardError("Apply the Unity adapter before generating a build script.")
        if tool.name.lower() != "unity.exe":
            raise GuardError("Select Unity.exe for the project's exact Editor version.")
        args = ["-batchmode", "-quit", "-projectPath", str(project.root), "-buildTarget", "Win64",
                "-executeMethod", "SteamReleaseGuard.Editor.ReleaseBuilder.BuildWindows",
                "-srgOutput", str(output / "Game.exe"), "-logFile", str(project.root / STATE / "unity-build.log")]
    else:
        if tool.name.lower() != "runuat.bat":
            raise GuardError("Select this UE version's Engine/Build/BatchFiles/RunUAT.bat.")
        args = ["BuildCookRun", f"-project={project.descriptor}", "-noP4", "-platform=Win64",
                "-clientconfig=Shipping", "-serverconfig=Shipping", "-build", "-cook", "-stage", "-pak", "-package",
                "-archive", f"-archivedirectory={output}", "-nodebuginfo", "-utf8output"]
        game = ini_values(read_optional(project.root, "Config/DefaultGame.ini"), PACKAGING)
        if game.get("buseiostore", "").casefold() in {"true", "1"}:
            args.append("-iostore")
    command = "& " + powershell_literal(str(tool)) + " " + " ".join(powershell_literal(arg) for arg in args)
    out = powershell_literal(str(output))
    return ("# Generated release build command. Review prerequisites and close the Editor first.\n"
            "$ErrorActionPreference = 'Stop'\n"
            f"$srgOutput = {out}\n"
            "if ((Test-Path -LiteralPath $srgOutput) -and (@(Get-ChildItem -LiteralPath $srgOutput -Force).Count -gt 0)) { throw 'Output must be empty; use a new version directory.' }\n"
            + command + "\nif ($LASTEXITCODE -ne 0) { throw \"Engine build failed: $LASTEXITCODE\" }\n"
            "Write-Host 'Engine command completed. Inspect the log, stage private symbols, and audit the exact depot folder.'\n")
