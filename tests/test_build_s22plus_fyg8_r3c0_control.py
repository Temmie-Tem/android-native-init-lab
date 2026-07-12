import hashlib
import importlib.util
import struct
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/build_s22plus_fyg8_r3c0_control.py"
CHECKER = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_r3_static_checker.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8R3C0ControlBuilderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load(SCRIPT, "build_s22plus_fyg8_r3c0_control_tested")
        cls.checker = load(CHECKER, "s22plus_fyg8_r3_static_checker_for_builder_test")

    def test_expected_control_changes_only_signer_tail_and_footer_size(self):
        old = (
            self.builder.SIGNER_START,
            self.builder.SIGNER_END,
            self.builder.FOOTER_START,
            self.builder.BOOT_SIZE,
        )
        try:
            self.builder.SIGNER_START = 32
            self.builder.SIGNER_END = 64
            self.builder.FOOTER_START = 64
            self.builder.BOOT_SIZE = 128
            stock = bytearray(128)
            stock[32:48] = self.builder.SEANDROID_MAGIC
            stock[48:64] = b"S" * 16
            struct.pack_into("!Q", stock, 76, 64)
            control = self.builder.expected_control_bytes(bytes(stock))
            self.assertEqual(control[32:48], self.builder.SEANDROID_MAGIC)
            self.assertEqual(control[48:64], bytes(16))
            self.assertEqual(struct.unpack_from("!Q", control, 76)[0], 48)
            self.assertEqual(control[:32], stock[:32])
        finally:
            (
                self.builder.SIGNER_START,
                self.builder.SIGNER_END,
                self.builder.FOOTER_START,
                self.builder.BOOT_SIZE,
            ) = old

    def test_deterministic_ap_is_one_canonical_member(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / "boot.img.lz4"
            payload.write_bytes(b"frame")
            first = root / "first.tar.md5"
            second = root / "second.tar.md5"
            self.builder.write_deterministic_ap(payload, first)
            self.builder.write_deterministic_ap(payload, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            data = first.read_bytes()
            tar_prefix, trailer = data[:-41], data[-41:]
            self.assertEqual(trailer, f"{hashlib.md5(tar_prefix).hexdigest()}  AP.tar\n".encode())
            member, parsed = self.checker.parse_single_boot_tar(tar_prefix, True)
            self.assertEqual(member["name"], "boot.img.lz4")
            self.assertEqual(parsed, b"frame")

    def test_manifest_contract_has_no_live_authorization(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"live_authorized": False', source)
        self.assertIn('"r3c1_authorized": False', source)
        self.assertIn('"device_contact": False', source)
        self.assertIn('"ap_members": ["boot.img.lz4"]', source)
        self.assertNotIn('"adb"', source.lower())
        self.assertNotIn("'adb'", source.lower())
        self.assertNotIn('"fastboot"', source.lower())
        self.assertNotIn("'fastboot'", source.lower())
        self.assertIn('"magiskboot_executed": False', source)
        self.assertIn('"tool": "direct fixed-offset transformation of pinned stock boot"', source)
        self.assertNotIn('[magiskboot, "unpack"', source)
        self.assertNotIn('[magiskboot, "repack"', source)

    def test_odin_gate_is_fixed_to_nonexistent_path(self):
        self.assertEqual(self.builder.INVALID_ODIN_DEVICE, "/dev/bus/usb/999/999")
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('"-l"', source)
        self.assertIn("failed_before_device_open", source)
        self.assertIn('[lz4, "--content-size", "-B6", "-f", "-q"', source)


if __name__ == "__main__":
    unittest.main()
