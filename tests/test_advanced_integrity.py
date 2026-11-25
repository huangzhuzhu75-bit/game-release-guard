import json
import unittest

import test_guard as fixtures
from test_advanced_binary import minimal_pe
from steam_release_guard import core
from steam_release_guard.advanced import integrity


class IntegrityTests(unittest.TestCase):
    setUp = fixtures.GuardTests.setUp
    put = fixtures.GuardTests.put
    cli = fixtures.GuardTests.cli

    def release(self):
        self.build = self.root / "build"
        for name in ("Game.exe", "SDK.dll", "audio.bank", "config.ini", "Textures/Hero.dds"):
            self.put(name, name.encode(), self.build)
        self.manifest = self.root / "private/manifest.json"
        self.record = integrity.create(self.build, "r1", self.manifest, ["Saved/*"])

    def verify(self, **kwargs):
        return integrity.verify(self.build, self.manifest, kwargs.get("identifier", "r1"),
                                kwargs.get("pin", self.record["manifest_sha256"]))

    def test_detects_modified_missing_and_added_files_without_mutating(self):
        self.release()
        self.assertEqual(self.verify()["status"], "INTEGRITY_MATCH")
        (self.build / "Game.exe").write_bytes(b"tamper")
        (self.build / "SDK.dll").unlink()
        self.put("extra.dll", b"extra", self.build)
        before = {str(p): p.read_bytes() for p in core.walk_files(self.build)}
        result = self.verify()
        self.assertEqual(result["changed"], ["Game.exe"])
        self.assertEqual(result["missing"], ["SDK.dll"])
        self.assertEqual(result["unexpected"], ["extra.dll"])
        self.assertEqual(before, {str(p): p.read_bytes() for p in core.walk_files(self.build)})

    def test_replaced_manifest_or_wrong_build_never_establishes_trust(self):
        self.release()
        with self.assertRaises(core.GuardError):
            self.verify(identifier="r2")
        self.manifest.write_bytes(self.manifest.read_bytes() + b" ")
        with self.assertRaises(core.GuardError):
            self.verify()

    def test_traversal_duplicate_unknown_schema_block_even_when_hash_matches(self):
        self.release()
        original = json.loads(self.manifest.read_text(encoding="utf-8"))
        for mode in ("path", "duplicate", "schema", "mutable"):
            value = json.loads(json.dumps(original))
            if mode == "path": value["files"][0]["path"] = "../outside"
            elif mode == "duplicate": value["files"].append(value["files"][0])
            elif mode == "schema": value["schema"] = 99
            else: value["mutable"] = ["*"]
            self.manifest.write_text(json.dumps(value), encoding="utf-8")
            with self.subTest(mode=mode), self.assertRaises(core.GuardError):
                self.verify(pin=core.file_digest(self.manifest))

    def test_mutable_files_explicit_and_updates_require_new_baseline(self):
        self.release()
        self.put("Saved/player.json", "user save", self.build)
        self.assertEqual(self.verify()["status"], "INTEGRITY_MATCH")
        (self.build / "Game.exe").write_bytes(b"legitimate update")
        new = self.root / "r2.json"
        record = integrity.create(self.build, "r2", new, ["Saved/*"])
        self.assertEqual(integrity.verify(self.build, new, "r2", record["manifest_sha256"])["status"], "INTEGRITY_MATCH")
        self.assertEqual(self.verify()["status"], "INTEGRITY_MISMATCH")

    def test_preview_and_existing_output_never_write(self):
        self.release()
        with self.assertRaises(core.GuardError):
            integrity.create(self.build, "r1", self.manifest)
        with self.assertRaises(core.GuardError):
            integrity.create(self.build, "r1", self.build / "manifest.json")
        output = self.root / "not-created.json"
        self.assertEqual(self.cli("advanced", "integrity-create", self.build, "--build-id", "r1", "--output", output, "--dry-run", "--json")[0], 0)
        self.assertFalse(output.exists())

    def test_drm_checks_structure_and_preserved_original_without_claiming_wrap(self):
        original = self.put("original.exe", minimal_pe())
        wrapped = self.put("wrapped.exe", minimal_pe() + b"fake change, not Steam DRM")
        result = integrity.drm_inspect(original, wrapped, core.file_digest(original))
        self.assertTrue(result["original_preserved"])
        self.assertEqual(result["wrapper_success"], "NOT_VERIFIED")
        with self.assertRaises(core.GuardError):
            integrity.drm_inspect(original, wrapped, "a" * 64)
