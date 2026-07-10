import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT = Path(
    "workspace/public/src/scripts/revalidation/"
    "s22plus_v3434_boot_boundary_map.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "s22plus_v3434_boot_boundary_map", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class S22PlusV3434BootBoundaryMapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load_module()
        cls.root = cls.module.repo_root()
        cls.result = cls.module.build_map(cls.root)

    def test_host_only_verdict(self):
        self.assertEqual(self.result["verdict"], "HOST_STATIC_MAP_PASS_NO_LIVE")
        self.assertEqual(
            self.result["safety"],
            {
                "host_only": True,
                "device_contact": False,
                "image_build": False,
                "flash": False,
                "live_authorized": False,
            },
        )

    def test_committed_map_is_current(self):
        committed = (self.root / self.module.OUTPUT).read_text(encoding="utf-8")
        expected = json.dumps(self.result, indent=2, sort_keys=True) + "\n"
        self.assertEqual(committed, expected)

    def test_kernel_flow_reaches_pid1_in_order(self):
        flow = self.result["kernel_boot_boundary"]["ordered_flow"]
        for before, after in zip(flow, flow[1:]):
            self.assertLess(flow.index(before), flow.index(after))
        self.assertIn("start_kernel", flow)
        self.assertIn("rest_init creates kernel_init as PID 1", flow)
        self.assertIn("kernel_execve replaces PID 1 with /init", flow)

    def test_init_selection_and_pid1_failure_are_explicit(self):
        boundary = self.result["kernel_boot_boundary"]
        self.assertEqual(boundary["init_selection"]["default"], "/init")
        self.assertEqual(
            boundary["init_selection"]["fallback_order"],
            ["CONFIG_DEFAULT_INIT", "/sbin/init", "/etc/init", "/bin/init", "/bin/sh"],
        )
        self.assertEqual(
            boundary["pid1_failure"]["post_exec_pid1_exit"],
            "panic: Attempted to kill init",
        )
        self.assertIn("module insert", boundary["pid1_failure"]["v3432_gap"])

    def test_running_kernel_config_is_not_defconfig_inference(self):
        config = self.result["evidence"]["kernel_config"]
        self.assertEqual(config["CONFIG_IKCONFIG"], "y")
        self.assertEqual(config["CONFIG_DEVTMPFS"], "n")
        self.assertEqual(config["CONFIG_SERIAL_EARLYCON"], "y")
        self.assertEqual(config["CONFIG_PSTORE_RAM"], "y")
        self.assertEqual(config["CONFIG_WATCHDOG_HANDLE_BOOT_ENABLED"], "y")
        self.assertEqual(config["CONFIG_WATCHDOG_OPEN_TIMEOUT"], "0")
        self.assertEqual(config["CONFIG_NAMESPACES"], "y")
        self.assertEqual(config["CONFIG_PID_NS"], "n")
        self.assertEqual(config["CONFIG_USER_NS"], "n")
        self.assertEqual(config["CONFIG_SYSVIPC"], "n")
        self.assertEqual(config["CONFIG_NET_NS"], "y")
        self.assertEqual(config["CONFIG_VETH"], "y")

    def test_watchdog_ownership_map_uses_stock_order_and_live_proof(self):
        watchdog = self.result["watchdog"]
        self.assertEqual(
            watchdog["stock_first_stage"]["gh_virt_wdt_modules_load_position"], 5
        )
        self.assertEqual(
            watchdog["stock_first_stage"]["qcom_wdt_core_modules_load_position"], 6
        )
        self.assertIn("survived 120 seconds", watchdog["live_discriminator"])
        self.assertIn("stock init ownership", watchdog["direct_pid1_requirement"])

    def test_observation_channel_activation_is_stage_scoped(self):
        channels = {
            channel["name"]: channel
            for channel in self.result["observation_channels"]
        }
        self.assertEqual(channels["earlycon_uart"]["fyg8_state"], "UNAVAILABLE_DEFAULT")
        self.assertEqual(channels["ramoops_pstore"]["fyg8_state"], "UNAVAILABLE_DEFAULT")
        self.assertEqual(
            channels["sec_log_buf"]["fyg8_state"],
            "AVAILABLE_AFTER_STOCK_PID1_LOAD",
        )
        self.assertEqual(
            channels["sec_debug"]["fyg8_state"], "AVAILABLE_LATE_FIRST_STAGE"
        )
        self.assertEqual(
            channels["pmic_pon_reset_reason"]["fyg8_state"],
            "AVAILABLE_PRE_KERNEL_AS_RESET_CLASS",
        )
        self.assertEqual(
            channels["stock_usb_tty_control"]["fyg8_state"], "LIVE_PROVEN"
        )
        for channel in channels.values():
            self.assertTrue(channel["earliest_stage"])
            self.assertTrue(channel["claim_limit"])

    def test_boot_and_vendor_boot_v4_ownership_is_split(self):
        images = self.result["boot_images"]
        self.assertEqual(images["boot_v4"]["header_version"], 4)
        self.assertEqual(images["boot_v4"]["kernel_size"], 41490944)
        self.assertEqual(images["vendor_boot_v4"]["header_version"], 4)
        self.assertEqual(
            images["vendor_boot_v4"]["kernel_load_address"], "0x00008000"
        )
        self.assertEqual(
            images["vendor_boot_v4"]["ramdisk_load_address"], "0x02000000"
        )
        self.assertIn("dtb", images["ownership"]["vendor_boot"])
        self.assertIn("bootconfig", images["ownership"]["vendor_boot"])

    def test_abl_handoff_boundary_is_proved_but_kernel_entry_is_not(self):
        abl = self.result["abl_targeted_boundary"]
        self.assertEqual(abl["binary"]["elf_class"], "ELF32")
        self.assertEqual(abl["binary"]["elf_machine"], "ARM")
        self.assertEqual(abl["binary"]["entry_point"], "0x9fa00000")
        self.assertEqual(
            abl["handoff_result"],
            "FIRMWARE_EXIT_BOOT_SERVICES_BOUNDARY_REACHED",
        )
        self.assertEqual(
            abl["kernel_entry_result"],
            "UNVERIFIED_AFTER_EXIT_BOOT_SERVICES",
        )
        self.assertIn(
            "kernel reaching start_kernel",
            abl["unverified"],
        )
        self.assertIn("unlocked device skips boot verification", " ".join(abl["verified"]))
        self.assertIn("do not widen ABL", abl["decision"])

    def test_selected_architecture_matches_running_namespace_support(self):
        architecture = self.result["selected_architecture"]
        self.assertEqual(
            architecture["name"],
            "stock_global_pid1_with_mount_namespace_service_supervisor",
        )
        self.assertIn("stock Android init", architecture["global_pid1"])
        self.assertIn("mount namespace plus pivot_root; not chroot", architecture["debian_root"])
        self.assertIn("not PID 1", architecture["process_model"])
        self.assertIn("CONFIG_PID_NS=n", architecture["kernel_constraint"])
        self.assertIn("child subreaper", architecture["reaping_model"])
        self.assertIn("ttyGS0", architecture["control_plane"])
        self.assertIn("research-only", architecture["direct_pid1_track"])
        self.assertGreaterEqual(len(architecture["handoff_gates"]), 5)

    def test_script_contains_no_live_transport_or_flash_path(self):
        source = (self.root / SCRIPT).read_text(encoding="utf-8")
        self.assertNotIn("adb ", source)
        self.assertNotIn("odin4 ", source)
        self.assertNotIn("--live", source)
        self.assertNotIn("reboot(", source)


if __name__ == "__main__":
    unittest.main()
