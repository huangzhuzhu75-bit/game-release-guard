"""Adapter contracts on synthetic projects; no claim of engine protection."""
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

import test_guard as fixtures
from steam_release_guard import core, project_backup
from steam_release_guard.advanced import obfuscation as ob
from steam_release_guard.advanced.common import private_run, read_json


class ObfuscationTests(fixtures.GuardTests.__bases__[0]):
    setUp = fixtures.GuardTests.setUp
    put = fixtures.GuardTests.put
    unity = fixtures.GuardTests.unity
    cli = fixtures.GuardTests.cli

    def config(self):
        return {"schema": 1, "engine_version": "6000.6.6f1", "adapter": "obfuz", "tool_version": "4.0.0",
                "assemblies": [{"name": "Game.Core", "include_types": ["Game.Core.Rules"],
                                "exclude_types": ["Game.Core.Save*"], "rename_fields": False}],
                "reference_assemblies": ["Assembly-CSharp"], "strings": False, "control_flow": False}

    def test_plan_is_read_only_excludes_all_until_explicitly_selected(self):
        project = self.unity()
        before = sorted(core.walk_files(project.root))
        planned = ob.ObfuzAdapter().plan(project, self.config())
        self.assertEqual(before, sorted(core.walk_files(project.root)))
        xml = ET.fromstring(next(p.data for p in planned if p.path.endswith("rename.xml")))
        types = xml.find("assembly").findall("type")
        self.assertEqual(types[0].attrib["obName"], "0")
        self.assertEqual(types[1].attrib["name"], "Game.Core.Rules")
        self.assertEqual(types[1].find("field").attrib["obName"], "0")
        self.assertEqual(types[-1].attrib["name"], "Game.Core.Save*")
        self.assertEqual(types[-1].attrib["obName"], "0")

    def test_unknown_version_wildcard_default_and_unverified_passes_rejected(self):
        project = self.unity()
        for change in ({"tool_version": "99"}, {"engine_version": "6000.1.0f1"}, {"strings": True},
                       {"control_flow": True}, {"assemblies": []}, {"typo": True}):
            with self.subTest(change=change), self.assertRaises(core.GuardError):
                ob.validate(project, {**self.config(), **change})
        config = self.config()
        config["assemblies"][0]["include_types"] = ["*"]
        with self.assertRaises(core.GuardError):
            ob.validate(project, config)

    def test_detect_missing_and_exact_version_without_execution(self):
        project = self.unity()
        adapter = ob.ObfuzAdapter()
        self.assertEqual(adapter.detect(project)["status"], "MISSING")
        with self.assertRaisesRegex(core.GuardError, "missing"):
            ob.apply(project, self.config())
        self.assertFalse((project.root / core.STATE).exists())
        package = self.put("Packages/com.code-philosophy.obfuz/package.json",
                           '{"name":"com.code-philosophy.obfuz","version":"4.0.0"}', project.root)
        self.assertTrue(adapter.detect(project)["installed_candidates"][0]["api_supported"])
        package.write_text('{"name":"com.code-philosophy.obfuz","version":"5.0.0"}')
        self.assertFalse(adapter.detect(project)["installed_candidates"][0]["api_supported"])

    def test_advanced_changes_use_full_backup_and_byte_exact_old_rollback(self):
        project = self.unity()
        self.put("Packages/com.code-philosophy.obfuz/package.json", '{"name":"com.code-philosophy.obfuz","version":"4.0.0"}', project.root)
        before = {str(p.relative_to(project.root)): p.read_bytes() for p in core.walk_files(project.root)}
        planned = ob.ObfuzAdapter().plan(project, self.config())
        manifest = ob.apply(project, self.config(), expected_plan=planned)
        journal = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(project_backup.verify(journal["full_backup"]["backup_path"])["status"], "VERIFIED")
        core.rollback(project)
        after = {str(p.relative_to(project.root)): p.read_bytes() for p in core.walk_files(project.root)
                 if not p.is_relative_to(project.root / core.STATE)}
        self.assertEqual(before, after)

    def test_failed_full_backup_and_stale_plan_do_not_mutate_project(self):
        project = self.unity()
        self.put("Packages/com.code-philosophy.obfuz/package.json", '{"name":"com.code-philosophy.obfuz","version":"4.0.0"}', project.root)
        planned = ob.ObfuzAdapter().plan(project, self.config())
        with mock.patch("steam_release_guard.project_backup.create", side_effect=core.GuardError("backup failed")):
            with self.assertRaises(core.GuardError):
                ob.apply(project, self.config(), expected_plan=planned)
        self.assertFalse((project.root / ob.CONFIG).exists())
        self.put(ob.CONFIG, "user change", project.root)
        with self.assertRaises(core.GuardError):
            ob.apply(project, self.config(), expected_plan=planned)
        self.assertEqual((project.root / ob.CONFIG).read_text(), "user change")

    def test_build_refuses_original_project_even_when_explicitly_requested(self):
        with self.assertRaisesRegex(core.GuardError, "backup-restore"):
            ob.build_preview(self.unity(), self.config(), Path("Unity.exe"), self.root / "build", self.root / "logs")

    def test_cli_preview_consent_missing_tool_and_status(self):
        project = self.unity()
        config = self.put("config.json", json.dumps(self.config()))
        self.assertEqual(self.cli("advanced", "unity-plan", project.root, "--config", config, "--json")[0], 0)
        self.assertEqual(self.cli("advanced", "unity-apply", project.root, "--config", config, "--json")[0], 3)
        self.assertEqual(self.cli("advanced", "unity-apply", project.root, "--config", config, "--yes", "--json")[0], 1)
        self.assertFalse((project.root / ob.CONFIG).exists())

    def test_duplicate_json_fields_rejected(self):
        with self.assertRaises(core.GuardError):
            read_json(self.put("config.json", '{"strings":true,"strings":false}'))

    def test_real_subprocess_has_redacted_bounded_log_and_no_shell(self):
        folder = self.root / "private"
        folder.mkdir()
        record = private_run([Path(sys.executable).resolve(strict=True), "-c", "print('EncryptionKey=DO_NOT_LOG');print('done')"], folder)
        self.assertEqual(record["exit_code"], 0)
        self.assertNotIn("DO_NOT_LOG", (folder / "tool.log").read_text())
        self.assertIn("done", (folder / "tool.log").read_text())
        self.assertFalse((folder / "tool-output.private").exists())

    def test_fast_tool_exceeding_log_limit_is_not_success(self):
        folder = self.root / "private"
        folder.mkdir()

        def fast_process(*args, **kwargs):
            # Explicit fake process: exits before the first poll. The retained
            # bytes must be bounded even without the polling loop running.
            kwargs["stdout"].write(b"x" * (16 * 1024 * 1024 + 1))
            return mock.Mock(poll=mock.Mock(return_value=0), returncode=0)

        with mock.patch("steam_release_guard.advanced.common.subprocess.Popen", side_effect=fast_process):
            with self.assertRaisesRegex(core.GuardError, "log limit"):
                private_run([Path(sys.executable).resolve(strict=True)], folder)
        self.assertLessEqual((folder / "tool.log").stat().st_size, 16 * 1024 * 1024)
        self.assertFalse((folder / "tool-output.private").exists())

    def test_untrusted_build_receipt_requires_exact_assembly_and_output_binding(self):
        project, config = self.unity(), self.config()
        output = self.root / "build"
        executable = self.put("Game.exe", b"synthetic receipt subject, not a runnable game", output)
        receipt = {"configuration": "PASS", "artifact": "PASS", "runtime": "NOT_VERIFIED",
                   "engine_version": project.version, "tool_version": "4.0.0",
                   "executable_sha256": core.file_digest(executable),
                   "assemblies": [{"name": "Game.Core", "before_sha256": "a" * 64,
                                   "after_sha256": "b" * 64, "renamed_selected_types": 1}]}

        for index, change in enumerate(({}, {"runtime": "PASS"}, {"executable_sha256": "0" * 64},
                                        {"assemblies": []}, {"assemblies": receipt["assemblies"] * 2})):
            def fake_tool(argv, folder, **kwargs):
                (folder / "obfuscation.json").write_text(json.dumps({**receipt, **change}), encoding="utf-8")
                return {"exit_code": 0}

            with self.subTest(change=change), mock.patch.object(ob, "build_preview", return_value={}), \
                 mock.patch.object(ob.ObfuzAdapter, "plan", return_value=[]), \
                 mock.patch.object(ob, "private_run", side_effect=fake_tool):
                if change:
                    with self.assertRaises(core.GuardError):
                        ob.build(project, config, self.root / "Unity.exe", output, self.root / f"proof{index}")
                else:
                    record = ob.build(project, config, self.root / "Unity.exe", output, self.root / f"proof{index}")
                    self.assertEqual(record["status"], "REVIEW")
                    self.assertEqual(record["artifact"]["runtime"], "NOT_VERIFIED")
