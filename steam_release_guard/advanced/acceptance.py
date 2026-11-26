"""Compare measured data and bind reviewer evidence to two immutable builds.

Reports record evidence, never substitute a JSON checkbox for a real game test.
"""
from __future__ import annotations

import math
import re
import statistics

from .. import core as c
from ..operations import GuardError
from ..project_backup import safe_path, relative_name
from . import integrity
from .common import shape

METRICS = {"startup_ms": "ms", "scene_load_ms": "ms", "memory_mib": "MiB", "cpu_percent": "%",
           "file_bytes": "bytes", "patch_bytes": "bytes", "crash_count": "count", "network_rtt_ms": "ms",
           "save_read_ms": "ms", "save_write_ms": "ms"}
RUNTIME = ("startup", "resource_loading", "old_save", "new_save", "multiplayer", "plugins", "offline",
           "patch_update", "dlc", "steam_test_branch", "debug_entrypoints")
STATUSES = {"PASS", "FAIL", "REVIEW", "NOT_VERIFIED", "NOT_APPLICABLE"}


def template():
    pending = lambda: {"status": "NOT_VERIFIED", "reason": "", "evidence": []}
    return {"schema": 1, "environment": {"engine_version": "", "hardware": "", "os": "", "scenario": "", "measurement_tool": ""},
            "baseline": {"build_id": "baseline-001", "manifest_sha256": ""},
            "candidate": {"build_id": "protected-001", "manifest_sha256": ""},
            "metrics": {k: {"baseline_samples": [], "candidate_samples": [], "max_regression_pct": None,
                             "evidence": []} for k in METRICS},
            "runtime_checks": {k: pending() for k in RUNTIME},
            "protection_checks": [{"name": "replace-with-enabled-protection", "configuration": pending(),
                                   "artifact": pending(), "runtime": pending()}]}


def evidence_status(items, evidence_root):
    if not isinstance(items, list) or len(items) > 100:
        raise GuardError("Evidence must be a bounded list of local path/SHA256 references.")
    if not items:
        return "NOT_VERIFIED"
    status = "VERIFIED_FILES"
    for item in items:
        shape(item, {"path", "sha256"})
        name = relative_name(item["path"])
        if not isinstance(item["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"]):
            raise GuardError("Evidence requires a valid SHA256, never a secret value.")
        path = c.local_path(evidence_root, name)
        if not path.is_file():
            if status != "FAIL": status = "NOT_VERIFIED"
        elif c.file_digest(path) != item["sha256"]:
            status = "FAIL"
    return status


def check_record(value, root):
    shape(value, {"status", "reason", "evidence"})
    if value["status"] not in STATUSES or not isinstance(value["reason"], str):
        raise GuardError("Invalid acceptance status/reason.")
    proof = evidence_status(value["evidence"], root)
    if proof == "FAIL" or value["status"] == "FAIL":
        status = "FAIL"
    elif value["status"] == "PASS":
        status = "RECORDED_PASS" if proof == "VERIFIED_FILES" else "NOT_VERIFIED"
    elif value["status"] == "NOT_APPLICABLE":
        status = "REVIEW"  # Applicability requires human review, never silently disappears.
    else:
        status = value["status"]
    return {"status": status, "declared_status": value["status"], "evidence_files": proof,
            "scope": "Reviewer declaration; file hashes checked, content/real-world test not independently attested."}


