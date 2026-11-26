import json
import unittest

import test_guard as fixtures
from steam_release_guard import core
from steam_release_guard.advanced.security import audit


class SecurityTests(unittest.TestCase):
    setUp = fixtures.GuardTests.setUp
    put = fixtures.GuardTests.put
    unity = fixtures.GuardTests.unity
    unreal = fixtures.GuardTests.unreal
    cli = fixtures.GuardTests.cli

    def test_unity_finds_concrete_locations_without_secret_values_or_writes(self):
        project = self.unity()
        self.put("Assets/Game/Economy.cs", '''string api_key = "private-secret-not-in-output";
coins += clientReward;
PlayerPrefs.SetInt("coins", coins);
isAdmin = true;
[ServerRpc(RequireOwnership = false)]
void RequestTrade() { }
// loot result
var result = Random.Range(0, 100);
void DebugMenu() { }
''', project.root)
        before = {str(p): p.read_bytes() for p in core.walk_files(project.root)}
        report = audit(project)
        ids = {f["id"] for f in report["findings"]}
        self.assertTrue({"HARDCODED_SECRET", "CLIENT_ECONOMY_WRITE", "LOCAL_CRITICAL_SAVE", "CLIENT_PRIVILEGE", "NETWORK_MUTATION", "LOCAL_REWARD_RANDOMNESS", "RELEASE_DEBUG_ENTRY"}.issubset(ids))
        first = report["findings"][0]["evidence"][0]
        self.assertEqual((first["path"], first["line"]), ("Assets/Game/Economy.cs", 1))
        self.assertNotIn("private-secret-not-in-output", json.dumps(report))
        self.assertEqual(before, {str(p): p.read_bytes() for p in core.walk_files(project.root)})

    def test_unreal_authority_and_dev_guards_are_acknowledged_not_proven(self):
        project = self.unreal()
        self.put("Source/Game/Trade.cpp", '''UFUNCTION(Server, Reliable, WithValidation)
void RequestTrade();
if (HasAuthority()) { balance += reward; }
#if !UE_BUILD_SHIPPING
void EnableCheats();
#endif
''', project.root)
        report = audit(project)
        row = next(f for f in report["findings"] if f["id"] == "CLIENT_ECONOMY_WRITE")
        self.assertTrue(row["evidence"][0]["authority_tokens_present_in_file"])
        self.assertTrue(row["evidence"][0]["development_guard_tokens_present_in_file"])
        self.assertEqual(row["status"], "REVIEW")
        self.assertFalse(any(f["status"] == "PASS" for f in report["findings"]))

    def test_clean_empty_and_oversized_source_never_gets_security_pass(self):
        project = self.unity()
        self.put("Assets/Large.cs", b"x" * (2 * 1024 * 1024 + 1), project.root)
        self.put("Library/Ignored.cs", 'api_key="not-scanned"', project.root)
        report = audit(project)
        coverage = next(f for f in report["findings"] if f["id"] == "SCAN_COVERAGE")
        self.assertEqual(coverage["evidence"][0]["path"], "Assets/Large.cs")
        self.assertFalse(any(f["status"] == "PASS" for f in report["findings"]))
        self.assertEqual(report["release_status"], "REQUIRES_MANUAL_REVIEW")

    def test_utf16_and_cli_do_not_generate_report_files(self):
        project = self.unreal()
        self.put("Config/Client.ini", 'client_secret="fixture-value-123456"'.encode("utf-16"), project.root)
        code, text, _ = self.cli("advanced", "security-inspect", project.root, "--json")
        self.assertEqual(code, 0, text)
        self.assertIn("HARDCODED_SECRET", text)
        self.assertNotIn("fixture-value-123456", text)
        self.assertFalse((project.root / core.STATE).exists())
