import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "workspace/public/src/scripts/revalidation/s22plus_stock_usb_topology_readonly.py"


def load_module():
    spec = importlib.util.spec_from_file_location("s22plus_stock_usb_topology_readonly_tested", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusStockUsbTopologyReadonlyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()

    def fixture_commands(self):
        good = {label: {"rc": 0, "stdout": "", "stderr": ""} for label, _ in self.module.DEVICE_COMMANDS}
        good["devnull_stat"]["stdout"] = "character special file|666|1:3|0|u:object_r:null_device:s0\n"
        good["root_id"]["stdout"] = "uid=0(root) gid=0(root) context=u:r:magisk:s0\n"
        good["root_boot_sha256"] = {"rc": 1, "stdout": "", "stderr": "Permission denied"}
        good["proc_modules"]["stdout"] = "dwc3_msm 1 0 - Live\nsec_log_buf 1 0 - Live\nsec_debug 1 0 - Live\n"
        good["dumpsys_usb"]["stdout"] = """
 connected=true
 configured=true
 supported_modes=dual
 current_mode=ufp
 power_role=sink
 data_role=device
 IsDeviceConnected :true
"""
        good["usb_role_class"]["stdout"] = "a600000.dwc3-role-switch\na600000.ssusb-role-switch\n"
        good["ssusb_driver"]["stdout"] = "/sys/bus/platform/drivers/msm-dwc3\n"
        good["dwc3_driver"]["stdout"] = "/sys/bus/platform/drivers/dwc3\n"
        good["ssusb_of_node"]["stdout"] = "/sys/firmware/devicetree/base/soc/ssusb@a600000\n"
        good["dwc3_of_node"]["stdout"] = "/sys/firmware/devicetree/base/soc/ssusb@a600000/dwc3@a600000\n"
        good["ssusb_role"]["stdout"] = "device\n"
        good["udc_state"]["stdout"] = "configured\n"
        good["gadget_udc"]["stdout"] = "a600000.dwc3\n"
        good["typec_port_path"]["stdout"] = (
            "/sys/devices/platform/soc/994000.i2c/i2c-57/57-0066/"
            "max77705-usbc/typec/port0\n"
        )
        good["typec_driver"]["stdout"] = "/sys/bus/platform/drivers/max77705-usbc\n"
        good["typec_data_role"]["stdout"] = "host [device]\n"
        good["typec_power_role"]["stdout"] = "source [sink]\n"
        good["typec_port_type"]["stdout"] = "[dual] source sink\n"
        good["extcon_class"]["stdout"] = (
            "extcon0 -> ../../devices/platform/soc/soc:qcom,msm-ext-disp/extcon/extcon0\n"
            "extcon2 -> ../../devices/platform/soc/88e0000.qcom,msm-eud/extcon/extcon2\n"
        )
        return good

    def test_redaction_removes_device_serial_and_mac(self):
        text = "ID_SERIAL_SHORT=RFCT0000000 mac=00:11:22:33:44:55"
        redacted = self.module.redact(text, "RFCT0000000")
        self.assertNotIn("RFCT0000000", redacted)
        self.assertNotIn("00:11:22:33:44:55", redacted)
        self.assertIn("<S22_SERIAL_REDACTED>", redacted)

    def test_adb_device_parser_keeps_raw_selection_value(self):
        devices = self.module.parse_adb_devices(
            "List of devices attached\nRFCT0000000\tdevice product:g0qksx model:SM_S906N\n"
        )
        self.assertEqual(devices, ["RFCT0000000"])

    def test_summary_keeps_denial_distinct_from_live_bind(self):
        properties = {
            "ro.product.model": "SM-S906N",
            "ro.product.device": "g0q",
            "ro.build.version.incremental": "S906NKSS7FYG8",
            "sys.boot_completed": "1",
            "init.svc.bootanim": "stopped",
        }
        result = self.module.summarize(
            properties,
            self.fixture_commands(),
            {"usb_id": "04e8:6860", "sysfs_path": "/sys/mock", "udev": {}},
        )
        self.assertEqual(result["result"], "pass-stock-topology-partial")
        self.assertEqual(result["stock_state"]["boot_sha256"], "READ_DENIED")
        self.assertEqual(result["conclusions"]["stock_dwc3_device_path"], "LIVE_BOUND")
        self.assertEqual(result["conclusions"]["max77705_typec_port"], "LIVE_BOUND")
        self.assertEqual(
            result["conclusions"]["max77705_to_dwc3_role_propagation"],
            "UNVERIFIABLE",
        )
        self.assertIn("root_boot_sha256", result["sysfs"]["read_denials"])
        self.assertTrue(result["usb_manager"]["device_connected"])
        self.assertEqual(result["typec"]["data_role"], "device")
        self.assertEqual(result["typec"]["power_role"], "sink")
        self.assertEqual(result["typec"]["port_type"], "dual")
        self.assertTrue(result["typec"]["max77705_usbc_provider"])

    def test_of_node_falls_back_to_observed_symlink(self):
        commands = self.fixture_commands()
        commands["ssusb_of_node"]["stdout"] = ""
        commands["ssusb_platform"]["stdout"] = (
            "lrwxrwxrwx 1 root root 0 of_node -> ../../firmware/devicetree/base/soc/ssusb@a600000\n"
        )
        result = self.module.summarize(
            {
                "ro.product.model": "SM-S906N",
                "ro.product.device": "g0q",
                "ro.build.version.incremental": "S906NKSS7FYG8",
                "sys.boot_completed": "1",
                "init.svc.bootanim": "stopped",
            },
            commands,
            {"usb_id": "04e8:6860", "sysfs_path": "/sys/mock", "udev": {}},
        )
        self.assertEqual(
            result["sysfs"]["ssusb_of_node"],
            "../../firmware/devicetree/base/soc/ssusb@a600000",
        )

    def test_offline_contract_forbids_device_mutation(self):
        contract = self.module.offline_check()
        self.assertEqual(contract["result"], "pass")
        self.assertTrue(contract["safety"]["device_read_only"])
        self.assertTrue(all(contract["fixed_read_commands"].values()))
        for key in (
            "flash",
            "reboot",
            "module_insertion",
            "service_control",
            "sysfs_write",
            "configfs_write",
            "partition_write",
        ):
            self.assertFalse(contract["safety"][key])

    def test_device_commands_are_fixed_read_operations(self):
        allowed = {"getprop", "stat", "su", "cat", "dumpsys", "cmd", "ls", "readlink"}
        for _label, argv in self.module.DEVICE_COMMANDS:
            self.assertIn(argv[0], allowed)
        command_text = "\n".join(
            " ".join(argv) for _label, argv in self.module.DEVICE_COMMANDS
        )
        for token in ("adb reboot", "finit_module", "insmod", "rmmod", "ctl.stop", "ctl.start"):
            self.assertNotIn(token, command_text)
        for _label, argv in self.module.DEVICE_COMMANDS:
            if argv[0] == "su":
                self.assertEqual(argv[1], "-c")
                self.assertNotRegex(argv[2], r"[;|&><`]" )
                self.assertNotIn("$(", argv[2])


if __name__ == "__main__":
    unittest.main()
