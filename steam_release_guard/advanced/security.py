"""Read-only, location-only client security triage, not semantic vulnerability proof."""
from __future__ import annotations

import re

from .. import core as c
from ..operations import Operation
from .common import finding, result

SKIP = {".git", c.STATE, "Library", "Temp", "Logs", "obj", "Obj", "Intermediate", "Saved",
        "Binaries", "node_modules", "Builds", "build", "dist", "__pycache__"}
TEXT = {".cs", ".cpp", ".cc", ".c", ".h", ".hpp", ".ini", ".json", ".yaml", ".yml", ".config", ".env", ".lua", ".js", ".ts"}
ECONOMY = r"(?:coins?|currency|wallet|balance|inventory|rewards?|trade|winner|score|rank|loot|damage)"
RULES = [
    ("HARDCODED_SECRET", re.compile(r'''(?i)\b(?:api[_-]?key|client[_-]?secret|password|access[_-]?token|private[_-]?key)\b["']?\s*[:=]\s*["'][^"'\r\n]{8,}["']'''),
     "Potential literal credential in client code/config.",
     "Confirm privately. Move privileged secrets to a server/secret store; revoke exposed credentials through the owner's approved process, never rotate automatically."),
    ("PRIVATE_KEY_MATERIAL", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
     "Private-key material marker in project text.",
     "Check whether it is a test fixture or production key. Keep production private keys out of the client and depot; do not copy values into chat/reports."),
    ("CLIENT_ECONOMY_WRITE", re.compile(r"(?i)\b" + ECONOMY + r"\w*\b[^\n]{0,80}(?:\+=|-=|(?<![=!<>])=(?!=)|\.Add\(|\.Remove\()"),
     "Potential client-side mutation of a valuable result.",
     "Trace the authoritative server path. Server should validate ownership, balance, prices, limits, replay/idempotency and atomic settlement; client sends intent, not final rewards."),
    ("LOCAL_CRITICAL_SAVE", re.compile(r'''(?i)PlayerPrefs\.Set(?:Int|Float|String)\s*\(\s*["'][^"']*''' + ECONOMY),
     "Important-looking game data stored in editable client preferences.",
     "Offline saves may be intentionally editable. Multiplayer economy/permissions must be checked against authoritative server state; encrypting PlayerPrefs does not establish authority."),
    ("CLIENT_PRIVILEGE", re.compile(r'''(?i)\b(?:isAdmin|adminRole|userRole|permissionLevel)\b\s*(?:=|\+=)|(?:role|permission)\s*=\s*["']admin["']'''),
     "Client-side permission/role assignment candidate.",
     "Server must derive permissions from the authenticated session and validate each privileged request; UI flags are not authorization."),
    ("NETWORK_MUTATION", re.compile(r"\b(?:ServerRpc|RequireOwnership|WithValidation)\b|UFUNCTION\s*\([^\n]*\bServer\b|\b(?:Request|Submit|Send)(?:Trade|Reward|Result|Purchase)\b"),
     "Network entry point or authority annotation needs semantic review.",
     "Inspect the matching server handler: identity, ownership, ranges, rate/replay checks and transaction consistency. An RPC/validation attribute alone is not proof; it may already be implemented correctly."),
    ("UNTRUSTED_DESERIALIZATION", re.compile(r"\bBinaryFormatter\b|TypeNameHandling\s*=\s*TypeNameHandling\.(?:All|Auto|Objects)"),
     "Deserialization mode can be risky with untrusted save/network data.",
     "Trace data provenance; prefer explicit bounded schemas and permitted types. Do not deserialize arbitrary client-supplied types on a server."),
    ("TLS_VALIDATION_BYPASS", re.compile(r"ServerCertificateValidationCallback[^\n]*(?:=>\s*true|return\s+true)|ValidateCertificate[^\n]*=>\s*true"),
     "Possible certificate-validation bypass.",
     "Restore normal certificate checks for release; inspect multi-line implementations and platform-specific transport settings separately."),
    ("RELEASE_DEBUG_ENTRY", re.compile(r"(?i)\b(?:DebugMenu|GodMode|SkipLevel|CheatConsole|EnableCheats)\b|UFUNCTION\s*\([^\n]*\bExec\b"),
     "Potential development/cheat entry point.",
     "Verify compile-time guards and the actual Shipping/non-development build; Editor-only source is not proof of a shipped debug feature."),
]
SERVER_HINT = re.compile(r"\b(?:IsServer|HasAuthority|WithValidation|RequireOwnership|_Validate)\b|\[Server\]")
DEV_HINT = re.compile(r"UNITY_EDITOR|DEVELOPMENT_BUILD|UE_BUILD_SHIPPING|WITH_EDITOR")
RNG = re.compile(r"\b(?:Random\.(?:Range|Next|value)|FMath::Rand\w*)\b")


def audit(project, *, operation=None):
    op = operation or Operation()
    findings, scanned, skipped = [], 0, []
    for path in c.walk_files(project.root, SKIP):
        op.check_cancel()
        if path.suffix.lower() not in TEXT and path.name != ".env":
            continue
        relative = path.relative_to(project.root).as_posix()
        if path.stat().st_size > 2 * 1024 * 1024:
            skipped.append({"path": relative, "reason": "text file exceeds 2 MiB review limit"})
            continue
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig")
        except UnicodeError:
            skipped.append({"path": relative, "reason": "unsupported text encoding"})
            continue
        scanned += 1
        lines = text.splitlines()
        observations = {"authority_tokens_present_in_file": bool(SERVER_HINT.search(text)),
                        "development_guard_tokens_present_in_file": bool(DEV_HINT.search(text))}
        for line_number, line in enumerate(lines, 1):
            for identifier, pattern, problem, remedy in RULES:
                if pattern.search(line):
                    findings.append(finding(identifier, "configuration", "REVIEW", problem + " " + remedy,
                                            [{"path": relative, "line": line_number, **observations}]))
            if RNG.search(line) and re.search(ECONOMY, "\n".join(lines[max(0, line_number - 4):line_number + 3]), re.I):
                findings.append(finding("LOCAL_REWARD_RANDOMNESS", "configuration", "REVIEW",
                                        "Local RNG near valuable outcomes. Trace whether it is cosmetic/offline or authoritative; multiplayer reward outcomes must be generated/validated by the server.",
                                        [{"path": relative, "line": line_number, **observations}]))
            if len(findings) >= 2000:
                skipped.append({"path": relative, "reason": "finding limit reached; narrow the review scope"})
                break
        if len(findings) >= 2000:
            break
    findings.append(finding("SERVER_AUTHORITY", "runtime", "NOT_VERIFIED",
                            "Text matches do not establish that server checks are missing or correct. Review handlers and run unauthorized/replay/ownership/invalid-value tests against an authorized test server. No server or game logic changed."))
    findings.append(finding("SCAN_COVERAGE", "configuration", "REVIEW" if skipped else "NOT_VERIFIED",
                            "Heuristic text triage only; comments/examples may match. Negative results and authority tokens are not a security PASS. Blueprints, binaries, dynamic code, encoded secrets and external services require separate review.", skipped))
    output = result(project.engine, project.version, findings)
    output.update(scanned_text_files=scanned, excluded_directory_names=sorted(SKIP), output="Conversation/stdout only; no report file written.")
    return output
