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
        package = self.put("Packages/com.code-philosophy.obfuz/package.json",
                           '{"name":"com.code-philosophy.obfuz","version":"4.0.0"}', project.root)
        self.assertTrue(adapter.detect(project)["installed_candidates"][0]["api_supported"])
        package.write_text('{"name":"com.code-philosophy.obfuz","version":"5.0.0"}')
        self.assertFalse(adapter.detect(project)["installed_candidates"][0]["api_supported"])

    def test_advanced_changes_use_full_backup_and_byte_exact_old_rollback(self):
        project = self.unity()
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
        record = private_run([sys.executable, "-c", "print('EncryptionKey=DO_NOT_LOG');print('done')"], folder)
        self.assertEqual(record["exit_code"], 0)
        self.assertNotIn("DO_NOT_LOG", (folder / "tool.log").read_text())
        self.assertIn("done", (folder / "tool.log").read_text())
        self.assertFalse((folder / "tool-output.private").exists())
