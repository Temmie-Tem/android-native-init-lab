import importlib.util
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "s22plus_fyg8_r4w1c_watchdog_carrier_static_checker.py"
SOURCE = ROOT / "workspace/public/src/native-init/s22plus_init_r4w1c_wdt_carrier.c"
REPRO_A = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/"
    "reproduction-h"
)
REPRO_B = ROOT / (
    "workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/"
    "reproduction-i"
)


class S22PlusFyg8R4W1CWatchdogCarrierStaticCheckerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        spec = importlib.util.spec_from_file_location("r4w1c_checker_tested", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(SCRIPTS))

    def test_independent_constants_bind_exact_module_order(self):
        self.assertEqual(
            [spec[0] for spec in self.module.MODULE_SPECS],
            [
                "smem.ko",
                "minidump.ko",
                "qcom-scm.ko",
                "qcom_wdt_core.ko",
                "gh_virt_wdt.ko",
            ],
        )
        self.assertEqual(
            [spec[1] for spec in self.module.MODULE_SPECS],
            ["smem", "minidump", "qcom_scm", "qcom_wdt_core", "gh_virt_wdt"],
        )
        self.assertTrue(
            set(self.module.FORBIDDEN_MODULES).isdisjoint(
                spec[0] for spec in self.module.MODULE_SPECS
            )
        )

    def test_independent_compilation_matches_pinned_init(self):
        receipt, data = self.module.compile_expected_init(SOURCE)
        self.assertEqual(receipt["size"], self.module.INIT_SIZE)
        self.assertEqual(receipt["sha256"], self.module.INIT_SHA256)
        self.assertEqual(len(data), self.module.INIT_SIZE)

    @unittest.skipUnless(REPRO_A.exists(), "private R4W1-C reproduction missing")
    def test_manifest_validation_rejects_safety_and_output_tampering(self):
        encoded = (REPRO_A / "manifest.json").read_bytes()
        receipt = self.module.validate_manifest(encoded)
        self.assertTrue(receipt["consistent"])
        for mutation in ("safety", "output"):
            data = json.loads(encoded)
            if mutation == "safety":
                data["safety"]["live_authorized"] = True
            else:
                data["outputs"]["boot_img"]["sha256"] = "0" * 64
            with self.subTest(mutation=mutation):
                with self.assertRaises(self.module.CheckError):
                    self.module.validate_manifest(json.dumps(data).encode("ascii"))

    def test_result_writer_is_exclusive(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "result.json"
            payload = {"schema": "test", "value": True}
            self.module.write_result(path, payload)
            self.assertEqual(json.loads(path.read_text(encoding="ascii")), payload)
            with self.assertRaises(FileExistsError):
                self.module.write_result(path, payload)

    def test_checker_has_no_live_transport_or_transfer_path(self):
        text = SCRIPT.read_text(encoding="utf-8").lower()
        self.assertNotIn('["adb"', text)
        self.assertNotIn("run_odin", text)
        self.assertNotIn("default_odin", text)
        self.assertNotIn("fastboot", text)
        self.assertIn('"device_contact": false', text)
        self.assertIn('"odin_invoked": false', text)
        self.assertIn('"flash": false', text)
        self.assertIn('"live_authorized": false', text)

    @unittest.skipUnless(
        REPRO_A.exists() and REPRO_B.exists(),
        "private R4W1-C reproductions missing",
    )
    def test_current_two_reproduction_contract(self):
        args = Namespace(
            repro_a=REPRO_A,
            repro_b=REPRO_B,
            image=self.module.DEFAULT_IMAGE,
            source=SOURCE,
            vendor_ramdisk=self.module.DEFAULT_VENDOR_RAMDISK,
            lz4=self.module.DEFAULT_LZ4,
            magiskboot=self.module.DEFAULT_MAGISKBOOT,
            out=Path("unused"),
            stdout_only=True,
        )
        result = self.module.check(args)
        self.assertEqual(result["verdict"], self.module.VERDICT)
        self.assertTrue(result["reproducible"])
        self.assertFalse(result["device_contact"])
        self.assertFalse(result["odin_invoked"])
        self.assertFalse(result["flash"])


if __name__ == "__main__":
    unittest.main()
