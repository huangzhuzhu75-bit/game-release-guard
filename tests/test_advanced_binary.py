import json
import struct
import unittest

import test_guard as fixtures
from steam_release_guard import core
from steam_release_guard.advanced.binary import pe_info, unity_audit, literal_candidates


def minimal_pe(managed=False):
    """Synthetic structural PE fixture, NOT a working game/native dependency."""
    data = bytearray(2048)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3c, 128)
    data[128:132] = b"PE\0\0"
    struct.pack_into("<HH", data, 132, 0x8664, 1)
    struct.pack_into("<H", data, 148, 240)
    struct.pack_into("<H", data, 152, 0x20b)
    struct.pack_into("<I", data, 260, 16)
    struct.pack_into("<IIII", data, 400, 1024, 0x1000, 1024, 512)
    if managed:
        struct.pack_into("<II", data, 264 + 14 * 8, 0x1000, 72)
        struct.pack_into("<II", data, 520, 0x1100, 100)
        data[768:772] = b"BSJB"
    return bytes(data)


class BinaryTests(unittest.TestCase):
    setUp = fixtures.GuardTests.setUp
    put = fixtures.GuardTests.put
    unity = fixtures.GuardTests.unity

    def test_valid_native_and_managed_structures_are_distinct(self):
        self.assertFalse(pe_info(self.put("native.dll", minimal_pe()))["managed"])
        self.assertTrue(pe_info(self.put("managed.dll", minimal_pe(True)))["managed"])

    def test_truncated_headers_and_unbacked_clr_are_rejected(self):
        for content in (b"MZ", minimal_pe()[:500], b"not PE"):
            with self.assertRaises(core.GuardError):
                pe_info(self.put("broken.dll", content))
        data = bytearray(minimal_pe(True))
        struct.pack_into("<I", data, 520, 0xffffff00)
        with self.assertRaises(core.GuardError):
            pe_info(self.put("bad-clr.dll", data))

    def test_header_mismatch_absence_and_rename_are_never_encryption_proof(self):
        project = self.unity()
        build = self.root / "build"
        path = self.put("global-metadata.dat", b"renamed-compressed-unknown", build)
        report = unity_audit(project, build)
        metadata = next(f for f in report["findings"] if f["id"] == "IL2CPP_METADATA")
        self.assertEqual(metadata["status"], "NOT_VERIFIED")
        path.write_bytes(struct.pack("<II", 0xfab11baf, 31))
        report = unity_audit(project, build)
        self.assertEqual(next(f for f in report["findings"] if f["id"] == "IL2CPP_METADATA")["status"], "REVIEW")
        self.assertFalse(any(f["status"] == "PASS" for f in report["findings"]))

    def test_secret_findings_redact_values_and_do_not_delete_modules(self):
        project = self.unity()
        build = self.root / "build"
        file = self.put("SDK.dll", minimal_pe() + b'api_key="private_value_123456"', build)
        original = file.read_bytes()
        report = unity_audit(project, build)
        self.assertIn("BINARY_SECRET_CANDIDATE", json.dumps(report))
        self.assertNotIn("private_value_123456", json.dumps(report))
        self.assertEqual(original, file.read_bytes())
        boundary = self.put("boundary.bin", b"x" * 65530 + b'\nclient_secret="private_value_123456"')
        self.assertEqual(len(literal_candidates(boundary)), 1)
