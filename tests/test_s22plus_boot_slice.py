import hashlib
import importlib.util
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_boot_slice.py"


def load():
    spec = importlib.util.spec_from_file_location("s22plus_boot_slice_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def arm64_image(size=128):
    data = bytearray(size)
    struct.pack_into(
        "<IIQQQQQQII", data, 0, 0x14000008, 0, 0, size, 10, 0, 0, 0, 0x644D5241, 0
    )
    return bytes(data)


class S22PlusBootSliceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load()

    def test_fixed_interval_replacement_and_outside_check(self):
        carrier = b"abcdefghij"
        candidate = self.module.replace_fixed_interval(carrier, b"XYZ", 3, 6)
        self.assertEqual(candidate, b"abcXYZghij")
        summary = self.module.diff_outside_interval(carrier, candidate, 3, 6)
        self.assertEqual(summary["outside_interval_changed_byte_count"], 0)
        self.assertEqual(summary["first_changed_offset"], 3)

    def test_fixed_interval_rejects_bad_bounds_and_lengths(self):
        for start, end, replacement in ((-1, 2, b"abc"), (3, 3, b""), (2, 8, b"x")):
            with self.subTest(start=start, end=end):
                with self.assertRaises(self.module.BootSliceError):
                    self.module.replace_fixed_interval(b"abcdef", replacement, start, end)

    def test_outside_mutation_is_rejected(self):
        carrier = bytes(8)
        candidate = bytearray(carrier)
        candidate[7] = 1
        with self.assertRaises(self.module.BootSliceError):
            self.module.diff_outside_interval(carrier, bytes(candidate), 2, 6)

    def test_arm64_header(self):
        parsed = self.module.parse_arm64_header(arm64_image())
        self.assertEqual(parsed["magic"], 0x644D5241)
        with self.assertRaises(self.module.BootSliceError):
            self.module.parse_arm64_header(bytes(64))

    def test_stable_pinned_read_and_symlink_rejection(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            payload = b"stable-pinned-input"
            path = root / "input"
            path.write_bytes(payload)
            receipt, data = self.module.read_pinned_stable(
                path, len(payload), hashlib.sha256(payload).hexdigest(), "input"
            )
            self.assertEqual(data, payload)
            self.assertTrue(receipt["stable_direct_regular_file"])
            link = root / "link"
            link.symlink_to(path)
            with self.assertRaises(self.module.BootSliceError):
                self.module.read_pinned_stable(
                    link, len(payload), hashlib.sha256(payload).hexdigest(), "link"
                )

    def test_stable_read_detects_descriptor_identity_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "input"
            payload = b"identity"
            path.write_bytes(payload)
            real_fstat = self.module.os.fstat
            calls = 0

            def changed_fstat(fd):
                nonlocal calls
                result = real_fstat(fd)
                calls += 1
                if calls == 2:
                    values = list(result)
                    values[1] += 1
                    return self.module.os.stat_result(values)
                return result

            with mock.patch.object(self.module.os, "fstat", side_effect=changed_fstat):
                with self.assertRaises(self.module.BootSliceError):
                    self.module.read_pinned_stable(
                        path, len(payload), hashlib.sha256(payload).hexdigest(), "input"
                    )

    def test_deterministic_ap_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = root / "first.tar.md5"
            second = root / "second.tar.md5"
            left = self.module.write_deterministic_boot_ap(b"frame", first)
            right = self.module.write_deterministic_boot_ap(b"frame", second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(left, right)
            self.assertEqual(left["members"], ["boot.img.lz4"])

    def test_marker_classification(self):
        prefix = b"[[S22R4W1B|"
        marker = b"\n[[S22R4W1B|id=good|phase=X]]\n"
        valid = self.module.classify_marker_family(b"x" + marker + b"y", marker, prefix)
        self.assertTrue(valid["valid_single_exact"])
        duplicate = self.module.classify_marker_family(marker + marker, marker, prefix)
        self.assertFalse(duplicate["valid_single_exact"])
        foreign = self.module.classify_marker_family(
            marker + b"[[S22R4W1B|id=bad|phase=X]]", marker, prefix
        )
        self.assertEqual(foreign["foreign_count"], 1)
        partial = self.module.classify_marker_family(prefix + b"id=cut", marker, prefix)
        self.assertEqual(partial["partial_count"], 1)

    def test_odin_gate_is_fixed_to_impossible_path(self):
        self.assertEqual(self.module.INVALID_ODIN_DEVICE, "/dev/bus/usb/999/999")
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('"-l"', source)
        self.assertNotIn("usb.core", source)
        self.assertIn("failed_before_device_open", source)


if __name__ == "__main__":
    unittest.main()
