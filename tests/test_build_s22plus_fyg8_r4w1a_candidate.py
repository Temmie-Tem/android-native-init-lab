import hashlib
import importlib.util
import struct
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/build_s22plus_fyg8_r4w1a_candidate.py"
CHECKER = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_r3_static_checker.py"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def arm64_kernel(fill):
    data = bytearray([fill] * 128)
    struct.pack_into(
        "<IIQQQQQQII",
        data,
        0,
        0x14000008,
        0,
        0x80000,
        128,
        0xA,
        0,
        0,
        0,
        0x644D5241,
        0,
    )
    return bytes(data)


class S22PlusFyg8R4W1ACandidateBuilderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = load(SCRIPT, "build_s22plus_fyg8_r4w1a_candidate_tested")
        cls.checker = load(CHECKER, "s22plus_fyg8_r3_checker_for_r4w1a_builder_test")

    def test_candidate_replaces_only_kernel_region(self):
        names = (
            "BOOT_SIZE",
            "KERNEL_START",
            "KERNEL_END",
            "KERNEL_SIZE",
            "EXPECTED_STOCK_KERNEL_SHA256",
            "R4W1_MARKER",
        )
        old = {name: getattr(self.builder, name) for name in names}
        try:
            self.builder.BOOT_SIZE = 256
            self.builder.KERNEL_START = 64
            self.builder.KERNEL_END = 192
            self.builder.KERNEL_SIZE = 128
            stock_kernel = arm64_kernel(0x11)
            rebuilt_kernel = bytearray(arm64_kernel(0x22))
            rebuilt_kernel[96:104] = b"R4W1TEST"
            rebuilt_kernel = bytes(rebuilt_kernel)
            self.builder.R4W1_MARKER = b"R4W1TEST"
            self.builder.EXPECTED_STOCK_KERNEL_SHA256 = hashlib.sha256(stock_kernel).hexdigest()
            control = bytearray([0xA5] * 256)
            control[64:192] = stock_kernel
            candidate = self.builder.build_candidate_bytes(bytes(control), rebuilt_kernel)
            self.assertEqual(candidate[:64], control[:64])
            self.assertEqual(candidate[64:192], rebuilt_kernel)
            self.assertEqual(candidate[192:], control[192:])
            summary = self.builder.changed_summary(bytes(control), candidate)
            self.assertEqual(summary["outside_kernel_changed_byte_count"], 0)
            self.assertGreater(summary["changed_byte_count"], 0)
        finally:
            for name, value in old.items():
                setattr(self.builder, name, value)

    def test_header_mismatch_fails_closed(self):
        names = (
            "BOOT_SIZE",
            "KERNEL_START",
            "KERNEL_END",
            "KERNEL_SIZE",
            "EXPECTED_STOCK_KERNEL_SHA256",
            "R4W1_MARKER",
        )
        old = {name: getattr(self.builder, name) for name in names}
        try:
            self.builder.BOOT_SIZE = 256
            self.builder.KERNEL_START = 64
            self.builder.KERNEL_END = 192
            self.builder.KERNEL_SIZE = 128
            stock_kernel = arm64_kernel(0x11)
            rebuilt_kernel = bytearray(arm64_kernel(0x22))
            rebuilt_kernel[96:104] = b"R4W1TEST"
            rebuilt_kernel[8] ^= 1
            self.builder.R4W1_MARKER = b"R4W1TEST"
            self.builder.EXPECTED_STOCK_KERNEL_SHA256 = hashlib.sha256(stock_kernel).hexdigest()
            control = bytearray(256)
            control[64:192] = stock_kernel
            with self.assertRaises(self.builder.BuildError):
                self.builder.build_candidate_bytes(bytes(control), bytes(rebuilt_kernel))
        finally:
            for name, value in old.items():
                setattr(self.builder, name, value)

    def test_missing_build_bound_marker_fails_closed(self):
        names = (
            "BOOT_SIZE",
            "KERNEL_START",
            "KERNEL_END",
            "KERNEL_SIZE",
            "EXPECTED_STOCK_KERNEL_SHA256",
            "R4W1_MARKER",
        )
        old = {name: getattr(self.builder, name) for name in names}
        try:
            self.builder.BOOT_SIZE = 256
            self.builder.KERNEL_START = 64
            self.builder.KERNEL_END = 192
            self.builder.KERNEL_SIZE = 128
            stock_kernel = arm64_kernel(0x11)
            self.builder.EXPECTED_STOCK_KERNEL_SHA256 = hashlib.sha256(stock_kernel).hexdigest()
            self.builder.R4W1_MARKER = b"missing-marker"
            control = bytearray(256)
            control[64:192] = stock_kernel
            with self.assertRaises(self.builder.BuildError):
                self.builder.build_candidate_bytes(bytes(control), arm64_kernel(0x22))
        finally:
            for name, value in old.items():
                setattr(self.builder, name, value)

    def test_changed_summary_rejects_outside_kernel_delta(self):
        old = (self.builder.KERNEL_START, self.builder.KERNEL_END)
        try:
            self.builder.KERNEL_START = 2
            self.builder.KERNEL_END = 6
            before = bytes(8)
            after = bytearray(before)
            after[7] = 1
            with self.assertRaises(self.builder.BuildError):
                self.builder.changed_summary(before, bytes(after))
        finally:
            self.builder.KERNEL_START, self.builder.KERNEL_END = old

    def test_read_pinned_validates_the_returned_memory_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input.bin"
            payload = b"pinned-r4w1a-input"
            path.write_bytes(payload)
            pin, data = self.builder.read_pinned(
                path, len(payload), hashlib.sha256(payload).hexdigest(), "input"
            )
            self.assertEqual(data, payload)
            self.assertEqual(pin["sha256"], hashlib.sha256(data).hexdigest())
            with self.assertRaises(self.builder.BuildError):
                self.builder.read_pinned(path, len(payload), "0" * 64, "input")

    def test_deterministic_ap_is_one_canonical_member(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = root / "boot.img.lz4"
            payload.write_bytes(b"r4w1a-frame")
            first = root / "first.tar.md5"
            second = root / "second.tar.md5"
            self.builder.write_deterministic_ap(payload, first)
            self.builder.write_deterministic_ap(payload, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            data = first.read_bytes()
            tar_prefix, trailer = data[:-41], data[-41:]
            self.assertEqual(
                trailer,
                f"{hashlib.md5(tar_prefix).hexdigest()}  AP.tar\n".encode(),
            )
            member, parsed = self.checker.parse_single_boot_tar(tar_prefix, True)
            self.assertEqual(member["name"], "boot.img.lz4")
            self.assertEqual(parsed, b"r4w1a-frame")

    def test_source_is_host_only_and_has_no_live_authorization(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"live_authorized": False', source)
        self.assertIn('"r4w1a_live_authorized": False', source)
        self.assertIn('"device_contact": False', source)
        self.assertIn('"ap_members": ["boot.img.lz4"]', source)
        self.assertIn('"outside_kernel_changed_byte_count"', source)
        self.assertIn('"r3c0_post_kernel_bytes_preserved"', source)
        self.assertNotIn('"adb"', source.lower())
        self.assertNotIn("'adb'", source.lower())
        self.assertNotIn('"fastboot"', source.lower())
        self.assertNotIn("'fastboot'", source.lower())

    def test_odin_gate_cannot_enumerate_a_real_device(self):
        self.assertEqual(self.builder.INVALID_ODIN_DEVICE, "/dev/bus/usb/999/999")
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('"-l"', source)
        self.assertIn("failed_before_device_open", source)
        self.assertIn('[pinned_lz4, "--content-size", "-B6", "-f", "-q"', source)
        self.assertIn("pinned_odin", source)
        self.assertIn(".pinned-tools", source)


if __name__ == "__main__":
    unittest.main()
