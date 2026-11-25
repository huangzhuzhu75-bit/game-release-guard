import base64
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from steam_release_guard import core
from steam_release_guard.cli import main


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="srg-test-")
        self.root = Path(self.scratch.name)
        self.addCleanup(self.scratch.cleanup)

    def put(self, relative, data=b"", base=None):
        path = (base or self.root) / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data.encode("utf-8") if isinstance(data, str) else data)
        return path

    def unity(self):
        root = self.root / "中文 Unity Project"
        self.put("ProjectSettings/ProjectVersion.txt", "m_EditorVersion: 6000.6.6f1\n", root)
        self.put("Assets/Scenes/Main.unity", "%YAML 1.1\n", root)
        self.put("ProjectSettings/ProjectSettings.asset", "PlayerSettings:\n  scriptingBackend:\n    Standalone: 0\n", root)
        return core.detect_project(root)

    def unreal(self, version="5.6"):
        root = self.root / "中文 Unreal Project"
        self.put("Demo.uproject", json.dumps({"FileVersion": 3, "EngineAssociation": version}), root)
        return core.detect_project(root)

    def config(self, project, data=None):
        return self.put("Config/DefaultGame.ini", data or (
            "; user comment\r\n[/Script/UnrealEd.ProjectPackagingSettings]\r\n"
            "BuildConfiguration=PPBC_Development\r\nIncludeDebugFiles=True\r\n"
            "+MapsToCook=(FilePath=\"/Game/Map\")\r\n+MapsToCook=(FilePath=\"/Game/Other\")\r\n"
            "bUseIoStore=True\r\n[Other]\r\nValue=keep-me\r\n"), project.root)

    def crypto(self, project, key=None):
        key = key or base64.b64encode(bytes(range(32))).decode("ascii")
        return self.put("Config/DefaultCrypto.ini", f"[{core.CRYPTO}]\nEncryptionKey={key}\nbEncryptPakIndex=False\n", project.root)

    def unity_build(self):
        root = self.root / "build"
        self.put("Game.exe", b"test-executable-not-a-real-PE", root)
        self.put("GameAssembly.dll", b"test-native-not-a-real-DLL", root)
        self.put("Game_Data/il2cpp_data/Metadata/global-metadata.dat", b"test-metadata", root)
        return root

    def ids(self, report):
        return {finding["id"]: finding for finding in report["findings"]}

    def cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            result = main(list(map(str, args)))
        return result, out.getvalue(), err.getvalue()

    def test_detect_unicode_and_spaces(self):
        self.assertEqual(self.unity().version, "6000.6.6f1")
        project = self.unreal()
        self.assertEqual(core.detect_project(project.descriptor).engine, "unreal")

    def test_ambiguous_unreal_requires_explicit_descriptor(self):
        project = self.unreal()
        self.put("Other.uproject", '{"EngineAssociation":"5.6"}', project.root)
        with self.assertRaises(core.GuardError):
            core.detect_project(project.root)
        self.assertEqual(core.detect_project(project.descriptor).descriptor.name, "Demo.uproject")

    def test_unrecognized_engine_does_not_mutate(self):
        project = self.unreal("{custom-source-guid}")
        before = list(project.root.rglob("*"))
        with self.assertRaises(core.GuardError):
            core.apply(project)
        self.assertEqual(before, list(project.root.rglob("*")))

    def test_unreal_apply_idempotence_and_byte_exact_rollback(self):
        project = self.unreal()
        config = self.config(project)
        original = config.read_bytes()
        manifest = core.apply(project)
        changed = config.read_bytes()
        self.assertIn(b"BuildConfiguration=PPBC_Shipping\r\n", changed)
        self.assertIn(b"IncludeDebugFiles=False\r\n", changed)
        self.assertIn(b"bUseIoStore=True\r\n", changed)
        self.assertEqual(changed.count(b"+MapsToCook"), 2)
        self.assertIn(b"[Other]\r\nValue=keep-me\r\n", changed)
        self.assertIsNone(core.apply(project))
        self.assertEqual(core.rollback(project), manifest)
        self.assertEqual(config.read_bytes(), original)
        self.assertFalse((project.root / ".gitignore").exists())
        self.assertEqual((project.root / core.STATE / ".gitignore").read_text(), "*\n")

    def test_unity_only_installs_editor_adapter(self):
        project = self.unity()
        settings = project.root / "ProjectSettings/ProjectSettings.asset"
        before = settings.read_bytes()
        core.apply(project)
        self.assertEqual(settings.read_bytes(), before)
        self.assertTrue((project.root / core.UNITY_ADAPTER).is_file())
        self.assertIn('"Editor"', (project.root / "Assets/SteamReleaseGuard/Editor/SteamReleaseGuard.Editor.asmdef").read_text())
        core.rollback(project)
        self.assertFalse((project.root / core.UNITY_ADAPTER).exists())

    def test_invalid_crypto_blocks_entire_transaction(self):
        project = self.unreal()
        config = self.config(project)
        before = config.read_bytes()
        for key in ("short", base64.b64encode(bytes(32)).decode("ascii")):
            self.crypto(project, key)
            with self.assertRaises(core.GuardError):
                core.apply(project, encrypt_index=True)
            self.assertEqual(config.read_bytes(), before)
            self.assertFalse((project.root / core.STATE).exists())

    def test_index_encryption_preserves_key_and_iostore(self):
        project = self.unreal()
        game = self.config(project)
        crypto = self.crypto(project)
        old_crypto = crypto.read_bytes()
        key = core.ini_values(old_crypto, core.CRYPTO)["encryptionkey"]
        core.apply(project, True)
        self.assertEqual(core.ini_values(crypto.read_bytes(), core.CRYPTO)["encryptionkey"], key)
        self.assertIn(b"bEncryptPakIndex=True", crypto.read_bytes())
        self.assertNotIn(b"bEncryptAllAssetFiles=True", crypto.read_bytes())
        self.assertIn(b"UsePakFile=True", game.read_bytes())
        self.assertIn(b"bUseIoStore=True", game.read_bytes())
        self.assertNotIn(key, json.dumps(core.audit(project)))
        core.rollback(project)
        self.assertEqual(crypto.read_bytes(), old_crypto)

    def test_repeated_sections_scalars_and_ue_arrays(self):
        original = b"[S]\nK=old\n+Array=a\n+Array=b\n[Other]\nK=stay\n[S]\nK=bad\n"
        changed = core.patch_ini(original, "S", {"K": "new", "Added": "True"})
        self.assertEqual(changed.count(b"K=new"), 2)
        self.assertIn(b"[Other]\nK=stay", changed)
        self.assertIn(b"+Array=a\n+Array=b", changed)
        self.assertEqual(core.patch_ini(changed, "S", {"K": "new", "Added": "True"}), changed)

    def test_utf16_bom_and_missing_newline(self):
        original = "[S]\r\nOther=中文".encode("utf-16")
        changed = core.patch_ini(original, "S", {"K": "True"})
        self.assertTrue(changed.startswith(b"\xff\xfe"))
        self.assertIn("Other=中文\r\nK=True\r\n", changed.decode("utf-16"))

    def test_rollback_refuses_to_overwrite_later_user_changes(self):
        project = self.unreal()
        config = self.config(project)
        core.apply(project)
        config.write_bytes(config.read_bytes() + b"; later user change\n")
        ignore_before = (project.root / ".gitignore").read_bytes()
        with self.assertRaisesRegex(core.GuardError, "Rollback conflict"):
            core.rollback(project)
        self.assertIn(b"later user change", config.read_bytes())
        self.assertEqual((project.root / ".gitignore").read_bytes(), ignore_before)

    def test_corrupt_backup_prevents_partial_restore(self):
        project = self.unreal()
        config = self.config(project)
        manifest = core.apply(project)
        before = config.read_bytes()
        backup = next(manifest.parent.glob("*.bak"))
        backup.write_bytes(b"corrupted")
        with self.assertRaisesRegex(core.GuardError, "integrity"):
            core.rollback(project)
        self.assertEqual(config.read_bytes(), before)

    def test_interrupted_apply_can_be_recovered(self):
        project = self.unreal()
        config = self.config(project)
        before = config.read_bytes()
        original_write = core.atomic_write

        def fail_config(path, data):
            if path == config:
                raise OSError("simulated disk error")
            return original_write(path, data)

        with mock.patch.object(core, "atomic_write", side_effect=fail_config):
            with self.assertRaisesRegex(core.GuardError, "interrupted"):
                core.apply(project)
        self.assertTrue((project.root / ".gitignore").exists())
        core.rollback(project)
        self.assertEqual(config.read_bytes(), before)
        self.assertFalse((project.root / ".gitignore").exists())

    def test_path_traversal_is_rejected(self):
        for name in ("../outside", str(self.root / "absolute")):
            with self.assertRaises(core.GuardError):
                core.local_path(self.root, name)

    def test_source_scan_has_locations_not_secret_contents(self):
        project = self.unity()
        self.put("Assets/Game/Commands.cs", '// DebugMenu secret-value-not-for-report\nvoid SkipLevel() {}\n', project.root)
        report = core.audit(project)
        candidates = self.ids(report)["DEBUG_SOURCE_CANDIDATES"]
        self.assertEqual(candidates["status"], "warn")
        self.assertEqual(len(candidates["evidence"]), 2)
        self.assertNotIn("secret-value-not-for-report", json.dumps(report))

    def test_managed_assembly_and_symbols_fail_even_with_native_dll(self):
        project = self.unity()
        build = self.unity_build()
        self.put("Game_Data/Managed/Assembly-CSharp.dll", b"managed", build)
        self.put("Game.pdb", b"symbols", build)
        result = self.ids(core.audit(project, build))
        self.assertEqual(result["UNITY_BUILD_CODE"]["status"], "fail")
        self.assertEqual(result["BUILD_SYMBOLS"]["status"], "fail")

    def test_no_false_launch_approval_on_clean_layout(self):
        report = core.audit(self.unity(), self.unity_build())
        self.assertEqual(report["automated_gate"], "no_detected_blocker")
        self.assertEqual(report["release_status"], "REQUIRES_MANUAL_REVIEW")
        self.assertEqual(self.ids(report)["RUNTIME_DEBUG_REVIEW"]["status"], "review")

    def test_empty_build_is_not_a_pass(self):
        project = self.unity()
        build = self.root / "empty"
        build.mkdir()
        report = core.audit(project, build)
        self.assertEqual(report["automated_gate"], "failed")

    def test_debug_boot_detects_real_flags_not_comment(self):
        project = self.unity()
        build = self.unity_build()
        boot = self.put("Game_Data/boot.config", "# player-connection-debug=1\nplayer-connection-debug=0\n", build)
        self.assertNotIn("UNITY_DEBUG_BOOT", self.ids(core.audit(project, build)))
        boot.write_text("player-connection-debug=1\n")
        self.assertEqual(self.ids(core.audit(project, build))["UNITY_DEBUG_BOOT"]["status"], "fail")

    def test_asset_containers_do_not_prove_encryption(self):
        project = self.unreal()
        build = self.root / "unreal-build"
        self.put("Demo.exe", b"test-only", build)
        for name in ("Demo.pak", "Demo.utoc", "Demo.ucas"):
            self.put("Demo/Content/Paks/" + name, b"fixture", build)
        self.put("Demo/audio.wav", b"fixture", build)
        result = self.ids(core.audit(project, build))
        self.assertEqual(result["ARCHIVE_REVIEW"]["status"], "review")
        self.assertEqual(result["IOSTORE_ARTIFACT"]["status"], "review")
        self.assertEqual(result["LOOSE_ASSETS"]["status"], "warn")

    def test_steam_appid_and_crypto_files_are_blockers(self):
        project = self.unity()
        build = self.unity_build()
        self.put("steam_appid.txt", "480", build)
        self.put("Config/DefaultCrypto.ini", "private-key-value", build)
        result = core.audit(project, build)
        self.assertEqual(self.ids(result)["PRIVATE_BUILD_FILES"]["status"], "fail")
        self.assertNotIn("private-key-value", json.dumps(result))

    def test_platform_override_remains_manual_review(self):
        project = self.unreal()
        self.config(project)
        self.put("Config/Windows/WindowsGame.ini", f"[{core.PACKAGING}]\nBuildConfiguration=PPBC_Development\n", project.root)
        core.apply(project)
        self.assertEqual(self.ids(core.audit(project))["UE_CONFIG_LAYERS"]["status"], "review")

    def test_stage_keeps_originals_and_verifies_separate_symbols(self):
        build = self.unity_build()
        self.put("Game.pdb", b"private-symbols", build)
        self.put("Game_BackUpThisFolder_ButDontShipItWithYourGame/il2cpp/main.cpp", b"generated-source", build)
        release, symbols = self.root / "release", self.root / "symbols"
        manifest = core.stage_release(build, release, symbols)
        self.assertTrue((build / "Game.pdb").exists())
        self.assertFalse((release / "Game.pdb").exists())
        self.assertEqual((symbols / "Game.pdb").read_bytes(), b"private-symbols")
        self.assertEqual(core.file_digest(build / "Game.exe"), core.file_digest(release / "Game.exe"))
        self.assertEqual(len(manifest["files"]), 5)
        self.assertEqual(json.loads((symbols / "srg-symbol-manifest.json").read_text())["files"], manifest["files"])

    def test_stage_rejects_overlaps_and_existing_outputs(self):
        build = self.unity_build()
        for dest, sym in ((build / "release", self.root / "symbols"), (self.root, self.root / "symbols"),
                          (self.root / "same", self.root / "same")):
            with self.assertRaises(core.GuardError):
                core.stage_release(build, dest, sym)
        self.put("occupied/do-not-touch.txt", "user file")
        with self.assertRaises(core.GuardError):
            core.stage_release(build, self.root / "occupied", self.root / "symbols")
        self.assertEqual((self.root / "occupied/do-not-touch.txt").read_text(), "user file")

    def test_stage_does_not_follow_links(self):
        build = self.unity_build()
        target = self.put("outside.txt", "private")
        link = build / "link.txt"
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest("Host cannot create symlinks; CI Linux runs this case")
        with self.assertRaises(core.GuardError):
            core.stage_release(build, self.root / "release", self.root / "symbols")

    def test_html_escapes_untrusted_project_and_paths(self):
        project = self.unity()
        report = core.audit(project)
        report["project_name"] = '<script>alert("x")</script>'
        report["findings"][0]["evidence"] = ['<img src=x onerror="alert(1)">']
        path = core.save_report(report, self.root / "report")
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("<script>", text)
        self.assertNotIn("<img", text)
        self.assertIn("&lt;script&gt;", text)

    def test_build_command_has_release_flags_and_never_executes(self):
        project = self.unreal()
        self.config(project)
        tool = self.put("Engine With Spaces/RunUAT.bat", "@echo should-not-run")
        script = core.build_script(project, tool, self.root / "build out")
        for option in ("-clientconfig=Shipping", "-nodebuginfo", "-package", "-iostore"):
            self.assertIn(option, script)
        self.assertNotIn("+run_app_build", script)
        self.assertNotIn("Development", script)

    def test_command_rejects_batch_metacharacters(self):
        for value in ("D:/Games/100%/Game", "D:/Games/A&B", "new\ncommand", "bad!path"):
            with self.assertRaises(core.GuardError):
                core.powershell_literal(value)
        self.assertEqual(core.powershell_literal("D:/Game's Folder"), "'D:/Game''s Folder'")

    def test_cli_returns_distinct_operational_and_audit_errors(self):
        project = self.unity()
        build = self.unity_build()
        self.put("Game.pdb", b"fixture", build)
        code, out, err = self.cli("audit", project.root, "--build", build)
        self.assertEqual(code, 2, err)
        self.assertIn("BLOCKED", out)
        code, _, err = self.cli("audit", project.root, "--build", self.root / "missing")
        self.assertEqual(code, 1)
        self.assertIn("does not exist", err)

    def test_invalid_build_input_cannot_partially_apply(self):
        project = self.unity()
        code, _, _ = self.cli("apply", project.root, "--build", self.root / "missing")
        self.assertEqual(code, 1)
        self.assertFalse((project.root / core.UNITY_ADAPTER).exists())

    def test_cli_plan_is_read_only(self):
        project = self.unreal()
        before = list(project.root.rglob("*"))
        code, out, err = self.cli("plan", project.root)
        self.assertEqual(code, 0, err)
        self.assertEqual(before, list(project.root.rglob("*")))
        self.assertIn("Shipping", out)

    def test_report_cannot_overwrite_project_gitignore(self):
        project = self.unity()
        ignore = self.put(".gitignore", "user-data/\n", project.root)
        with self.assertRaisesRegex(core.GuardError, "dedicated"):
            core.save_report(core.audit(project), project.root)
        self.assertEqual(ignore.read_text(), "user-data/\n")
        code, _, _ = self.cli("apply", project.root, "--report-dir", project.root)
        self.assertEqual(code, 1)
        self.assertFalse((project.root / core.UNITY_ADAPTER).exists())

    def test_existing_generated_report_can_be_updated(self):
        project = self.unity()
        directory = self.root / "reports"
        core.save_report(core.audit(project), directory)
        core.save_report(core.audit(project, self.unity_build()), directory)
        self.assertEqual(json.loads((directory / "report.json").read_text(encoding="utf-8"))["inventory"]["file_count"], 3)


if __name__ == "__main__":
    unittest.main()
