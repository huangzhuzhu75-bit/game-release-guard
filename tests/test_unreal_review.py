"""PR review regressions on synthetic files/explicitly fake module capabilities."""
import json
import unittest
from pathlib import Path
from unittest import mock

import test_guard as fixtures
from steam_release_guard import core, project_backup
from steam_release_guard.advanced import unreal
import test_advanced_unreal as previous


class UnrealReviewTests(unittest.TestCase):
    setUp = fixtures.GuardTests.setUp
    put = fixtures.GuardTests.put
    unreal_project = fixtures.GuardTests.unreal
    crypto = fixtures.GuardTests.crypto
    cli = fixtures.GuardTests.cli
    profile = previous.UnrealAdvancedTests.profile
    engine = previous.UnrealAdvancedTests.engine

    def inventory(self, root):
        return {str(p.relative_to(root)): p.read_bytes() for p in core.walk_files(root)
                if not p.is_relative_to(root / core.STATE)}

    def test_explicit_container_choices_and_keys_round_trip(self):
        project = self.unreal_project()
        fixtures.GuardTests.config(self, project)
        self.crypto(project)
        before = self.inventory(project.root)
        for policy, expected in (("pak-only", ("True", "False")), ("pak+iostore", ("True", "True"))):
            with self.subTest(policy=policy):
                config = {**self.profile(), "container_policy": policy}
                planned = unreal.UnrealAdapter().plan(project, config)
                self.assertEqual(self.inventory(project.root), before)
                journal = unreal.apply(project, config, expected_plan=planned)
                saved = json.loads(journal.read_text(encoding="utf-8"))
                self.assertEqual(project_backup.verify(saved["full_backup"]["backup_path"])["status"], "VERIFIED")
                settings = core.ini_values((project.root / "Config/DefaultGame.ini").read_bytes(), core.PACKAGING)
                self.assertEqual((settings["usepakfile"], settings["buseiostore"]), expected)
                core.rollback(project)
                self.assertEqual(self.inventory(project.root), before)

    def test_iostore_only_unsupported_never_enables_pak_or_touches_project(self):
        project = self.unreal_project()
        self.crypto(project)
        self.put("Config/DefaultGame.ini", f"[{core.PACKAGING}]\nUsePakFile=False\nbUseIoStore=True\n", project.root)
        before = self.inventory(project.root)
        with mock.patch("steam_release_guard.project_backup.create") as backup:
            with self.assertRaisesRegex(core.GuardError, "IoStore-only is NOT_VERIFIED"):
                unreal.apply(project, {**self.profile(), "container_policy": "iostore-only"})
        backup.assert_not_called()
        self.assertEqual(self.inventory(project.root), before)
        self.assertFalse((project.root / core.STATE).exists())

    def test_ambiguous_legacy_and_missing_policy_are_rejected_before_mutation(self):
        project = self.unreal_project()
        self.crypto(project)
        before = self.inventory(project.root)
        legacy = {**self.profile(), "schema": 1, "iostore": True}
        legacy.pop("container_policy")
        missing = self.profile()
        missing.pop("container_policy")
        for config in (legacy, missing, {**self.profile(), "container_policy": "auto"}):
            with self.subTest(config=config), self.assertRaises(core.GuardError):
                unreal.apply(project, config)
        self.assertEqual(self.inventory(project.root), before)
        self.assertFalse((project.root / core.STATE).exists())

    def test_example_policy_and_cli_preview_expose_explicit_choice(self):
        project = self.unreal_project()
        self.crypto(project)
        config_path = Path(__file__).resolve().parents[1] / "examples/advanced/unreal-policy.json"
        value = json.loads(config_path.read_text())
        unreal.validate(project, value)
        code, out, _ = self.cli("advanced", "unreal-apply", project.root, "--config", config_path, "--dry-run", "--json")
        self.assertEqual(code, 0, out)
        result = json.loads(out)["result"]
        self.assertEqual(result["container_policy"], "pak+iostore")
        self.assertTrue(result["pak_requested"] and result["iostore_requested"])
        self.assertFalse((project.root / core.STATE).exists())

    def packaged(self):
        build = self.root / "build"
        for name in ("Demo.pak", "Demo.utoc", "Demo.ucas"):
            self.put(name, b"synthetic container", build)
        return build

    def runner(self, pak="UnrealPak -Test -List -CryptoKeys=<file>",
               iostore="IoStoreUtilities -List=<container> -Csv=<file> -CryptoKeys=<file>",
               failure=None, listing=True, help_exit=0):
        self.calls = []
        def fake_run(argv, folder, **kwargs):
            self.calls.append(argv)
            is_io = "IoStore" in argv
            text = (iostore if is_io else pak) if "-Help" in argv else "synthetic only"
            (folder / "tool.log").write_text(text, encoding="utf-8")
            if "-Help" in argv:
                return {"exit_code": help_exit, "log_sha256": core.file_digest(folder / "tool.log")}
            if failure == ("iostore" if is_io else "pak"):
                return {"exit_code": 7, "log_sha256": core.file_digest(folder / "tool.log")}
            for arg in argv:
                if arg.startswith("-Csv=") and listing:
                    Path(arg[5:]).write_text("fixture,not-real-assets\n", encoding="utf-8")
            return {"exit_code": 0, "log_sha256": core.file_digest(folder / "tool.log")}
        return fake_run

    def inspect(self, **kwargs):
        with mock.patch.object(unreal, "private_run", side_effect=self.runner(**kwargs)):
            return unreal.verify(self.unreal_project(), self.engine(), self.packaged(), self.root / "proof")

    def test_only_pak_entrypoint_cannot_verify_iostore(self):
        report = self.inspect(iostore="UnrealPak -Test -List")
        self.assertEqual(report["groups"]["pak"]["status"], "REVIEW")
        self.assertEqual(report["groups"]["iostore"]["status"], "NOT_VERIFIED")
        self.assertEqual(report["status"], "NOT_VERIFIED")
        self.assertFalse(any("IoStore" in call and "-Help" not in call for call in self.calls))

    def test_only_iostoreutilities_entrypoint_cannot_verify_pak(self):
        report = self.inspect(pak="UnrealPak host; no PakFileUtilities commands")
        self.assertEqual(report["groups"]["pak"]["status"], "NOT_VERIFIED")
        self.assertEqual(report["groups"]["iostore"]["status"], "REVIEW")
        self.assertTrue(all("IoStore" in c or "-Help" in c for c in self.calls))
        self.assertTrue(all(row["container"].endswith(".utoc") for row in report["groups"]["iostore"]["checks"]))

    def test_missing_host_and_undocumented_standalone_do_not_execute(self):
        project, build = self.unreal_project(), self.packaged()
        engine = self.root / "no-host"
        self.put("Engine/Build/Build.version", '{"MajorVersion":5,"MinorVersion":6,"PatchVersion":0}', engine)
        self.put("Engine/Binaries/Win64/IoStoreUtilities.exe", b"not an established official standalone CLI", engine)
        with mock.patch.object(unreal, "private_run") as run:
            report = unreal.verify(project, engine, build, self.root / "proof")
        run.assert_not_called()
        self.assertEqual(report["status"], "NOT_VERIFIED")
        self.assertTrue(all(g["status"] == "NOT_VERIFIED" for g in report["groups"].values()))

    def test_version_mismatch_unknown_version_and_malformed_version_never_execute(self):
        project, build = self.unreal_project(), self.packaged()
        for index, version in enumerate(((5, 5, 0), (5, 9, 0), (5, True, 0))):
            engine = self.engine()
            self.put("Engine/Build/Build.version", json.dumps(dict(zip(("MajorVersion", "MinorVersion", "PatchVersion"), version))), engine)
            with mock.patch.object(unreal, "private_run") as run:
                report = unreal.verify(project, engine, build, self.root / f"proof{index}")
            run.assert_not_called()
            self.assertEqual(report["status"], "NOT_VERIFIED")

    def test_iostore_unreviewed_version_does_not_borrow_pak_capability(self):
        project = self.unreal_project("5.5")
        entry = unreal.UnrealAdapter().detect(project, self.engine(5))["tools"]
        self.assertEqual(entry["pak"]["status"], "DETECTED")
        self.assertEqual(entry["iostore"]["status"], "NOT_VERIFIED")

    def test_unsupported_iostore_parameters_and_help_failure_are_not_verified(self):
        self.assertFalse(unreal._supports("-ListFormats -TestSomething", "-List"))
        for index, options in enumerate(({"iostore": "IoStore -List -Info"}, {"help_exit": 1})):
            with mock.patch.object(unreal, "private_run", side_effect=self.runner(**options)):
                report = unreal.verify(self.unreal_project(), self.engine(), self.packaged(), self.root / f"proof{index}")
            self.assertEqual(report["groups"]["iostore"]["status"], "NOT_VERIFIED")
            self.assertFalse(any("IoStore" in c and "-Help" not in c for c in self.calls))

    def test_failed_container_execution_does_not_destroy_other_group_result(self):
        report = self.inspect(failure="iostore")
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["groups"]["pak"]["status"], "REVIEW")
        self.assertEqual(report["groups"]["iostore"]["status"], "FAIL")
        self.assertEqual(report["groups"]["iostore"]["checks"][0]["exit_code"], 7)

    def test_os_execution_failure_is_recorded_without_secret_exception(self):
        with mock.patch.object(unreal, "private_run", side_effect=OSError("SECRET_DIAGNOSTIC")):
            report = unreal.verify(self.unreal_project(), self.engine(), self.packaged(), self.root / "proof")
        self.assertEqual(report["status"], "FAIL")
        self.assertNotIn("SECRET_DIAGNOSTIC", json.dumps(report))

    def test_exit_zero_without_iostore_listing_is_not_an_artifact_check(self):
        report = self.inspect(listing=False)
        self.assertEqual(report["groups"]["iostore"]["status"], "NOT_VERIFIED")
        self.assertFalse(any(f["status"] == "PASS" for f in report["findings"]))

    def test_only_one_container_kind_does_not_probe_the_other(self):
        for index, names in enumerate((("Demo.pak",), ("Demo.utoc", "Demo.ucas"))):
            build = self.root / f"build{index}"
            for name in names:
                self.put(name, b"synthetic", build)
            with mock.patch.object(unreal, "private_run", side_effect=self.runner()):
                report = unreal.verify(self.unreal_project(), self.engine(), build, self.root / f"proof{index}")
            absent = "iostore" if index == 0 else "pak"
            self.assertEqual(report["groups"][absent]["status"], "NOT_REQUESTED")
            self.assertTrue(all(("IoStore" in c) == (index == 1) for c in self.calls))
