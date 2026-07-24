import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
CHECKER_PATH = (
    SCRIPT_DIR / "s22plus_fyg8_p251b_phy_nested_closure_audit.py"
)
PRIVATE_READY = all(
    (ROOT / path).is_file()
    for path in (
        "workspace/private/outputs/s22plus_fyg8_p249/static-check-result.json",
        "workspace/private/outputs/s22plus_fyg8_p249/candidate-a/boot.img",
        "workspace/private/outputs/s22plus_fyg8_p249/artifacts-a/.config",
        "workspace/private/outputs/s22plus_fyg8_p249/intent/"
        "materialized-sources/s22plus_fyg8_p244_e2_plan.h",
        "workspace/private/outputs/s22plus_fyg8_p249/intent/"
        "materialized-sources/s22plus_fyg8_p248_e2_runtime.c",
        "workspace/private/runs/device-action-f1-live-v2/"
        "p249-20260724-2/live-result.json",
        "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
        "extracted-images/unpack-vendor-boot/vendor_ramdisk00",
        "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
        "extracted-images/unpack-vendor-boot/dtb",
        "workspace/private/inputs/s22plus_kernel_source/"
        "SM-S906N_15_base_osrc/Kernel.tar.gz",
        "workspace/private/inputs/s22plus_kernel_source/"
        "S906NKSS7FYG8_osrc/S906NKSS7FYG8_kernel.tar.gz",
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


@unittest.skipUnless(PRIVATE_READY, "exact FYG8 private inputs are unavailable")
class P251bPhyNestedClosureAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load(
            "s22plus_fyg8_p251b_phy_nested_closure_audit_tested",
            CHECKER_PATH,
        )
        cls.result = cls.module.build_result()

    def test_host_only_audit_passes(self):
        self.assertEqual(self.result["verdict"], self.module.VERDICT)
        self.assertTrue(self.result["safety"]["host_only"])
        for key, value in self.result["safety"].items():
            if key != "host_only":
                self.assertFalse(value, key)

    def test_four_variants_have_one_nested_closure(self):
        tree = self.result["vendor_dtb"]
        self.assertEqual(tree["blob_count"], 4)
        closure = tree["common"]["closure"]
        self.assertEqual(
            set(closure["hsphy"]["supplies"].values()),
            {
                f"{self.module.wrapper_path(resource)}/{leaf}"
                for (
                    _label,
                    consumer,
                    _property,
                    resource,
                    leaf,
                    _name,
                    _detail,
                ) in self.module.SUPPLY_SPECS
                if consumer == self.module.HS_PHY
            },
        )
        self.assertEqual(
            set(closure["ssphy"]["supplies"].values()),
            {
                f"{self.module.wrapper_path(resource)}/{leaf}"
                for (
                    _label,
                    consumer,
                    _property,
                    resource,
                    leaf,
                    _name,
                    _detail,
                ) in self.module.SUPPLY_SPECS
                if consumer == self.module.SS_PHY
            },
        )
        self.assertEqual(closure["ssphy"]["pinctrl_owner"], self.module.TLMM)
        self.assertEqual(
            closure["ssphy"]["pinctrl_wakeup_parent"],
            "/soc/interrupt-controller@b220000",
        )

    def test_gdsc_has_no_external_fw_devlink_supplier(self):
        gdsc = self.result["vendor_dtb"]["common"]["closure"]["gdsc"]
        self.assertEqual(gdsc["proxy_supply"], self.module.GDSC)
        self.assertEqual(gdsc["external_supplier_properties"], [])
        self.assertTrue(
            self.result["source"][
                "gdsc_self_proxy_link_rejected_as_self_ancestor"
            ]
        )

    def test_exact_modules_and_hard_closures_are_complete(self):
        modules = self.result["modules"]
        self.assertEqual(modules["selected_module_count"], 59)
        self.assertEqual(
            set(modules["identities"]), self.module.MODULES
        )
        for closure in modules["hard_closures"].values():
            self.assertEqual(closure["missing_from_plan"], [])
        self.assertFalse(
            modules["exact_phy_modules_compile_tuning_sysfs"]
        )
        self.assertEqual(
            modules["elf"]["phy-msm-snps-hs.ko"][
                "tuning_sysfs_imports"
            ],
            [],
        )
        self.assertEqual(
            modules["elf"]["phy-msm-ssusb-qmp.ko"][
                "tuning_sysfs_imports"
            ],
            [],
        )

    def test_classifier_refinement_adds_only_branch_reads(self):
        classifier = self.result["bounded_classifier_refinement"]
        self.assertEqual(classifier["frontier_stage"], "0x84")
        self.assertEqual(classifier["add_modules"], [])
        self.assertEqual(classifier["add_stages"], [])
        self.assertEqual(len(classifier["direct_checks"]), 7)
        self.assertEqual(len(classifier["nested_branch_checks"]), 6)
        self.assertEqual(len(classifier["phy_checks"]), 2)
        self.assertEqual(
            [row["detail"] for row in classifier["direct_checks"]],
            ["0xa01", "0xa02", "0xa03", "0xa04", "0xa05", "0xa06", "0xa07"],
        )
        self.assertEqual(
            [row["detail"] for row in classifier["nested_branch_checks"]],
            ["0xa08", "0xa09", "0xa0a", "0xa0b", "0xa0c", "0xa0d"],
        )
        self.assertEqual(
            [row["detail"] for row in classifier["phy_checks"]],
            ["0xa20", "0xa21"],
        )
        self.assertEqual(
            set(classifier["terminal_details"]), {"0xa10", "0xa30"}
        )
        all_details = [
            row["detail"]
            for group in (
                classifier["direct_checks"],
                classifier["nested_branch_checks"],
                classifier["phy_checks"],
            )
            for row in group
        ] + list(classifier["terminal_details"])
        self.assertEqual(len(all_details), len(set(all_details)))
        self.assertEqual(classifier["maximum_added_runtime_sec"], 5)

    def test_source_archives_are_directly_pinned(self):
        prerequisite = self.result["prerequisite"]
        self.assertEqual(
            prerequisite["base_source"]["sha256"],
            self.module.EXPECTED_SHA256["base_source"],
        )
        self.assertEqual(
            prerequisite["delta_source"]["sha256"],
            self.module.EXPECTED_SHA256["delta_source"],
        )

    def test_cleanup_asymmetry_is_a_lead_not_a_live_claim(self):
        self.assertTrue(
            self.result["source"][
                "hsphy_regulator_failure_removes_registered_phy"
            ]
        )
        self.assertTrue(
            self.result["source"][
                "ssphy_regulator_failure_after_usb_add_has_no_probe_cleanup"
            ]
        )
        self.assertFalse(
            self.result["proof_limits"]["ssphy_failed_probe_leak_observed"]
        )
        self.assertFalse(
            self.result["conclusion"]["exact_live_root_cause_identified"]
        )

    def test_checker_contains_no_device_or_build_action(self):
        source = CHECKER_PATH.read_text(encoding="ascii")
        for token in (
            "adb ",
            "odin4 ",
            "fastboot ",
            "finit_module(",
            "reboot(",
            "make -j",
        ):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
