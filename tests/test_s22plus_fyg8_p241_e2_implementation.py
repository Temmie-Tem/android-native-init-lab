import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
CHECKER_PATH = SCRIPT_DIR / "s22plus_fyg8_p241_e2_static_checker.py"
DTBO_PATH = SCRIPT_DIR / "s22plus_fyg8_p241_dtbo_role_contract.py"
PRIVATE_READY = all(
    (ROOT / path).exists()
    for path in (
        "workspace/private/work/s22plus_fyg8_kernel_rebuild_r0",
        "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
        "extracted-images/unpack-vendor-boot/vendor_ramdisk00",
        "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
        "extracted-images/raw/dtbo.img",
    )
)


def load(name: str, path: Path):
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class P241DtboRoleContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load("s22plus_fyg8_p241_dtbo_role_contract_tested", DTBO_PATH)

    @unittest.skipUnless(PRIVATE_READY, "exact FYG8 private inputs are unavailable")
    def test_exact_dtbo_table_and_all_role_entries_pass(self):
        result = self.module.build_result()
        self.assertEqual(result["verdict"], self.module.VERDICT)
        self.assertEqual(result["entry_count"], 11)
        self.assertEqual(
            result["entry_manifest_sha256"],
            self.module.EXPECTED_ENTRY_MANIFEST_SHA256,
        )
        for entry in result["entries"]:
            self.assertTrue(all(entry["checks"].values()))
            self.assertTrue(entry["checks"]["no_role_switch_default_mode"])

    def test_parser_source_has_no_device_or_build_command(self):
        source = DTBO_PATH.read_text(encoding="ascii")
        for token in ("adb ", "odin4", "fastboot", "finit_module", "dtc "):
            self.assertNotIn(token, source)


@unittest.skipUnless(PRIVATE_READY, "exact FYG8 private inputs are unavailable")
class P241E2ImplementationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load("s22plus_fyg8_p241_e2_static_checker_tested", CHECKER_PATH)
        cls.result = cls.module.build_result(cls.module.parse_args([]))

    def test_full_host_contract_passes_without_candidate_or_authority(self):
        self.assertEqual(self.result["verdict"], self.module.VERDICT)
        self.assertEqual(self.result["profile"], "E2")
        self.assertEqual(self.result["profile_number"], 3)
        self.assertTrue(self.result["safety"]["host_only"])
        for key, value in self.result["safety"].items():
            if key != "host_only":
                self.assertFalse(value, key)

    def test_exact_plan_and_vendor_module_bytes_are_closed(self):
        self.assertEqual(self.result["plan"]["module_count"], 59)
        self.assertEqual(self.result["plan"]["constraint_count"], 210)
        self.assertEqual(
            self.result["plan"]["tsv_sha256"],
            self.module.planner.EXPECTED_E2_PROFILE_PLAN_TSV_SHA256,
        )
        rootfs = self.result["vendor_rootfs"]
        self.assertEqual(rootfs["module_count"], 59)
        self.assertEqual(rootfs["request_firmware_string_hits"], 0)
        self.assertTrue(rootfs["sec_log_buf_absent"])
        self.assertEqual(len({row["sha256"] for row in rootfs["modules"]}), 59)

    def test_profile3_reachable_contract_and_e1_regression_pass(self):
        self.assertEqual(
            self.result["reachable_record_contract"]["reachable_slot_variants"],
            307_201,
        )
        self.assertEqual(
            self.result["e1a_e1b_regression"]["reachable_slot_variants"],
            90_114,
        )
        self.assertEqual(self.result["patch"]["sequence_count"], 76)
        self.assertEqual(self.result["patch"]["terminal"], 0x8F)

    def test_runtime_is_static_and_read_only_at_usb_boundary(self):
        linked = self.result["linked_userspace"]["init"]
        self.assertTrue(linked["static_aarch64"])
        self.assertEqual(linked["undefined_symbols"], 0)
        self.assertTrue(self.result["sources"]["module_prefix_checked_after_each_load"])
        self.assertTrue(self.result["sources"]["eexist_rejected"])
        self.assertTrue(self.result["sources"]["read_only_gate_phase"])
        self.assertEqual(self.result["dtbo_role_contract"]["entry_count"], 11)

    def test_source_has_no_device_flash_or_live_command(self):
        source = CHECKER_PATH.read_text(encoding="ascii")
        for token in ("adb ", "odin4 -a", "fastboot flash", "dd of=/dev/block"):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
