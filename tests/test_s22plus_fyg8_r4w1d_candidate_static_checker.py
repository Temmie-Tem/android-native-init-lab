import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
SCRIPT = SCRIPTS / "s22plus_fyg8_r4w1d_candidate_static_checker.py"
CARRIER = (
    ROOT
    / "workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/"
    "reproduction-i/carrier.boot.img"
)
INIT = (
    ROOT
    / "workspace/private/outputs/s22plus_fyg8_r4w1c_watchdog_carrier/"
    "reproduction-i/build/s22plus_init_r4w1c_wdt_carrier"
)
VENDOR_BOOT = (
    ROOT
    / "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
    "extracted-images/raw/vendor_boot.img"
)
LZ4 = (
    ROOT
    / "workspace/private/work/s22plus_fyg8_kernel_rebuild_r0/kernel_platform/"
    "prebuilts/kernel-build-tools/linux-x86/bin/lz4"
)


class S22PlusFyg8R4W1DCandidateStaticCheckerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(SCRIPTS))
        spec = importlib.util.spec_from_file_location("r4w1d_static_tested", SCRIPT)
        cls.module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        sys.path.remove(str(SCRIPTS))

    def test_watchdog_init_static_runtime_contract(self):
        result = self.module.inspect_watchdog_init(INIT.read_bytes())
        self.assertTrue(result["verified"])
        self.assertEqual(result["machine"], "AArch64")
        self.assertFalse(result["interpreter"])
        mutated = INIT.read_bytes().replace(b"phase=park_enter", b"phase=park_fails", 1)
        with self.assertRaises(self.module.CheckError):
            self.module.inspect_watchdog_init(mutated)

    def test_effective_rootfs_is_exact_watchdog_init(self):
        result = self.module.audit_rootfs(
            CARRIER.read_bytes(), VENDOR_BOOT.read_bytes(), LZ4
        )
        effective = result["effective_init"]
        self.assertEqual(effective["layer"], "generic")
        self.assertEqual(effective["size"], self.module.INIT_SIZE)
        self.assertEqual(effective["sha256"], self.module.INIT_SHA256)
        self.assertTrue(effective["entrypoint"]["verified"])
        self.assertEqual(result["rdinit_override_sources"], [])

    def test_marker_and_three_reproduction_contract(self):
        image = self.module.DEFAULT_IMAGE
        self.assertTrue(self.module.classify_marker(image.read_bytes())["valid_single_exact"])
        result = self.module.audit(self.module.parse_args([]))
        self.assertEqual(result["verdict"], self.module.VERDICT)
        self.assertEqual(result["blockers"], [])
        self.assertTrue(result["three_reproductions_byte_identical"])
        self.assertIn("r4w1d_reproduction_result", result["inputs"])

    def test_engine_binding_is_restored(self):
        before = {
            name: getattr(self.module.engine, name)
            for name in ("SCHEMA", "RUNG", "INIT_SHA256", "INIT_INSPECTOR")
        }
        with self.module._bind_engine_contract():
            self.assertEqual(self.module.engine.SCHEMA, self.module.SCHEMA)
            self.assertIs(self.module.engine.INIT_INSPECTOR, self.module.inspect_watchdog_init)
        self.assertEqual(
            before,
            {
                name: getattr(self.module.engine, name)
                for name in ("SCHEMA", "RUNG", "INIT_SHA256", "INIT_INSPECTOR")
            },
        )

    def test_source_has_no_device_or_live_authority(self):
        source = SCRIPT.read_text(encoding="utf-8").lower()
        for token in ("adb", "fastboot", "--execute", "candidate_flash_start"):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
