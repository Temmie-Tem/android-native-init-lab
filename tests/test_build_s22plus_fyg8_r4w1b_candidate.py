import importlib.util
import json
import struct
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "build_s22plus_fyg8_r4w1b_candidate.py"
REPRO = ROOT / "workspace/private/outputs/s22plus_fyg8_r4w1b_clean_repro_20260719/repro/result.json"


class S22PlusFyg8R4W1BCandidateBuilderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        spec = importlib.util.spec_from_file_location("r4w1b_builder_tested", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(SCRIPTS))

    def synthetic_inputs(self):
        carrier = bytearray(640)
        carrier[:8] = b"ANDROID!"
        struct.pack_into("<4I", carrier, 8, 384, 7, 0, 1584)
        struct.pack_into("<I", carrier, 40, 4)
        image = bytearray(384)
        struct.pack_into(
            "<IIQQQQQQII", image, 0, 0x14000008, 0, 0, 384, 10, 0, 0, 0, 0x644D5241, 0
        )
        image[128 : 128 + len(self.module.MARKER)] = self.module.MARKER
        return bytes(carrier), bytes(image)

    def geometry_override(self):
        names = (
            "BOOT_SIZE",
            "HEADER_END",
            "KERNEL_START",
            "KERNEL_END",
            "KERNEL_SIZE",
            "GAP_START",
            "GAP_END",
            "GAP_SIZE",
        )
        old = {name: getattr(self.module, name) for name in names}
        values = {
            "BOOT_SIZE": 640,
            "HEADER_END": 64,
            "KERNEL_START": 64,
            "KERNEL_END": 448,
            "KERNEL_SIZE": 384,
            "GAP_START": 448,
            "GAP_END": 512,
            "GAP_SIZE": 64,
        }
        return old, values

    def test_candidate_replaces_only_selected_slice(self):
        old, values = self.geometry_override()
        try:
            for key, value in values.items():
                setattr(self.module, key, value)
            carrier, image = self.synthetic_inputs()
            candidate, checks = self.module.build_candidate_bytes(carrier, image)
            self.assertEqual(candidate[:64], carrier[:64])
            self.assertEqual(candidate[64:448], image)
            self.assertEqual(candidate[448:], carrier[448:])
            self.assertTrue(checks["marker"]["valid_single_exact"])
        finally:
            for key, value in old.items():
                setattr(self.module, key, value)

    def test_marker_absent_duplicate_foreign_and_partial_fail_closed(self):
        old, values = self.geometry_override()
        try:
            for key, value in values.items():
                setattr(self.module, key, value)
            carrier, valid = self.synthetic_inputs()
            variants = []
            absent = bytearray(valid)
            absent[128 : 128 + len(self.module.MARKER)] = bytes(len(self.module.MARKER))
            variants.append(absent)
            duplicate = bytearray(valid)
            duplicate[240 : 240 + len(self.module.MARKER)] = self.module.MARKER
            variants.append(duplicate)
            foreign = bytearray(valid)
            foreign[128 : 128 + len(self.module.MARKER)] = self.module.MARKER.replace(
                self.module.MARKER_ID.encode(), b"f" * 32
            )
            variants.append(foreign)
            partial = bytearray(valid)
            partial[128 : 128 + len(self.module.MARKER)] = bytes(len(self.module.MARKER))
            partial[128 : 128 + len(self.module.MARKER_FAMILY)] = self.module.MARKER_FAMILY
            variants.append(partial)
            for variant in variants:
                with self.subTest(kind=len(variants)):
                    with self.assertRaises(self.module.BuildError):
                        self.module.build_candidate_bytes(carrier, bytes(variant))
        finally:
            for key, value in old.items():
                setattr(self.module, key, value)

    def test_reproduction_result_semantics(self):
        encoded = REPRO.read_bytes()
        receipt = self.module.verify_reproduction_result(encoded)
        self.assertTrue(receipt["two_clean_images_verified"])
        data = json.loads(encoded)
        data["image_byte_identical"] = False
        with self.assertRaises(self.module.BuildError):
            self.module.verify_reproduction_result(json.dumps(data).encode())

    def test_invalid_carrier_and_image_headers_fail_closed(self):
        old, values = self.geometry_override()
        try:
            for key, value in values.items():
                setattr(self.module, key, value)
            carrier, image = self.synthetic_inputs()
            bad_carrier = bytearray(carrier)
            bad_carrier[:8] = b"NOTBOOT!"
            with self.assertRaises(self.module.BuildError):
                self.module.build_candidate_bytes(bytes(bad_carrier), image)
            bad_image = bytearray(image)
            struct.pack_into("<I", bad_image, 56, 0)
            with self.assertRaises(self.module.boot_slice.BootSliceError):
                self.module.build_candidate_bytes(carrier, bytes(bad_image))
        finally:
            for key, value in old.items():
                setattr(self.module, key, value)

    def test_patch_vbmeta_flag_is_exact(self):
        self.module.validate_patch_vbmeta_flag({})
        self.module.validate_patch_vbmeta_flag({"PATCHVBMETAFLAG": "false"})
        for value in ("", "0", "False", "true"):
            with self.subTest(value=value):
                with self.assertRaises(self.module.BuildError):
                    self.module.validate_patch_vbmeta_flag({"PATCHVBMETAFLAG": value})

    def test_existing_output_is_rejected_before_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "exists"
            output.mkdir()
            args = Namespace(
                out=output,
                carrier=Path("missing"),
                image=Path("missing"),
                repro_result=Path("missing"),
                lz4=Path("missing"),
                odin=Path("missing"),
            )
            with self.assertRaisesRegex(self.module.BuildError, "output path already exists"):
                self.module.build(args)

    def test_source_has_no_live_capability(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"device_contact": False', source)
        self.assertIn('"device_write": False', source)
        self.assertIn('"flash": False', source)
        self.assertIn('"live_authorized": False', source)
        self.assertNotIn('"adb"', source.lower())
        self.assertNotIn("'adb'", source.lower())
        self.assertNotIn("fastboot", source.lower())
        self.assertNotIn("timeline", source.lower())
        self.assertNotIn("consumed", source.lower())
        self.assertNotIn('"-l"', source)
        self.assertEqual(self.module.boot_slice.INVALID_ODIN_DEVICE, "/dev/bus/usb/999/999")


if __name__ == "__main__":
    unittest.main()
