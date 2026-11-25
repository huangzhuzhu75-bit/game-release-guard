import base64
import json
import unittest
from unittest import mock

import test_guard as fixtures
from steam_release_guard import core
from steam_release_guard.advanced import unreal


class UnrealAdvancedTests(unittest.TestCase):
    setUp = fixtures.GuardTests.setUp
    put = fixtures.GuardTests.put
    unreal_project = fixtures.GuardTests.unreal
    crypto = fixtures.GuardTests.crypto
    cli = fixtures.GuardTests.cli

    def profile(self):
        return {"schema": 1, "engine_version": "5.6", "pak": {"index": True, "ini": True,
                "uasset": False, "all_assets": False, "signing": False}, "iostore": True,
                "assets": [{"path": "Content/Core/*", "grade": "A", "loading": "streamed"}]}

    def test_each_crypto_switch_independent_and_key_bytes_preserved_on_rollback(self):
        project = self.unreal_project()
        crypto = self.crypto(project)
        before = crypto.read_bytes()
        config = self.profile()
        for switch in ("index", "ini", "uasset", "all_assets"):
            config["pak"] = {k: k == switch for k in unreal.FLAGS}
            unreal.apply(project, config)
            values = core.ini_values(crypto.read_bytes(), core.CRYPTO)
            self.assertEqual(values["encryptionkey"], core.ini_values(before, core.CRYPTO)["encryptionkey"])
            for key, ini_name in unreal.FLAGS.items():
                self.assertEqual(values[ini_name.lower()], str(key == switch))
            core.rollback(project)
            self.assertEqual(crypto.read_bytes(), before)

    def test_missing_zero_and_bad_signing_keys_block_without_state_or_secrets(self):
        project = self.unreal_project()
        for key in ("short", base64.b64encode(bytes(32)).decode()):
            self.crypto(project, key)
            with self.assertRaises(core.GuardError):
                unreal.apply(project, self.profile())
        self.crypto(project)
        config = self.profile()
        config["pak"]["signing"] = True
        with self.assertRaises(core.GuardError):
            unreal.apply(project, config)
        self.assertFalse((project.root / core.STATE).exists())

    def test_turning_off_individual_encryption_does_not_require_new_keys(self):
        project = self.unreal_project()
        config = self.profile()
        config["pak"] = dict.fromkeys(unreal.FLAGS, False)
        self.assertTrue(unreal.UnrealAdapter().plan(project, config))

    def test_unsupported_version_and_ambiguous_assets_remain_review(self):
        project = self.unreal_project()
        self.crypto(project)
        with self.assertRaises(core.GuardError):
            unreal.validate(project, {**self.profile(), "engine_version": "5.9"})
        self.put("Content/Core/Hero.uasset", b"fixture", project.root)
        config = self.profile()
        config["assets"].append({"path": "Content/*", "grade": "B", "loading": "startup"})
        result = unreal.asset_plan(project, config)
        self.assertEqual(result["resources"][0]["reason"], "Ambiguous rules")
        self.assertEqual(result["status"], "REVIEW")

    def engine(self, minor=6):
        root = self.root / "UE"
        self.put("Engine/Build/Build.version", json.dumps({"MajorVersion": 5, "MinorVersion": minor, "PatchVersion": 0}), root)
        self.put("Engine/Binaries/Win64/UnrealPak.exe", b"mock official tool placeholder -- NEVER executed", root)
        return root

    def test_tool_version_missing_partition_and_keys_in_depot_refused(self):
        project = self.unreal_project()
        build = self.root / "build"
        self.put("Demo.utoc", b"fixture", build)
        engine = self.engine(5)
        with self.assertRaises(core.GuardError):
            unreal.verify_preview(project, engine, build, self.root / "evidence")
        self.engine()
        with self.assertRaisesRegex(core.GuardError, "ucas"):
            unreal.verify_preview(project, engine, build, self.root / "evidence")
        self.put("Demo.ucas", b"fixture", build)
        key = self.put("Crypto.json", "{}", build)
        with self.assertRaises(core.GuardError):
            unreal.verify_preview(project, engine, build, self.root / "evidence", key)

    def test_pak_and_iostore_checks_are_separate_no_success_from_exit_zero(self):
        project = self.unreal_project()
        build = self.root / "build"
        for name in ("Demo.pak", "Demo.utoc", "Demo.ucas"):
            self.put(name, b"synthetic", build)
        calls = []

        def fake_run(argv, folder, **kwargs):
            calls.append(argv)
            (folder / "tool.log").write_text("-Test -List -Info" if "-Help" in argv else "synthetic only", encoding="utf-8")
            return {"exit_code": 0, "log_sha256": "a" * 64}
        with mock.patch.object(unreal, "private_run", side_effect=fake_run):
            output = unreal.verify(project, self.engine(), build, self.root / "evidence")
        self.assertEqual(len(calls), 5)
        self.assertTrue(any(call[1].endswith(".utoc") for call in calls))
        self.assertEqual(output["status"], "REVIEW")
        self.assertFalse(any(f["status"] == "PASS" for f in output["findings"]))

    def test_cli_dry_run_is_read_only_and_never_prints_crypto_material(self):
        project = self.unreal_project()
        key = self.crypto(project)
        config = self.put("profile.json", json.dumps(self.profile()))
        code, output, _ = self.cli("advanced", "unreal-apply", project.root, "--config", config, "--dry-run", "--json")
        self.assertEqual(code, 0, output)
        self.assertNotIn(core.ini_values(key.read_bytes(), core.CRYPTO)["encryptionkey"], output)
        self.assertFalse((project.root / core.STATE).exists())
