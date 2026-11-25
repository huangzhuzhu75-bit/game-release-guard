import unittest

import test_guard as fixtures
from steam_release_guard import core
from steam_release_guard.advanced import acceptance, integrity


class AcceptanceTests(unittest.TestCase):
    put = fixtures.GuardTests.put

    def setUp(self):
        fixtures.GuardTests.setUp(self)
        self.record = acceptance.template()
        self.baseline = self.root / "baseline"
        self.candidate = self.root / "candidate"
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()
        self.manifests = []
        for side, build in (("baseline", self.baseline), ("candidate", self.candidate)):
            self.put("Game.exe", b"synthetic-" + side.encode(), build)
            manifest = self.root / (side + ".json")
            result = integrity.create(build, self.record[side]["build_id"], manifest)
            self.record[side]["manifest_sha256"] = result["manifest_sha256"]
            self.manifests.append(manifest)

    def check(self):
        return acceptance.check(self.record, self.baseline, self.candidate, *self.manifests, self.evidence)

    def evidence_ref(self):
        path = self.put("measurement.txt", "synthetic evidence only", self.evidence)
        return {"path": "measurement.txt", "sha256": core.file_digest(path)}

    def test_missing_measurements_and_runtime_are_never_pass(self):
        report = self.check()
        self.assertEqual(report["release_status"], "REQUIRES_MANUAL_REVIEW")
        self.assertTrue(all(m["status"] == "NOT_VERIFIED" for m in report["metrics"].values()))
        self.assertEqual(report["runtime_checks"]["startup"]["status"], "NOT_VERIFIED")

    def test_real_evidence_files_do_not_upgrade_review_or_runtime_claims(self):
        ref = self.evidence_ref()
        for status in ("REVIEW", "NOT_VERIFIED", "PASS"):
            self.record["runtime_checks"]["startup"] = {"status": status, "reason": "fixture", "evidence": [ref]}
            expected = "RECORDED_PASS" if status == "PASS" else status
            self.assertEqual(self.check()["runtime_checks"]["startup"]["status"], expected)
        self.record["runtime_checks"]["startup"]["evidence"] = []
        self.assertEqual(self.check()["runtime_checks"]["startup"]["status"], "NOT_VERIFIED")

    def test_metric_regression_and_zero_baseline_are_blockers(self):
        data = {"baseline_samples": [100, 110, 100], "candidate_samples": [140, 145, 140],
                "max_regression_pct": 10, "evidence": [self.evidence_ref()]}
        self.record["metrics"]["startup_ms"] = data
        self.assertEqual(self.check()["release_status"], "BLOCKED")
        data.update(baseline_samples=[0, 0, 0], candidate_samples=[1, 1, 1])
        metric = self.check()["metrics"]["startup_ms"]
        self.assertEqual(metric["status"], "FAIL")
        self.assertIsNone(metric["regression_pct"])

    def test_changed_build_or_evidence_invalidates_acceptance(self):
        ref = self.evidence_ref()
        self.record["protection_checks"][0]["artifact"] = {"status": "PASS", "reason": "fixture", "evidence": [ref]}
        (self.evidence / ref["path"]).write_bytes(b"changed")
        self.assertEqual(self.check()["release_status"], "BLOCKED")
        self.record["metrics"]["file_bytes"]["evidence"] = [ref]
        self.record["metrics"]["file_bytes"]["max_regression_pct"] = 100
        self.assertEqual(self.check()["metrics"]["file_bytes"]["status"], "FAIL")
        (self.candidate / "Game.exe").write_bytes(b"updated")
        self.assertIn("Build bytes", self.check()["reason"])

    def test_malformed_metrics_typo_and_traversal_rejected(self):
        self.record["metrics"]["startup_ms"]["candidate_samples"] = [True]
        with self.assertRaises(core.GuardError):
            self.check()
        self.record["metrics"]["startup_ms"]["candidate_samples"] = []
        self.record["runtime_checks"]["startup"]["evidence"] = [{"path": "../secret", "sha256": "a" * 64}]
        with self.assertRaises(core.GuardError):
            self.check()
