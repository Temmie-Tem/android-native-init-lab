import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_stock_usb_role_crosscheck_readonly.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_stock_usb_role_crosscheck_readonly_tested", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusStockUsbRoleCrosscheckReadonlyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def command(self, stdout: str, rc: int = 0):
        return {"argv": [], "rc": rc, "stdout": stdout, "stderr": "", "timeout": False}

    def fixture(self):
        module_lines = "".join(f"{name} 1 0 - Live 0x0\n" for name in self.module.EXPECTED_MODULES)
        baseline = {
            "result": "pass-stock-topology-partial",
            "stock_state": {"boot_sha256": self.module.EXPECTED_BOOT_SHA256},
        }
        baseline_commands = {"proc_modules": self.command(module_lines)}
        values = {
            "dt_model": "Samsung G0Q PROJECT (board-id,12)\x00",
            "dt_symbol_usb0": "/soc/ssusb@a600000\x00",
            "dt_symbol_ucsi": "/soc/qcom,pmic_glink/qcom,ucsi\x00",
            "dt_symbol_qupv3_se5_i2c": "/soc/i2c@994000\x00",
            "dt_parent_role_switch_size": "0\n",
            "dt_child_role_switch_size": "0\n",
            "dt_child_dr_mode": "otg\x00",
            "dt_max77705_compatible": "maxim,max77705\x00",
            "dt_max77705_status": "okay\x00",
            "dt_pdic_compatible": "maxim,max77705_pdic\x00",
            "dt_pdic_status": "okay\x00",
            "dt_pdic_role_swap_size": "0\n",
            "dt_usb_notifier_compatible": "samsung,usb-notifier\x00",
            "bind_max77705_driver": "/sys/bus/platform/drivers/max77705-usbc\n",
            "bind_usb_notifier_driver": "/sys/bus/platform/drivers/usb_notifier\n",
            "bind_dwc3_msm_driver": "/sys/bus/platform/drivers/msm-dwc3\n",
            "bind_usb_notifier_module": "/sys/module/usb_notifier_qcom\n",
            "bind_ssusb_module": "/sys/module/dwc3_msm\n",
            "bind_typec_module": "/sys/module/pdic_max77705\n",
            "dmesg": (
                "[ 1.000000] max77705: max77705_ccic_event_notifier: usb: dest=BATTERY\n"
                "[ 1.000010] TCM: manager_handle_pdic_notification: dest:BATTERY\n"
                "[ 1.000020] TCM: manager_event_notify: dest:BATTERY\n"
                "[ 1.000030] TCM: manager_event_notify: notify done(0x0)\n"
            ),
        }
        commands = {label: self.command(values[label]) for label, _argv in self.module.DEVICE_COMMANDS}
        static_payload = {"result": "pass-static-role-path-reconstructed"}
        return static_payload, baseline, baseline_commands, commands

    def test_offline_contract_allows_only_fixed_reads(self):
        contract = self.module.offline_check()
        self.assertEqual(contract["result"], "pass")
        self.assertEqual(contract["device_command_count"], len(self.module.DEVICE_COMMANDS))
        self.assertTrue(all(contract["fixed_read_commands"].values()))

    def test_filter_keeps_only_role_chain_lines_and_strips_ansi(self):
        text = (
            "\x1b[31m[ 1.0] max77705_ccic_event_notifier event\x1b[0m\n"
            "unrelated serial-looking line\n"
            "[ 1.1] manager_event_notify: notify done\n"
        )
        filtered = self.module.filtered_dmesg(text)
        self.assertNotIn("\x1b", filtered)
        self.assertNotIn("unrelated", filtered)
        self.assertIn("max77705_ccic_event_notifier", filtered)

    def test_relay_sequence_requires_ordered_four_line_group(self):
        _static, _baseline, _baseline_commands, commands = self.fixture()
        self.assertEqual(self.module.relay_sequence_count(commands["dmesg"]["stdout"]), 1)
        reordered = "\n".join(reversed(commands["dmesg"]["stdout"].splitlines()))
        self.assertEqual(self.module.relay_sequence_count(reordered), 0)

    def test_exact_fixture_passes_with_partial_runtime_boundary(self):
        payload = self.module.summarize(*self.fixture())
        self.assertEqual(payload["result"], "pass-live-role-crosscheck-partial")
        self.assertTrue(all(payload["modules_loaded"].values()))
        self.assertTrue(all(payload["device_tree_checks"].values()))
        self.assertTrue(all(payload["driver_bind_checks"].values()))
        self.assertEqual(payload["conclusions"]["pdic_to_typec_manager_relay"], "LIVE_OBSERVED")
        self.assertEqual(
            payload["conclusions"]["usb_notifier_to_dwc3_role_event"],
            "NOT_CAPTURED_THIS_BOOT",
        )

    def test_missing_module_fails_closed(self):
        static_payload, baseline, baseline_commands, commands = self.fixture()
        baseline_commands["proc_modules"]["stdout"] = baseline_commands["proc_modules"]["stdout"].replace(
            "usb_notifier_qcom 1 0 - Live 0x0\n", ""
        )
        payload = self.module.summarize(static_payload, baseline, baseline_commands, commands)
        self.assertEqual(payload["result"], "fail")
        self.assertFalse(payload["modules_loaded"]["usb_notifier_qcom"])

    def test_source_has_no_mutating_device_operation(self):
        source = SCRIPT.read_text(encoding="ascii")
        for token in (
            "adb reboot",
            "odin4",
            "heimdall",
            "fastboot",
            "finit_module",
            "insmod",
            "rmmod",
            "ctl.stop",
            "ctl.start",
            "> /sys",
            "> /config",
        ):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
