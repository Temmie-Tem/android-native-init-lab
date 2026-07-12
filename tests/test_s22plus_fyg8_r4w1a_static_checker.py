import importlib.util
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_r4w1a_static_checker.py"


def load():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_r4w1a_static_checker_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def arm64_kernel(fill, marker=b""):
    data = bytearray([fill] * 128)
    struct.pack_into("<IIQQQQQQII", data, 0, 0x14000008, 0, 0x80000, 128, 0xA,
                     0, 0, 0, 0x644D5241, 0)
    if marker:
        data[96:96 + len(marker)] = marker
    return bytes(data)


class S22PlusFyg8R4W1AStaticCheckerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = load()

    def test_independent_reconstruction_replaces_only_kernel(self):
        names = ("BOOT_SIZE", "KERNEL_START", "KERNEL_END", "KERNEL_SIZE", "R4W1_MARKER")
        old = {name: getattr(self.checker, name) for name in names}
        try:
            self.checker.BOOT_SIZE = 256
            self.checker.KERNEL_START = 64
            self.checker.KERNEL_END = 192
            self.checker.KERNEL_SIZE = 128
            self.checker.R4W1_MARKER = b"R4W1TEST"
            control = bytearray([0xA5] * 256)
            control[64:192] = arm64_kernel(0x11)
            image = arm64_kernel(0x22, b"R4W1TEST")
            candidate = self.checker.reconstruct_candidate(bytes(control), image)
            self.assertEqual(candidate[:64], control[:64])
            self.assertEqual(candidate[64:192], image)
            self.assertEqual(candidate[192:], control[192:])
        finally:
            for name, value in old.items():
                setattr(self.checker, name, value)

    def test_reconstruction_rejects_missing_or_duplicate_marker(self):
        names = ("BOOT_SIZE", "KERNEL_START", "KERNEL_END", "KERNEL_SIZE", "R4W1_MARKER")
        old = {name: getattr(self.checker, name) for name in names}
        try:
            self.checker.BOOT_SIZE = 256
            self.checker.KERNEL_START = 64
            self.checker.KERNEL_END = 192
            self.checker.KERNEL_SIZE = 128
            self.checker.R4W1_MARKER = b"R4"
            control = bytearray(256)
            control[64:192] = arm64_kernel(0x11)
            with self.assertRaises(self.checker.CheckError):
                self.checker.reconstruct_candidate(bytes(control), arm64_kernel(0x22))
            duplicate = bytearray(arm64_kernel(0x22))
            duplicate[96:100] = b"R4R4"
            with self.assertRaises(self.checker.CheckError):
                self.checker.reconstruct_candidate(bytes(control), bytes(duplicate))
        finally:
            for name, value in old.items():
                setattr(self.checker, name, value)

    def test_candidate_validation_rejects_outside_kernel_mutation(self):
        names = ("BOOT_SIZE", "KERNEL_START", "KERNEL_END", "KERNEL_SIZE", "R4W1_MARKER")
        old = {name: getattr(self.checker, name) for name in names}
        try:
            self.checker.BOOT_SIZE = 256
            self.checker.KERNEL_START = 64
            self.checker.KERNEL_END = 192
            self.checker.KERNEL_SIZE = 128
            self.checker.R4W1_MARKER = b"R4W1TEST"
            control = bytearray(256)
            control[64:192] = arm64_kernel(0x11)
            image = arm64_kernel(0x22, b"R4W1TEST")
            expected = self.checker.reconstruct_candidate(bytes(control), image)
            mutated = bytearray(expected)
            mutated[200] ^= 1
            with self.assertRaisesRegex(self.checker.CheckError, "outside delta=1"):
                self.checker.validate_candidate_bytes(bytes(mutated), expected, bytes(control), image)
        finally:
            for name, value in old.items():
                setattr(self.checker, name, value)

    def test_manifest_rejects_live_authorization(self):
        hashes = {"boot_img": "a", "boot_img_lz4": "b", "ap_tar_md5": "c", "kernel": "d"}
        data = {
            "schema": "s22plus_fyg8_r4w1a_candidate_build_v1",
            "verdict": "PASS_R4W1A_ARTIFACT_BUILT_HOST_ONLY",
            "artifacts": {"hashes": hashes},
            "construction": {"r4w1_marker_count": 1, "difference": {"outside_kernel_changed_byte_count": 0}},
            "safety": {
                "device_contact": False, "usb_enumeration": False, "odin_transfer": False,
                "flash": False, "live_authorized": True, "r4w1a_live_authorized": False,
                "boot_only_ap": True, "ap_members": ["boot.img.lz4"],
                "stale_avb_descriptor_semantics_retained": True,
            },
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            path.write_text(json.dumps(data), encoding="ascii")
            with self.assertRaises(self.checker.CheckError):
                self.checker.audit_manifest(path, hashes)

    def test_checker_has_no_direct_device_or_odin_invocation_path(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("subprocess.run", source)
        self.assertNotIn('"adb"', source.lower())
        self.assertNotIn("run_odin", source)
        self.assertNotIn("INVALID_ODIN", source)
        self.assertIn("r3.run_avbtool", source)
        self.assertIn("r3.validate_ap", source)
        self.assertIn('"odin_invocation": False', source)
        self.assertIn('"live_authorized": False', source)


if __name__ == "__main__":
    unittest.main()
