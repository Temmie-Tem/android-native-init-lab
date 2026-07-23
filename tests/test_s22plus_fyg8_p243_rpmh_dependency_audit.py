import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "workspace/public/src/scripts/revalidation"
CHECKER_PATH = SCRIPT_DIR / "s22plus_fyg8_p243_rpmh_dependency_audit.py"
PRIVATE_READY = all(
    (ROOT / path).is_file()
    for path in (
        "workspace/private/outputs/s22plus_fyg8_p242/candidate-a/boot.img",
        "workspace/private/outputs/s22plus_fyg8_p242/artifacts-a/.config",
        "workspace/private/runs/s22plus_o3r1_native_retained_sysrq_live_gate_"
        "20260709T220014Z/sec_debug_state/pre_o3r1/proc__cmdline.txt",
        "workspace/private/inputs/s22plus_firmware/S906NKSS7FYG8_SKC/"
        "extracted-images/raw/vendor_boot.img",
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
class P243RpmhDependencyAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load(
            "s22plus_fyg8_p243_rpmh_dependency_audit_tested", CHECKER_PATH
        )
        cls.result = cls.module.build_result()

    def test_host_only_dependency_audit_passes(self):
        self.assertEqual(self.result["verdict"], self.module.VERDICT)
        self.assertEqual(
            self.result["verdict"],
            "PASS_P243_RPMH_DEPENDENCY_AUDIT_HOST_ONLY",
        )
        self.assertTrue(self.result["safety"]["host_only"])
        for key, value in self.result["safety"].items():
            if key != "host_only":
                self.assertFalse(value, key)

    def test_failed_gate_is_display_clock_not_power_domain(self):
        cause = self.result["failure_explanation"]
        self.assertEqual(
            cause["classification"],
            "STATIC_MISSING_DISPLAY_CLOCK_SUPPLIER_EXPLANATION",
        )
        self.assertEqual(cause["failed_node_role"], "display-rsc")
        self.assertFalse(cause["failed_node_has_power_domain"])
        self.assertEqual(cause["required_supplier_module"], "dispcc-waipio.ko")
        self.assertFalse(cause["supplier_module_selected"])
        self.assertTrue(cause["fw_devlink_defers_before_rpmh_rsc_probe"])
        self.assertTrue(cause["source_artifact_closure"])
        self.assertFalse(cause["p242_runtime_supplier_state_observed"])
        self.assertFalse(cause["p242_live_root_cause_proven"])
        self.assertFalse(
            self.result["boot_arguments"][
                "candidate_runtime_cmdline_directly_observed"
            ]
        )
        provider = self.result["power_domain_provider"]
        self.assertEqual(provider["provider"], "/soc/psci/cluster-pd")
        self.assertEqual(provider["provider_driver"], "psci-cpuidle-domain")
        self.assertEqual(
            provider["provider_bind_path"],
            "/sys/bus/platform/drivers/psci-cpuidle-domain/soc:psci",
        )
        self.assertTrue(provider["provider_builtin"])
        self.assertTrue(provider["source_artifact_closure"])
        self.assertFalse(provider["p242_live_provider_bind_observed"])
        self.assertTrue(
            self.result["source"][
                "power_domains_are_required_fw_devlink_suppliers"
            ]
        )

    def test_all_vendor_dtb_variants_have_same_dependency_split(self):
        tree = self.result["vendor_dtb"]
        self.assertEqual(tree["blob_count"], 4)
        for variant in tree["variants"]:
            self.assertEqual(
                variant["apps_rsc"]["power_domain_provider"],
                "/soc/psci/cluster-pd",
            )
            self.assertIsNone(variant["apps_rsc"]["clock_supplier"])
            self.assertIsNone(
                variant["display_rsc"]["power_domain_provider"]
            )
            self.assertEqual(
                variant["display_rsc"]["clock_supplier"],
                "/soc/clock-controller@af00000",
            )
            self.assertEqual(variant["display_rsc"]["clock_id"], 0x48)
        self.assertEqual(self.result["dtbo"]["entry_count"], 11)
        self.assertEqual(self.result["dtbo"]["rsc_parent_property_overrides"], 0)

    def test_exact_plan_omits_only_display_supplier_from_its_hard_closure(self):
        modules = self.result["module_closure"]
        self.assertEqual(modules["module_count"], 59)
        self.assertEqual(
            modules["missing_display_supplier_module"], "dispcc-waipio.ko"
        )
        self.assertFalse(modules["display_supplier_itself_selected"])
        self.assertTrue(
            modules["display_supplier_hard_dependencies_already_selected"]
        )
        self.assertEqual(
            set(modules["display_supplier_hard_dependencies"]),
            self.module.DISPCC_HARD_DEPS,
        )

    def test_discriminator_replaces_gate_without_display_scope_growth(self):
        discriminator = self.result["bounded_discriminator"]
        self.assertEqual(
            discriminator["action"],
            "replace-display-rsc-and-gcc-gates-with-usb-provider-chain",
        )
        self.assertEqual(discriminator["old_gate"], self.module.OLD_GATE)
        self.assertEqual(discriminator["new_gate"], self.module.NEW_GATE)
        self.assertEqual(
            [row["id"] for row in discriminator["ordered_predicates"]],
            [
                "psci-domain",
                "apps-rsc",
                "apps-rpmh-clock",
                "apps-rpmh-cxlvl",
                "apps-rpmh-mxlvl",
                "gcc-waipio",
            ],
        )
        self.assertEqual(
            discriminator["replaces_existing_gates"],
            ["rpmh", "gcc-waipio"],
        )
        self.assertEqual(discriminator["resulting_gate_count"], 12)
        self.assertEqual(
            discriminator["resulting_stage_range"],
            {"first": "0x7b", "last": "0x86", "success": "0x8f"},
        )
        self.assertEqual(discriminator["add_modules"], [])
        self.assertEqual(discriminator["do_not_add"], ["dispcc-waipio.ko"])
        self.assertTrue(discriminator["preserve_unreplaced_gate_order"])
        self.assertFalse(self.result["proof_limits"]["apps_rsc_live_bind"])
        self.assertFalse(self.result["proof_limits"]["live_authority"])

    def test_checker_contains_no_device_or_build_action(self):
        source = CHECKER_PATH.read_text(encoding="ascii")
        for token in (
            "adb ",
            "odin4 ",
            "fastboot ",
            "subprocess.",
            "finit_module(",
            "reboot(",
        ):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
