"""Failure behavior on synthetic fixtures; these are not engine protection tests."""
import errno
import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

import test_guard as fixtures
from steam_release_guard import core, staging, transactions
from steam_release_guard.operations import Cancelled, Operation, load_journal, seal, writer


class P0Tests(unittest.TestCase):
    setUp = fixtures.GuardTests.setUp
    put = fixtures.GuardTests.put
    unity = fixtures.GuardTests.unity
    unreal = fixtures.GuardTests.unreal
    config = fixtures.GuardTests.config
    unity_build = fixtures.GuardTests.unity_build
    cli = fixtures.GuardTests.cli
    ids = fixtures.GuardTests.ids

    def setUp(self):
        fixtures.GuardTests.setUp(self)
        patch = mock.patch.dict(os.environ, {"SRG_LOCK_DIRECTORY": str(self.root / "locks")})
        patch.start()
        self.addCleanup(patch.stop)

    def child(self, script, *arguments):
        proc = subprocess.Popen([sys.executable, "-c", script, *map(str, arguments)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

        def stop():
            if proc.poll() is None:
                proc.kill()
            proc.communicate(timeout=10)
        self.addCleanup(stop)
        return proc

    def ready(self, path, proc):
        deadline = time.monotonic() + 15
        while not path.exists() and time.monotonic() < deadline and proc.poll() is None:
            time.sleep(.02)
        if not path.exists():
            if proc.poll() is None:
                proc.kill()
            _, error = proc.communicate(timeout=10)
            self.fail("Child did not reach interruption point: " + error.decode(errors="replace"))

    def stage_paths(self):
        return self.unity_build(), self.root / "release", self.root / "symbols"

    def interrupted_stage(self):
        build, release, symbols = self.stage_paths()

        def fail(source, partial, *args):
            partial.write_bytes(source.read_bytes()[:3])
            raise OSError(errno.ENOSPC, "private-value-must-not-appear")
        with mock.patch.object(staging, "_copy", side_effect=fail):
            with self.assertRaisesRegex(core.GuardError, "INCOMPLETE") as caught:
                core.stage_release(build, release, symbols)
        self.assertNotIn("private-value", str(caught.exception))
        return build, release, symbols, symbols / staging.JOURNAL

    def test_process_lock_blocks_apply_rollback_stage_and_releases_on_kill(self):
        project = self.unreal()
        core.apply(project)
        ready = self.root / "ready"
        proc = self.child('''import sys,time
from pathlib import Path
from steam_release_guard.operations import writer
with writer():
    Path(sys.argv[1]).write_text('ready')
    time.sleep(60)
''', ready)
        self.ready(ready, proc)
        build, release, symbols = self.stage_paths()
        for call in (lambda: core.apply(project), lambda: core.rollback(project),
                     lambda: core.stage_release(build, release, symbols)):
            with self.assertRaisesRegex(core.GuardError, "lock"):
                call()
        proc.kill()
        proc.wait(timeout=10)
        core.rollback(project)
        core.stage_release(build, release, symbols)

    def test_killed_apply_recovers_from_durable_journal(self):
        project = self.unreal()
        config = self.config(project)
        before = config.read_bytes()
        ready = self.root / "ready"
        proc = self.child('''import sys,time
from pathlib import Path
from steam_release_guard import core
write=core.atomic_write
def interrupt(path,data):
    write(path,data)
    if path.name=='.gitignore' and path.parent==Path(sys.argv[1]):
        Path(sys.argv[2]).write_text('ready')
        time.sleep(60)
core.atomic_write=interrupt
core.apply(core.detect_project(sys.argv[1]))
''', project.root, ready)
        self.ready(ready, proc)
        proc.kill()
        proc.wait(timeout=10)
        self.assertTrue(transactions.pending(project))
        self.assertEqual(self.ids(core.audit(project))["INCOMPLETE_PROJECT_TRANSACTION"]["status"], "fail")
        with self.assertRaisesRegex(core.GuardError, "rollback"):
            core.apply(project)
        core.rollback(project)
        self.assertEqual(config.read_bytes(), before)
        self.assertFalse((project.root / ".gitignore").exists())

    def test_journal_damage_and_duplicate_targets_block_all_restore(self):
        project = self.unreal()
        config = self.config(project)
        manifest = core.apply(project)
        original = manifest.read_bytes()
        after = config.read_bytes()
        for mode in ("count", "status", "hash", "duplicate", "version", "downgrade"):
            journal = json.loads(original)
            if mode == "count":
                journal["file_count"] += 1
                seal(journal)
            elif mode == "status":
                journal["status"] = "ready-ish"
                seal(journal)
            elif mode == "hash":
                journal["files"][0]["after_sha256"] = "f" * 64
            elif mode == "duplicate":
                journal["files"][1]["path"] = journal["files"][0]["path"]
                seal(journal)
            elif mode == "version":
                journal["schema"] = 99
                seal(journal)
            else:
                journal["schema"] = 1
            core.write_json(manifest, journal)
            with self.assertRaises(core.GuardError):
                core.rollback(project)
            self.assertEqual(config.read_bytes(), after)
        manifest.write_bytes(original)
        core.rollback(project)

    def test_legacy_schema1_rollback_remains_usable(self):
        project = self.unreal()
        config = self.config(project)
        before = config.read_bytes()
        manifest = core.apply(project)
        journal = json.loads(manifest.read_text(encoding="utf-8"))
        journal["schema"] = 1
        journal["root"] = str(project.root).replace("\\\\?\\", "")  # v0.1 used normal Windows paths
        for field in ("integrity_sha256", "file_count", "operation"):
            journal.pop(field)
        core.write_json(manifest, journal)
        self.assertTrue(transactions.rollback_preview(project)["legacy_journal"])
        core.rollback(project)
        self.assertEqual(config.read_bytes(), before)
        self.assertEqual(load_journal(manifest, "apply")["status"], "rolled_back")

    def test_insufficient_space_prevents_payload_writes(self):
        project = self.unreal()
        config = self.config(project)
        original = config.read_bytes()
        build, release, symbols = self.stage_paths()
        with mock.patch("steam_release_guard.operations.shutil.disk_usage", return_value=mock.Mock(free=0)):
            with self.assertRaisesRegex(core.GuardError, "space"):
                core.apply(project)
            with self.assertRaisesRegex(core.GuardError, "space"):
                core.stage_release(build, release, symbols)
        self.assertEqual(config.read_bytes(), original)
        self.assertFalse((project.root / ".gitignore").exists())
        self.assertFalse(release.exists())

    def test_backup_disk_full_cleans_preparation(self):
        project = self.unreal()
        config = self.config(project)
        before = config.read_bytes()
        write = core.atomic_write

        def fail(path, data):
            if path.suffix == ".bak":
                raise OSError(errno.ENOSPC, "disk full")
            return write(path, data)
        with mock.patch.object(core, "atomic_write", side_effect=fail):
            with self.assertRaises(OSError):
                core.apply(project)
        self.assertEqual(config.read_bytes(), before)
        self.assertEqual(list((project.root / core.STATE).rglob("*.bak")), [])
        self.assertEqual(list(transactions.manifests(project)), [])

    def test_rollback_failure_can_be_retried(self):
        project = self.unreal()
        config = self.config(project)
        before = config.read_bytes()
        manifest = core.apply(project)
        write = core.atomic_write

        def occupied(path, data):
            if path == config:
                raise PermissionError(errno.EACCES, "file in use")
            return write(path, data)
        with mock.patch.object(core, "atomic_write", side_effect=occupied):
            with self.assertRaisesRegex(core.GuardError, "Rollback interrupted"):
                core.rollback(project)
        self.assertEqual(load_journal(manifest, "apply")["status"], "rollback_incomplete")
        core.rollback(project)
        self.assertEqual(config.read_bytes(), before)

    @unittest.skipUnless(os.name == "nt", "Windows sharing-violation test")
    def test_actual_windows_occupied_config_preserves_recovery(self):
        import ctypes
        from ctypes import wintypes
        project = self.unreal()
        config = self.config(project)
        before = config.read_bytes()
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.CreateFileW(str(config), 0x80000000, 1, None, 3, 0, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        try:
            with self.assertRaisesRegex(core.GuardError, "interrupted"):
                core.apply(project)
            self.assertEqual(config.read_bytes(), before)
        finally:
            kernel.CloseHandle(handle)
        core.rollback(project)
        self.assertEqual(config.read_bytes(), before)

    def test_preview_change_blocks_stale_apply(self):
        project = self.unreal()
        config = self.config(project)
        preview = core.plan(project)
        config.write_bytes(config.read_bytes() + b"; subsequent user edit\n")
        with self.assertRaisesRegex(core.GuardError, "preview"):
            core.apply(project, expected_plan=preview)
        self.assertIn(b"subsequent user edit", config.read_bytes())
        self.assertFalse((project.root / ".gitignore").exists())

    def test_cancel_before_commit_and_ignore_cancel_during_commit(self):
        project = self.unreal()
        config = self.config(project)
        before = config.read_bytes()
        op = Operation()
        op.cancel.set()
        with self.assertRaises(Cancelled):
            core.apply(project, operation=op)
        self.assertEqual(config.read_bytes(), before)
        op = Operation(lambda event: op.cancel.set() if not event["cancellable"] else None)
        manifest = core.apply(project, operation=op)
        self.assertEqual(load_journal(manifest, "apply")["status"], "applied")
        core.rollback(project)
        self.assertEqual(config.read_bytes(), before)

    def test_long_chinese_paths_stage_and_rollback(self):
        deep = self.root / ("工程路径" * 8) / ("版本目录" * 8) / ("长文件夹" * 8)
        self.put("Demo.uproject", '{"EngineAssociation":"5.6"}', deep)
        project = core.detect_project(deep)
        config = self.config(project)
        before = config.read_bytes()
        core.apply(project)
        core.rollback(project)
        self.assertEqual(config.read_bytes(), before)
        self.put("游戏.exe", "原始数据", deep / "构建")
        core.stage_release(deep / "构建", deep / "发布", deep / "私有符号")
        self.assertEqual((deep / "构建/游戏.exe").read_bytes(), (deep / "发布/游戏.exe").read_bytes())

    def test_stage_failure_is_blocked_and_verified_cleanup_is_repeatable(self):
        build, release, symbols, manifest = self.interrupted_stage()
        originals = {p: p.read_bytes() for p in core.walk_files(build)}
        self.assertEqual(self.ids(core.audit(self.unity(), release))["INCOMPLETE_STAGE"]["status"], "fail")
        result = staging.cleanup_stage(manifest)
        self.assertEqual(result["status"], "CLEANED")
        self.assertEqual(list(release.iterdir()), [])
        self.assertEqual(staging.cleanup_stage(manifest)["removed"], 0)
        for path, data in originals.items():
            self.assertEqual(path.read_bytes(), data)

    def test_cleanup_refuses_unknown_files_and_modified_partial(self):
        _, release, _, manifest = self.interrupted_stage()
        unknown = self.put("user-notes.txt", "keep", release)
        with self.assertRaisesRegex(core.GuardError, "unrecognized"):
            staging.cleanup_stage(manifest)
        self.assertEqual(unknown.read_text(), "keep")
        unknown.unlink()
        partial = next(release.rglob("*.srg-part-*"))
        partial.write_bytes(b"different")
        with self.assertRaisesRegex(core.GuardError, "partial"):
            staging.cleanup_stage(manifest)
        self.assertEqual(partial.read_bytes(), b"different")

    def test_killed_stage_can_safely_clean_partial_copy(self):
        build, release, symbols = self.stage_paths()
        ready = self.root / "ready"
        proc = self.child('''import sys,time
from pathlib import Path
from steam_release_guard import core,staging
def interrupt(source,partial,*args):
    partial.write_bytes(source.read_bytes()[:5])
    Path(sys.argv[4]).write_text('ready')
    time.sleep(60)
staging._copy=interrupt
core.stage_release(*map(Path,sys.argv[1:4]))
''', build, release, symbols, ready)
        self.ready(ready, proc)
        proc.kill()
        proc.wait(timeout=10)
        self.assertEqual(json.loads((release / staging.MARKER).read_text())["status"], "INCOMPLETE")
        staging.cleanup_stage(symbols / staging.JOURNAL)
        self.assertEqual(list(release.iterdir()), [])
        self.assertTrue((build / "Game.exe").exists())

    def test_stage_cancel_keeps_journal_and_completed_stage_cannot_be_cleaned(self):
        build, release, symbols = self.stage_paths()
        op = Operation(lambda event: op.cancel.set() if event["phase"] == "copying verified files" else None)
        with self.assertRaises(Cancelled):
            core.stage_release(build, release, symbols, operation=op)
        staging.cleanup_stage(symbols / staging.JOURNAL)
        release2, symbols2 = self.root / "release2", self.root / "symbols2"
        core.stage_release(build, release2, symbols2)
        with self.assertRaisesRegex(core.GuardError, "completed"):
            staging.cleanup_stage(symbols2 / staging.JOURNAL)
        self.assertEqual((release2 / "Game.exe").read_bytes(), (build / "Game.exe").read_bytes())

    def test_cli_json_confirmation_and_preview_do_not_mutate(self):
        project = self.unreal()
        original = list(project.root.rglob("*"))
        for options, expected in ((["--json"], 3), (["--dry-run", "--json"], 0)):
            code, out, err = self.cli("apply", project.root, *options)
            self.assertEqual(code, expected, err)
            self.assertEqual(json.loads(out)["command"], "apply")
            self.assertEqual(original, list(project.root.rglob("*")))
        code, out, err = self.cli("--json", "apply", project.root, "--yes")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["status"], "REQUIRES_MANUAL_REVIEW")
        code, out, _ = self.cli("rollback", project.root, "--yes", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["status"], "COMPLETE")

    def test_unexpected_exception_has_json_error_without_sensitive_contents(self):
        project = self.unreal()
        with mock.patch("steam_release_guard.cli.plan", side_effect=RuntimeError("secret-password")):
            code, out, err = self.cli("plan", project.root, "--json")
        self.assertEqual(code, 1)
        self.assertEqual(err, "")
        self.assertNotIn("secret-password", out)
        self.assertIn("RuntimeError", json.loads(out)["error"])
        code, out, _ = self.cli("nonsense", "--json")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["status"], "ERROR")

    def test_audit_can_cancel_before_scanning_without_writing_project(self):
        project = self.unity()
        before = list(project.root.rglob("*"))
        op = Operation(lambda event: op.cancel.set())
        with self.assertRaises(Cancelled):
            core.audit(project, operation=op)
        self.assertEqual(list(project.root.rglob("*")), before)

    def test_valid_long_asset_filename_is_not_lengthened_by_staging(self):
        build, release, symbols = self.stage_paths()
        name = "音频" + "a" * 220 + ".wav"
        source = self.put(name, b"original-audio", core.absolute_path(build))
        self.addCleanup(source.unlink, missing_ok=True)
        target = core.absolute_path(release) / name
        self.addCleanup(target.unlink, missing_ok=True)
        core.stage_release(build, release, symbols)
        self.assertEqual(target.read_bytes(), source.read_bytes())
