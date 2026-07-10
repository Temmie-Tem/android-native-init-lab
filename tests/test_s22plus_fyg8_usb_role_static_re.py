import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_fyg8_usb_role_static_re.py"


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_fyg8_usb_role_static_re_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusFyg8UsbRoleStaticReTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.payload = cls.module.build_payload()

    def test_exact_static_re_passes(self):
        self.assertEqual(self.payload["result"], "pass-static-role-path-reconstructed")
        self.assertEqual(len(self.payload["modules"]), 5)
        self.assertEqual(len(self.payload["call_edges"]), len(self.module.EXPECTED_CALL_EDGES))
        self.assertTrue(self.payload["safety"]["host_only"])
        self.assertFalse(self.payload["safety"]["adb"])
        self.assertFalse(self.payload["safety"]["device_read"])

    def test_notifier_chain_has_load_bearing_edges(self):
        edges = {
            (edge["module"], edge["caller"], edge["callee"])
            for edge in self.payload["call_edges"]
        }
        for edge in self.module.EXPECTED_CALL_EDGES:
            self.assertIn(edge, edges)

    def test_qcom_callback_table_reaches_dwc3_wrappers(self):
        callbacks = {
            entry["target"] for entry in self.payload["sec_otg_notify_callback_table"]
        }
        self.assertIn("qcom_set_host.cfi_jt", callbacks)
        self.assertIn("qcom_set_peripheral.cfi_jt", callbacks)
        conclusions = self.payload["conclusions"]
        self.assertEqual(conclusions["qcom_callbacks_to_dwc3_events"], "ELF_VERIFIED")

    def test_all_g0q_overlays_share_role_topology_without_extcon_property(self):
        device_tree = self.payload["device_tree"]
        self.assertEqual(device_tree["overlay_count"], 11)
        for overlay in device_tree["overlays"]:
            self.assertTrue(all(overlay["matches"].values()))
            self.assertEqual(overlay["explicit_extcon_property_count"], 0)
        self.assertFalse(device_tree["common_topology"]["direct_max77705_to_dwc3_phandle"])

    def test_forced_peripheral_bypass_is_exact_binary_verified(self):
        bypass = self.payload["forced_peripheral_bypass"]
        self.assertEqual(bypass["result"], "ELF_INSTRUCTION_AND_CALL_PATH_VERIFIED")
        self.assertEqual(bypass["peripheral_role_value"], 2)
        self.assertEqual(bypass["shared_vbus_active_offset"], 858)
        self.assertEqual(
            bypass["show_callback_relocation_offset"],
            bypass["dev_attr_mode_address"] + 0x10,
        )
        self.assertEqual(
            bypass["store_callback_relocation_offset"],
            bypass["dev_attr_mode_address"] + 0x18,
        )
        self.assertTrue(all(bypass["sysfs_mode_attribute_callbacks"].values()))
        self.assertTrue(all(bypass["instruction_checks"].values()))
        self.assertEqual(len(bypass["call_edges"]), len(self.module.FORCED_PERIPHERAL_EDGES))

    def test_forced_bypass_rules_out_notifier_omission_only_after_mode_executes(self):
        conclusions = self.payload["conclusions"]
        self.assertEqual(
            conclusions["forced_peripheral_role_bypass"],
            "ELF_VERIFIED_AFTER_DWC3_MSM_BIND",
        )
        self.assertFalse(conclusions["max77705_chain_required_for_forced_peripheral"])
        self.assertEqual(
            conclusions["o3_role_chain_omission_as_no_usb_root_cause"],
            "RULED_OUT_IF_MODE_WRITE_EXECUTED",
        )

    def test_write_then_check_is_reproducible_and_fail_closed(self):
        rendered = self.module.artifacts()
        with tempfile.TemporaryDirectory() as temp_dir:
            out = Path(temp_dir)
            self.module.write_artifacts(out, rendered)
            self.module.check_artifacts(out, rendered)
            payload = json.loads((out / "static-analysis.json").read_text(encoding="ascii"))
            self.assertEqual(payload["schema"], self.module.SCHEMA)
            (out / "live-crosscheck.json").write_text("{}\n", encoding="ascii")
            self.module.write_artifacts(out, rendered)
            self.module.check_artifacts(out, rendered)
            (out / "stale.txt").write_text("stale\n", encoding="ascii")
            with self.assertRaises(self.module.StaticReError):
                self.module.check_artifacts(out, rendered)

    def test_source_has_no_device_or_flash_command(self):
        source = SCRIPT.read_text(encoding="ascii")
        for token in ("adb ", "odin4", "heimdall", "fastboot", "finit_module", "insmod"):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
