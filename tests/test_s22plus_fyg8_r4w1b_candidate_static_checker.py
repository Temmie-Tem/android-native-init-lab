import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "s22plus_fyg8_r4w1b_candidate_static_checker.py"
CARRIER = ROOT / "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate_inputs/m4t2-carrier/boot.img"
VENDOR_BOOT = ROOT / "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/extracted-images/raw/vendor_boot.img"
LZ4 = ROOT / "workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/prebuilts/kernel-build-tools/linux-x86/bin/lz4"
REPRO = ROOT / "workspace/private/outputs/s22plus_fyg8_r4w1b_clean_repro_20260719/repro/result.json"
REPRO_A = ROOT / "workspace/private/outputs/s22plus_fyg8_r4w1b_candidate/reproduction-a"


class S22PlusFyg8R4W1BCandidateStaticCheckerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        spec = importlib.util.spec_from_file_location("r4w1b_static_tested", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(SCRIPTS))

    def test_independent_formula_and_every_mutation_class(self):
        names = ("BOOT_SIZE", "HEADER_END", "KERNEL_START", "KERNEL_END", "KERNEL_SIZE")
        old = {name: getattr(self.module, name) for name in names}
        try:
            values = {"BOOT_SIZE": 12, "HEADER_END": 2, "KERNEL_START": 2, "KERNEL_END": 6, "KERNEL_SIZE": 4}
            for key, value in values.items():
                setattr(self.module, key, value)
            carrier = b"abcdefghijkl"
            expected = self.module.expected_candidate(carrier, b"WXYZ")
            self.assertEqual(expected, b"abWXYZghijkl")
            with self.assertRaises(self.module.CheckError):
                self.module.expected_candidate(carrier[:-1], b"WXYZ")
            with self.assertRaises(self.module.CheckError):
                self.module.expected_candidate(carrier, b"bad")
        finally:
            for key, value in old.items():
                setattr(self.module, key, value)

    def test_marker_exact_duplicate_foreign_and_partial(self):
        marker = self.module.MARKER
        valid = self.module.classify_marker(b"x" + marker + b"y")
        self.assertTrue(valid["valid_single_exact"])
        self.assertFalse(self.module.classify_marker(marker + marker)["valid_single_exact"])
        foreign = marker.replace(b"36dc5462adedcf136176f2ddcfee08a8", b"f" * 32)
        self.assertFalse(self.module.classify_marker(foreign)["valid_single_exact"])
        self.assertFalse(
            self.module.classify_marker(self.module.MARKER_FAMILY + b"cut")["valid_single_exact"]
        )

    def test_kernel_reproduction_result_is_reopened_semantically(self):
        encoded = REPRO.read_bytes()
        self.assertTrue(self.module.verify_reproduction_result(encoded)["two_clean_images_verified"])
        data = json.loads(encoded)
        data["images"][0]["marker_count"] = 2
        with self.assertRaises(self.module.CheckError):
            self.module.verify_reproduction_result(json.dumps(data).encode())

    def test_real_m4t2_and_stock_vendor_rootfs_contract(self):
        result = self.module.audit_rootfs(CARRIER.read_bytes(), VENDOR_BOOT.read_bytes(), LZ4)
        effective = result["effective_init"]
        self.assertEqual(effective["layer"], "generic")
        self.assertEqual(effective["size"], self.module.M4T2_INIT_SIZE)
        self.assertEqual(effective["sha256"], self.module.M4T2_INIT_SHA256)
        self.assertEqual(effective["entrypoint"]["instructions"], ["wfe", "b <entrypoint>"])
        self.assertEqual(result["rdinit_override_sources"], [])
        self.assertEqual(result["vendor_boot"]["fragment_count"], 1)

    def test_real_manifest_consistency_and_safety_mutation(self):
        frame_receipt, _ = self.module.verify.read_stable(
            REPRO_A / "boot.img.lz4", "test frame"
        )
        ap_receipt, _ = self.module.verify.read_stable(
            REPRO_A / "odin4/AP.tar.md5", "test AP"
        )
        manifest = (REPRO_A / "manifest.json").read_bytes()
        candidate_sha = self.module.verify.sha256_bytes((REPRO_A / "boot.img").read_bytes())
        result = self.module.validate_manifest(
            manifest, candidate_sha, frame_receipt, ap_receipt
        )
        self.assertTrue(result["consistent"])
        mutated = json.loads(manifest)
        mutated["safety"]["flash"] = True
        with self.assertRaises(self.module.CheckError):
            self.module.validate_manifest(
                json.dumps(mutated).encode(), candidate_sha, frame_receipt, ap_receipt
            )

    def test_real_three_reproduction_contract(self):
        result = self.module.audit(self.module.parse_args([]))
        self.assertEqual(result["verdict"], self.module.VERDICT)
        self.assertEqual(result["blockers"], [])
        self.assertTrue(result["three_reproductions_byte_identical"])
        self.assertIn("kernel_reproduction_result", result["inputs"])
        self.assertNotIn("r4w1b_reproduction_result", result["inputs"])

    def test_checker_is_evidence_isolated_and_host_only(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("import s22plus_boot_verify as verify", source)
        self.assertNotIn("s22plus_boot_slice", source)
        self.assertNotIn("build_s22plus", source)
        self.assertNotIn('"adb"', source.lower())
        self.assertNotIn("fastboot", source.lower())
        self.assertNotIn("timeline", source.lower())
        self.assertNotIn("consumed", source.lower())
        self.assertIn('"device_contact": False', source)
        self.assertIn('"device_write": False', source)
        self.assertIn('"flash": False', source)
        self.assertIn('"live_authorized": False', source)


if __name__ == "__main__":
    unittest.main()
