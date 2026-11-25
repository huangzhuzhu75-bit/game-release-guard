"""Full project backup/restore contracts, including failures before adaptation."""
import errno
import json
import os
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

import test_guard as fixtures
from steam_release_guard import core, project_backup as backups
from steam_release_guard.operations import Cancelled, Operation, seal


class FullBackupTests(unittest.TestCase):
    put = fixtures.GuardTests.put
    unity = fixtures.GuardTests.unity
    unreal = fixtures.GuardTests.unreal
    config = fixtures.GuardTests.config
    cli = fixtures.GuardTests.cli

    def setUp(self):
        fixtures.GuardTests.setUp(self)
        patch = mock.patch.dict(os.environ, {"SRG_LOCK_DIRECTORY": str(self.root / "locks")})
        patch.start()
        self.addCleanup(patch.stop)
        self.project = self.unity()
        for name in (".hidden", ".git/objects/example", "Library/cache.bin", "Assets/音效.wav", "Assets/音效.wav.meta",
                     "Builds/Demo.exe", "Tools/build.bat"):
            self.put(name, name.encode("utf-8") + b"\0payload", self.project.root)
        (self.project.root / "Assets/Empty Folder").mkdir()
        self.destination = self.root / "private-full-backups"

    def contents(self, root):
        return {p.relative_to(root).as_posix(): p.read_bytes() for p in core.walk_files(root)}

    def create(self):
        result = backups.create(self.project, self.destination)
        return Path(result["backup_path"])

    def test_backup_and_restore_include_hidden_cache_git_meta_and_empty_directories(self):
        before = self.contents(self.project.root)
        snapshot = self.create()
        payload = snapshot / backups.PAYLOAD
        self.assertEqual(before, self.contents(payload))
        self.assertEqual(before, self.contents(self.project.root))
        self.assertTrue((payload / "Assets/Empty Folder").is_dir())
        self.assertNotEqual((payload / "Assets/音效.wav").stat().st_ino,
                            (self.project.root / "Assets/音效.wav").stat().st_ino)
        (self.project.root / "Assets/音效.wav").write_bytes(b"later user changes")
        self.assertEqual(backups.verify(snapshot)["status"], "VERIFIED")
        restored = self.root / "restored"
        result = backups.restore(snapshot, restored)
        self.assertEqual(result["status"], "COMPLETE")
        self.assertEqual(before, self.contents(restored))
        self.assertTrue((restored / "Assets/Empty Folder").is_dir())
        self.assertEqual((self.project.root / "Assets/音效.wav").read_bytes(), b"later user changes")
        self.assertEqual(backups.verify(snapshot)["status"], "VERIFIED")

    def test_apply_has_verified_full_copy_before_first_project_file_write(self):
        before = self.contents(self.project.root)
        original = core.atomic_write
        observed = []

        def inspect(path, data):
            if path == self.project.root / ".gitignore":
                snapshots = list(self.destination.iterdir())
                self.assertEqual(len(snapshots), 1)
                self.assertEqual(backups.verify(snapshots[0])["status"], "VERIFIED")
                self.assertEqual(self.contents(snapshots[0] / backups.PAYLOAD), before)
                observed.append(True)
            return original(path, data)
        with mock.patch.object(core, "atomic_write", side_effect=inspect):
            journal = core.apply(self.project, backup_dir=self.destination)
        self.assertEqual(observed, [True])
        full = json.loads(journal.read_text(encoding="utf-8"))["full_backup"]
        self.assertEqual(full["status"], "COMPLETE")
        self.assertTrue(Path(full["backup_path"]).is_dir())
        core.rollback(self.project)
        self.assertTrue(Path(full["backup_path"]).is_dir(), "Rollback must retain the independent snapshot")

    def test_full_backup_failure_prevents_every_project_mutation(self):
        before = self.contents(self.project.root)

        def fail(source, target, expected, op):
            target.write_bytes(b"partial")
            raise OSError(errno.ENOSPC, "private-secret-must-not-appear")
        with mock.patch.object(backups, "_copy", side_effect=fail):
            with self.assertRaisesRegex(core.GuardError, "Full backup failed") as caught:
                core.apply(self.project, backup_dir=self.destination)
        self.assertNotIn("private-secret", str(caught.exception))
        self.assertEqual(before, self.contents(self.project.root))
        self.assertFalse((self.project.root / core.STATE).exists())
        snapshot = next(self.destination.iterdir())
        with self.assertRaisesRegex(core.GuardError, "INCOMPLETE"):
            backups.verify(snapshot)
        with self.assertRaises(core.GuardError):
            backups.restore(snapshot, self.root / "cannot-restore")
        self.assertFalse((self.root / "cannot-restore").exists())

    def test_insufficient_space_does_not_create_snapshot_or_change_project(self):
        before = self.contents(self.project.root)
        usage = shutil.disk_usage(self.root)
        with mock.patch("steam_release_guard.operations.shutil.disk_usage", return_value=usage._replace(free=1)):
            with self.assertRaisesRegex(core.GuardError, "space"):
                core.apply(self.project, backup_dir=self.destination)
        self.assertEqual(before, self.contents(self.project.root))
        self.assertFalse(self.destination.exists())

    def test_changed_source_or_corrupt_copy_never_allows_apply(self):
        original = backups._copy
        for mode in ("source", "copy"):
            destination = self.root / mode
            changed = []

            def alter(source, target, expected, op):
                result = original(source, target, expected, op)
                if not changed:
                    (source if mode == "source" else target).write_bytes(("changed " + mode).encode())
                    changed.append(True)
                return result
            with self.subTest(mode=mode), mock.patch.object(backups, "_copy", side_effect=alter):
                with self.assertRaises(core.GuardError):
                    core.apply(self.project, backup_dir=destination)
            self.assertFalse((self.project.root / ".gitignore").exists())
            self.assertFalse((self.project.root / core.UNITY_ADAPTER).exists())
            with self.assertRaisesRegex(core.GuardError, "INCOMPLETE"):
                backups.verify(next(destination.iterdir()))

    def test_cancel_between_verified_backup_and_apply_preserves_original(self):
        before = self.contents(self.project.root)
        op = Operation(lambda event: op.cancel.set() if event.get("backup_path") else None)
        with self.assertRaises(Cancelled):
            core.apply(self.project, backup_dir=self.destination, operation=op)
        self.assertEqual(before, {k: v for k, v in self.contents(self.project.root).items() if not k.startswith(core.STATE + "/")})
        self.assertEqual(backups.verify(next(self.destination.iterdir()))["status"], "VERIFIED")

    def test_cancel_during_copy_leaves_incomplete_backup(self):
        before = self.contents(self.project.root)
        op = Operation(lambda e: op.cancel.set() if e["phase"] == "copying full project backup" and e["current"] == 1 else None)
        with self.assertRaises(Cancelled):
            backups.create(self.project, self.destination, operation=op)
        self.assertEqual(before, self.contents(self.project.root))
        with self.assertRaisesRegex(core.GuardError, "INCOMPLETE"):
            backups.verify(next(self.destination.iterdir()))

    def test_corruption_unknown_files_and_missing_empty_directory_block_restore_before_write(self):
        for mode in ("corrupt", "extra", "empty_dir"):
            snapshot = self.create()
            if mode == "corrupt":
                (snapshot / backups.PAYLOAD / "Assets/音效.wav").write_bytes(b"corrupt")
            elif mode == "extra":
                (snapshot / backups.PAYLOAD / "unknown.txt").write_bytes(b"unexpected")
            else:
                (snapshot / backups.PAYLOAD / "Assets/Empty Folder").rmdir()
            output = self.root / ("restore-" + mode)
            with self.subTest(mode=mode), self.assertRaises(core.GuardError):
                backups.restore(snapshot, output)
            self.assertFalse(output.exists())
            self.assertFalse(output.with_name(output.name + ".srg-restore.json").exists())

    def test_manifest_traversal_duplicates_and_tampering_are_rejected(self):
        snapshot = self.create()
        manifest = snapshot / backups.MANIFEST
        original = json.loads(manifest.read_text(encoding="utf-8"))
        for mode in ("hash", "traversal", "duplicate", "parent", "incomplete"):
            record = json.loads(json.dumps(original))
            if mode == "hash":
                record["files"][0]["sha256"] = "0" * 64
            elif mode == "traversal":
                record["files"][0]["path"] = "../outside"
                seal(record)
            elif mode == "duplicate":
                record["files"].append(record["files"][0])
                record["file_count"] += 1
                seal(record)
            elif mode == "parent":
                record["directories"].remove("Assets")
                seal(record)
            else:
                record["status"] = "INCOMPLETE"
                seal(record)
            manifest.write_text(json.dumps(record), encoding="utf-8")
            with self.subTest(mode=mode), self.assertRaises(core.GuardError):
                backups.restore(snapshot, self.root / "rejected")
            self.assertFalse((self.root / "rejected").exists())

    def test_nested_and_existing_destinations_never_overwrite(self):
        for path in (self.project.root, self.project.root / "backups", self.project.root.parent):
            with self.subTest(path=path), self.assertRaises(core.GuardError):
                backups.create(self.project, path)
        snapshot = self.create()
        existing = self.root / "existing"
        existing.mkdir()
        (existing / "keep").write_bytes(b"user file")
        for path in (existing, self.project.root, self.project.root / "restore", snapshot / "restore"):
            with self.subTest(path=path), self.assertRaises(core.GuardError):
                backups.restore(snapshot, path)
        self.assertEqual((existing / "keep").read_bytes(), b"user file")

    def test_restored_transaction_history_supports_rollback_and_second_generation_restore(self):
        before = self.contents(self.project.root)
        core.apply(self.project, backup_dir=self.destination)
        snapshot = self.create()
        output = self.root / "with-history"
        backups.restore(snapshot, output)
        restored_project = core.detect_project(output)
        core.rollback(restored_project)
        payload = {k: v for k, v in self.contents(output).items() if not k.startswith(core.STATE + "/")}
        self.assertEqual(before, payload)
        second = backups.create(restored_project, self.root / "second-backups")
        again = self.root / "restored-again"
        backups.restore(second["backup_path"], again)
        self.assertIsNotNone(core.apply(core.detect_project(again), backup_dir=self.root / "third-backups"))
        self.assertTrue((self.project.root / core.UNITY_ADAPTER).exists(), "Original project stays adapted")

    def test_incomplete_restore_receipt_blocks_apply_and_audit(self):
        receipt = self.project.root.with_name(self.project.root.name + ".srg-restore.json")
        receipt.write_text(json.dumps({"status": "INCOMPLETE", "output": str(self.project.root)}), encoding="utf-8")
        before = self.contents(self.project.root)
        with self.assertRaisesRegex(core.GuardError, "restoration is incomplete"):
            core.apply(self.project, backup_dir=self.destination)
        self.assertEqual(before, self.contents(self.project.root))
        report = core.audit(self.project)
        self.assertEqual(report["release_status"], "BLOCKED")
        self.assertTrue(any(f["id"] == "INCOMPLETE_FULL_RESTORE" and f["status"] == "fail" for f in report["findings"]))

    def test_restore_failure_preserves_original_and_records_incomplete(self):
        snapshot = self.create()
        before = self.contents(self.project.root)
        original_copy = backups._copy
        copied = []

        def fail(source, target, expected, op):
            if copied:
                target.write_bytes(b"partial")
                raise OSError(errno.ENOSPC, "injected")
            copied.append(True)
            return original_copy(source, target, expected, op)
        output = self.root / "partial-restore"
        with mock.patch.object(backups, "_copy", side_effect=fail), self.assertRaisesRegex(core.GuardError, "incomplete"):
            backups.restore(snapshot, output)
        receipt = json.loads(output.with_name(output.name + ".srg-restore.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["status"], "INCOMPLETE")
        self.assertEqual(before, self.contents(self.project.root))
        self.assertEqual(backups.verify(snapshot)["status"], "VERIFIED")

    def test_cli_preview_confirmation_verify_restore_and_custom_apply_destination(self):
        before = self.contents(self.project.root)
        code, text, _ = self.cli("backup", self.project.root, "--backup-dir", self.destination, "--dry-run", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)["status"], "PREVIEW")
        self.assertFalse(self.destination.exists())
        self.assertEqual(self.cli("backup", self.project.root, "--json")[0], 3)
        self.assertEqual(before, self.contents(self.project.root))
        code, text, _ = self.cli("backup", self.project.root, "--backup-dir", self.destination, "--yes", "--json")
        self.assertEqual(code, 0, text)
        snapshot = json.loads(text)["result"]["backup_path"]
        code, text, _ = self.cli("backup-verify", snapshot, "--json")
        self.assertEqual((code, json.loads(text)["status"]), (0, "VERIFIED"))
        output = self.root / "cli-restored"
        self.assertEqual(self.cli("backup-restore", snapshot, "--output", output, "--json")[0], 3)
        self.assertFalse(output.exists())
        code, text, _ = self.cli("backup-restore", snapshot, "--output", output, "--yes", "--json")
        self.assertEqual(code, 0, text)
        self.assertEqual(before, self.contents(output))
        code, text, _ = self.cli("apply", self.project.root, "--backup-dir", self.destination, "--yes", "--json")
        self.assertEqual(code, 0, text)
        self.assertEqual(json.loads(text)["result"]["full_backup"]["status"], "COMPLETE")

    def test_junction_or_symlink_is_refused_without_copying_external_files(self):
        external = self.root / "external"
        external.mkdir()
        (external / "secret").write_bytes(b"must not be copied")
        link = self.project.root / "linked"
        if os.name == "nt":
            process = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(external)], capture_output=True)
            if process.returncode:
                self.skipTest("Host cannot create a test junction")
            self.addCleanup(lambda: link.rmdir() if link.exists() else None)
        else:
            link.symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(core.GuardError, "symlinks/junctions"):
            backups.create(self.project, self.destination)
        self.assertFalse(self.destination.exists())
        self.assertEqual((external / "secret").read_bytes(), b"must not be copied")

    def test_killed_full_backup_cannot_be_restored_or_used_for_adaptation(self):
        before = self.contents(self.project.root)
        ready = self.root / "ready"
        script = '''import sys,time
from pathlib import Path
from steam_release_guard import core,project_backup
def pause(source,target,expected,op):
    target.write_bytes(b'partial')
    Path(sys.argv[3]).write_text('ready')
    time.sleep(60)
project_backup._copy=pause
core.apply(core.detect_project(sys.argv[1]),backup_dir=Path(sys.argv[2]))
'''
        child = subprocess.Popen([sys.executable, "-c", script, str(self.project.root), str(self.destination), str(ready)],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 15
            while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(.02)
            self.assertTrue(ready.exists(), "Child failed to reach partial full backup")
            child.kill()
            child.communicate(timeout=10)
            self.assertEqual(before, self.contents(self.project.root))
            with self.assertRaisesRegex(core.GuardError, "INCOMPLETE"):
                backups.verify(next(self.destination.iterdir()))
            # OS lock released; a new backup and adaptation can proceed safely.
            self.assertIsNotNone(core.apply(self.project, backup_dir=self.destination))
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)