def compare_metric(name, data, root, baseline_files, candidate_files):
    shape(data, {"baseline_samples", "candidate_samples", "max_regression_pct", "evidence"})
    samples = [data["baseline_samples"], data["candidate_samples"]]
    for group in samples:
        if not isinstance(group, list) or len(group) > 10000 or any(type(v) not in {int, float} or not math.isfinite(v) or v < 0 for v in group):
            raise GuardError("Metrics require finite, nonnegative numeric samples (not booleans).")
    limit = data["max_regression_pct"]
    if limit is not None and (type(limit) not in {int, float} or not math.isfinite(limit) or limit < 0):
        raise GuardError("Set an explicit nonnegative regression threshold or leave it unverified.")
    proof = evidence_status(data["evidence"], root)
    if proof == "FAIL":
        return {"status": "FAIL", "reason": "Measurement evidence hash mismatch"}
    if name == "file_bytes":
        samples = [[sum(f["bytes"] for f in baseline_files)], [sum(f["bytes"] for f in candidate_files)]]
        proof = "VERIFIED_FILES"
    minimum = 1 if name in {"file_bytes", "patch_bytes", "crash_count"} else 3
    if limit is None or any(len(group) < minimum for group in samples) or proof != "VERIFIED_FILES":
        return {"status": "NOT_VERIFIED", "reason": "Need threshold, enough comparable samples and hashed evidence", "unit": METRICS[name]}
    before, after = map(statistics.median, samples)
    regression = 100 * (after - before) / before if before else (0 if not after else None)
    passed = regression is not None and regression <= limit
    if name == "crash_count" and any(samples[1]):
        passed = False
    return {"status": "WITHIN_LIMIT" if passed else "FAIL", "unit": METRICS[name],
            "baseline_median": before, "candidate_median": after, "regression_pct": regression,
            "limit_pct": limit, "scope": "Arithmetic on supplied measurements; only file_bytes measured automatically."}


def check(record, baseline_build, candidate_build, baseline_manifest, candidate_manifest, evidence_root):
    shape(record, {"schema", "environment", "baseline", "candidate", "metrics", "runtime_checks", "protection_checks"})
    if record["schema"] != 1:
        raise GuardError("Unsupported acceptance schema.")
    shape(record["environment"], {"engine_version", "hardware", "os", "scenario", "measurement_tool"})
    if any(not isinstance(v, str) for v in record["environment"].values()):
        raise GuardError("Environment fields must be descriptions without secrets.")
    for side in ("baseline", "candidate"):
        shape(record[side], {"build_id", "manifest_sha256"})
    if record["baseline"]["build_id"] == record["candidate"]["build_id"]:
        raise GuardError("Baseline and protected candidate need distinct build IDs.")
    root = safe_path(evidence_root)
    if not root.is_dir():
        raise GuardError("Local private evidence root is missing.")
    builds, manifests = {}, {}
    for side, build, manifest in (("baseline", baseline_build, baseline_manifest), ("candidate", candidate_build, candidate_manifest)):
        identity = record[side]
        manifests[side] = integrity.load_pinned(manifest, identity["manifest_sha256"], identity["build_id"])
        builds[side] = integrity.verify(build, manifest, identity["build_id"], identity["manifest_sha256"])
    if any(b["status"] != "INTEGRITY_MATCH" for b in builds.values()):
        return {"release_status": "BLOCKED", "reason": "Build bytes no longer match pinned acceptance subjects.", "builds": builds}
    shape(record["metrics"], METRICS)
    metrics = {name: compare_metric(name, data, root, manifests["baseline"]["files"], manifests["candidate"]["files"])
               for name, data in record["metrics"].items()}
    shape(record["runtime_checks"], RUNTIME)
    runtime = {name: check_record(value, root) for name, value in record["runtime_checks"].items()}
    protections = record["protection_checks"]
    if not isinstance(protections, list) or not 1 <= len(protections) <= 100:
        raise GuardError("Record each enabled protection with separate configuration, artifact and runtime evidence.")
    checked, seen = [], set()
    for entry in protections:
        shape(entry, {"name", "configuration", "artifact", "runtime"})
        if not isinstance(entry["name"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", entry["name"]) or entry["name"] in seen:
            raise GuardError("Each protection requires a unique bounded name.")
        seen.add(entry["name"])
        checked.append({"name": entry["name"], **{tier: check_record(entry[tier], root) for tier in ("configuration", "artifact", "runtime")}})
    failed = any(v["status"] == "FAIL" for v in [*metrics.values(), *runtime.values(),
                                                *(p[t] for p in checked for t in ("configuration", "artifact", "runtime"))])
    return {"release_status": "BLOCKED" if failed else "REQUIRES_MANUAL_REVIEW", "builds": builds,
            "environment": "RECORDED" if all(record["environment"].values()) else "NOT_VERIFIED",
            "metrics": metrics, "runtime_checks": runtime, "protection_checks": checked,
            "scope": "No game executed. PASS declarations are only RECORDED_PASS with matching evidence files. REVIEW/NOT_VERIFIED never become PASS. Human inspection of real engine/runtime/protection evidence remains required."}
