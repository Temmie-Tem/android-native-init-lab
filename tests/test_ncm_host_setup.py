from __future__ import annotations

import argparse
import unittest
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


ncm_setup = load_script("workspace/public/src/scripts/revalidation/ncm_host_setup.py")


def args(**overrides):
    defaults = {
        "bridge_host": "127.0.0.1",
        "bridge_port": 54321,
        "bridge_timeout": 3.0,
        "device_protocol": "auto",
        "busy_retries": 2,
        "busy_retry_sleep": 0.0,
        "device_helper": "/cache/bin/a90_usbnet",
        "toybox": "/bin/busybox",
        "device_ip": "192.168.7.2",
        "host_ip": "192.168.7.1",
        "prefix": 24,
        "interface_timeout": 1.0,
        "interface": None,
        "allow_auto_interface": False,
        "ping_count": 1,
        "ping_timeout": 1,
        "reattach_sleep": 0.0,
        "sudo": "sudo -n",
        "no_sudo": False,
        "manual_host_config": False,
        "manual_host_timeout": 1.0,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class ParseAndValidationHelpers(unittest.TestCase):
    def test_parse_status_extracts_fields_lowercases_macs_and_preserves_raw(self) -> None:
        raw = (
            "noise\n"
            "ncm.ifname: ncm0\n"
            "ncm.dev_addr: 02:AA:BB:CC:DD:EE\n"
            "ncm.host_addr: 56:6C:B8:D2:17:E9\n"
        )
        status = ncm_setup.parse_status(raw)
        self.assertEqual(status.ifname, "ncm0")
        self.assertEqual(status.dev_addr, "02:aa:bb:cc:dd:ee")
        self.assertEqual(status.host_addr, "56:6c:b8:d2:17:e9")
        self.assertIs(status.raw, raw)

        missing = ncm_setup.parse_status("ncm.ifname missing\n")
        self.assertIsNone(missing.ifname)
        self.assertIsNone(missing.dev_addr)
        self.assertIsNone(missing.host_addr)

    def test_prefix_to_netmask_cmdv1_unavailable_and_sudo_prefix(self) -> None:
        self.assertEqual(ncm_setup.prefix_to_netmask(24), "255.255.255.0")
        self.assertEqual(ncm_setup.prefix_to_netmask(30), "255.255.255.252")
        self.assertTrue(ncm_setup.cmdv1_unavailable(OSError("offline")))
        self.assertTrue(ncm_setup.cmdv1_unavailable(RuntimeError(ncm_setup.CMDV1_END_MISSING_TEXT)))
        self.assertFalse(ncm_setup.cmdv1_unavailable(RuntimeError("real device error")))

        with mock.patch.object(ncm_setup.os, "geteuid", return_value=1000):
            self.assertEqual(ncm_setup.sudo_prefix(args(sudo="sudo -n")), ["sudo", "-n"])
            self.assertEqual(ncm_setup.sudo_prefix(args(no_sudo=True)), [])
        with mock.patch.object(ncm_setup.os, "geteuid", return_value=0):
            self.assertEqual(ncm_setup.sudo_prefix(args(sudo="sudo -n")), [])

    def test_validate_host_interface_name_accepts_safe_existing_and_rejects_unsafe(self) -> None:
        with mock.patch.object(ncm_setup.os.path, "exists", return_value=True):
            ncm_setup.validate_host_interface_name("enx566cb8d217e9")
            ncm_setup.validate_host_interface_name("usb0.10")

        for bad in ("", ".", "..", "bad/name", "bad name", "bad$"):
            with self.subTest(bad=bad), self.assertRaises(RuntimeError):
                ncm_setup.validate_host_interface_name(bad)

        with mock.patch.object(ncm_setup.os.path, "exists", return_value=False), \
                self.assertRaises(RuntimeError):
            ncm_setup.validate_host_interface_name("enx0")


class InterfaceSelection(unittest.TestCase):
    def test_select_host_interface_explicit_validates_name_and_mac_match(self) -> None:
        status = ncm_setup.UsbnetStatus(
            ifname="ncm0",
            dev_addr=None,
            host_addr="56:6c:b8:d2:17:e9",
            raw="",
        )
        with mock.patch.object(ncm_setup, "validate_host_interface_name") as validate, \
                mock.patch.object(ncm_setup, "sysfs_mac_for", return_value="56:6c:b8:d2:17:e9"):
            self.assertEqual(ncm_setup.select_host_interface(args(interface="enx0"), status), "enx0")
        validate.assert_called_once_with("enx0")

        with mock.patch.object(ncm_setup, "validate_host_interface_name"), \
                mock.patch.object(ncm_setup, "sysfs_mac_for", return_value="00:11:22:33:44:55"), \
                self.assertRaises(RuntimeError):
            ncm_setup.select_host_interface(args(interface="enx0"), status)

    def test_select_host_interface_auto_requires_verified_ncm_or_explicit_opt_in(self) -> None:
        status = ncm_setup.UsbnetStatus(
            ifname="ncm0",
            dev_addr=None,
            host_addr="56:6c:b8:d2:17:e9",
            raw="",
        )
        with mock.patch.object(ncm_setup, "find_interface_by_mac", return_value="enx0"), \
                mock.patch.object(ncm_setup, "host_interface_is_verified_a90_ncm", return_value=True):
            self.assertEqual(ncm_setup.select_host_interface(args(), status), "enx0")

        with mock.patch.object(ncm_setup, "find_interface_by_mac", return_value="eth0"), \
                mock.patch.object(ncm_setup, "host_interface_is_verified_a90_ncm", return_value=False), \
                self.assertRaises(RuntimeError):
            ncm_setup.select_host_interface(args(), status)

        with mock.patch.object(ncm_setup, "find_interface_by_mac", return_value=None), \
                mock.patch.object(ncm_setup, "wait_for_interface_by_mac", return_value="enx1") as wait:
            self.assertEqual(
                ncm_setup.select_host_interface(args(allow_auto_interface=True, interface_timeout=4.0), status),
                "enx1",
            )
        wait.assert_called_once_with("56:6c:b8:d2:17:e9", 4.0)

        no_mac = ncm_setup.UsbnetStatus(ifname="ncm0", dev_addr=None, host_addr=None, raw="")
        with self.assertRaises(RuntimeError):
            ncm_setup.select_host_interface(args(allow_auto_interface=True), no_mac)


class DeviceCommandProtocol(unittest.TestCase):
    def test_device_command_uses_cmdv1_result_and_enforces_status_by_default(self) -> None:
        ok = SimpleNamespace(status="ok", rc=0, text="ok text")
        with mock.patch.object(ncm_setup, "run_device_cmdv1", return_value=ok) as run_cmdv1:
            self.assertEqual(ncm_setup.device_command(args(), "version"), "ok text")
        run_cmdv1.assert_called_once()

        failed = SimpleNamespace(status="ok", rc=7, text="bad")
        with mock.patch.object(ncm_setup, "run_device_cmdv1", return_value=failed), \
                self.assertRaises(RuntimeError):
            ncm_setup.device_command(args(), "bad")
        with mock.patch.object(ncm_setup, "run_device_cmdv1", return_value=failed):
            self.assertEqual(ncm_setup.device_command(args(), "bad", allow_error=True), "bad")

    def test_device_command_auto_falls_back_to_raw_bridge_only_for_unavailable_cmdv1(self) -> None:
        with mock.patch.object(ncm_setup, "run_device_cmdv1", side_effect=RuntimeError(ncm_setup.CMDV1_END_MISSING_TEXT)), \
                mock.patch.object(ncm_setup, "bridge_command", return_value="raw [done]") as bridge:
            self.assertEqual(ncm_setup.device_command(args(), "version"), "raw [done]")
        bridge.assert_called_once()

        with mock.patch.object(ncm_setup, "run_device_cmdv1", side_effect=RuntimeError("real failure")), \
                self.assertRaises(RuntimeError):
            ncm_setup.device_command(args(), "version")

    def test_device_command_busy_hides_menu_then_retries_cmdv1(self) -> None:
        busy = SimpleNamespace(status="busy", rc=0, text="busy text\n")
        ok = SimpleNamespace(status="ok", rc=0, text="ok text")
        with mock.patch.object(ncm_setup, "run_device_cmdv1", side_effect=[busy, ok]) as run_cmdv1, \
                mock.patch.object(ncm_setup, "bridge_command", return_value="hidden [done]") as bridge:
            self.assertEqual(ncm_setup.device_command(args(busy_retries=3), "version"), "ok text")

        self.assertEqual(run_cmdv1.call_count, 2)
        bridge.assert_called_once()
        self.assertEqual(bridge.call_args.args[2], "hide")


class HostConfiguration(unittest.TestCase):
    def test_configure_host_interface_nmcli_runs_profile_commands_and_waits_for_cidr(self) -> None:
        with mock.patch.object(ncm_setup.shutil, "which", return_value="/usr/bin/nmcli"), \
                mock.patch.object(
                    ncm_setup,
                    "run_host_command_result",
                    return_value=SimpleNamespace(returncode=0, stdout="", stderr=""),
                ) as run_result, \
                mock.patch.object(ncm_setup, "wait_for_host_addr") as wait:
            self.assertTrue(ncm_setup.configure_host_interface_nmcli("enx0", "192.168.7.1/24"))

        self.assertEqual(
            [call.args[0][:3] for call in run_result.call_args_list],
            [["nmcli", "connection", "delete"], ["nmcli", "connection", "add"], ["nmcli", "connection", "up"]],
        )
        wait.assert_called_once_with("enx0", "192.168.7.1/24", 10.0)

        with mock.patch.object(ncm_setup.shutil, "which", return_value=None), \
                mock.patch.object(ncm_setup, "run_host_command_result") as run_result:
            self.assertFalse(ncm_setup.configure_host_interface_nmcli("enx0", "192.168.7.1/24"))
        run_result.assert_not_called()

    def test_configure_host_interface_skips_ready_nmcli_or_uses_sudo_fallback(self) -> None:
        setup_args = args(host_ip="192.168.7.1", prefix=24)
        with mock.patch.object(ncm_setup, "interface_has_addr", return_value=True), \
                mock.patch.object(ncm_setup, "configure_host_interface_nmcli") as nmcli, \
                mock.patch.object(ncm_setup, "run_host_command") as run_host:
            ncm_setup.configure_host_interface(setup_args, "enx0")
        nmcli.assert_not_called()
        run_host.assert_not_called()

        with mock.patch.object(ncm_setup, "interface_has_addr", return_value=False), \
                mock.patch.object(ncm_setup, "configure_host_interface_nmcli", return_value=True), \
                mock.patch.object(ncm_setup, "run_host_command") as run_host:
            ncm_setup.configure_host_interface(setup_args, "enx0")
        run_host.assert_not_called()

        with mock.patch.object(ncm_setup, "interface_has_addr", return_value=False), \
                mock.patch.object(ncm_setup, "configure_host_interface_nmcli", return_value=False), \
                mock.patch.object(ncm_setup, "run_host_command") as run_host:
            ncm_setup.configure_host_interface(setup_args, "enx0")
        self.assertEqual(
            [call.args[1] for call in run_host.call_args_list],
            [
                ["ip", "addr", "replace", "192.168.7.1/24", "dev", "enx0"],
                ["ip", "link", "set", "enx0", "up"],
            ],
        )
        self.assertTrue(all(call.kwargs["use_sudo"] for call in run_host.call_args_list))

    def test_configure_host_interface_manual_fallback_prints_commands_and_waits(self) -> None:
        setup_args = args(host_ip="192.168.7.1", prefix=24, manual_host_config=True, manual_host_timeout=7.0)
        with mock.patch.object(ncm_setup, "interface_has_addr", return_value=False), \
                mock.patch.object(ncm_setup, "configure_host_interface_nmcli", return_value=False), \
                mock.patch.object(ncm_setup, "run_host_command", side_effect=RuntimeError("sudo denied")), \
                mock.patch.object(ncm_setup, "print_required_host_commands") as print_commands, \
                mock.patch.object(ncm_setup, "wait_for_host_addr") as wait:
            ncm_setup.configure_host_interface(setup_args, "enx0")

        print_commands.assert_called_once_with("enx0", "192.168.7.1/24")
        wait.assert_called_once_with("enx0", "192.168.7.1/24", 7.0)


class CommandOrchestration(unittest.TestCase):
    def test_command_setup_enables_missing_ncm_configures_device_host_and_pings(self) -> None:
        inactive = ncm_setup.UsbnetStatus(ifname=None, dev_addr=None, host_addr=None, raw="first")
        active = ncm_setup.UsbnetStatus(
            ifname="ncm0",
            dev_addr="02:aa:bb:cc:dd:ee",
            host_addr="56:6c:b8:d2:17:e9",
            raw="second",
        )
        setup_args = args()
        with mock.patch.object(ncm_setup, "get_usbnet_status", side_effect=[inactive, active]) as status, \
                mock.patch.object(ncm_setup, "device_command", return_value="device ok\n") as device_command, \
                mock.patch.object(ncm_setup, "select_host_interface", return_value="enx0") as select, \
                mock.patch.object(ncm_setup, "configure_host_interface") as configure, \
                mock.patch.object(ncm_setup, "run_ping") as ping:
            self.assertEqual(ncm_setup.command_setup(setup_args), 0)

        self.assertEqual(status.call_count, 2)
        self.assertEqual(
            [call.args[1] for call in device_command.call_args_list],
            [
                "run /cache/bin/a90_usbnet ncm",
                "run /bin/busybox ifconfig ncm0 192.168.7.2 netmask 255.255.255.0 up",
            ],
        )
        select.assert_called_once_with(setup_args, active)
        configure.assert_called_once_with(setup_args, "enx0")
        ping.assert_called_once_with(setup_args)

    def test_command_setup_fails_closed_when_status_lacks_ifname_or_host_mac(self) -> None:
        with mock.patch.object(
            ncm_setup,
            "get_usbnet_status",
            return_value=ncm_setup.UsbnetStatus(ifname=None, dev_addr=None, host_addr="56:6c:b8:d2:17:e9", raw=""),
        ), mock.patch.object(ncm_setup, "device_command", return_value="still missing"):
            with self.assertRaises(RuntimeError):
                ncm_setup.command_setup(args())


if __name__ == "__main__":
    unittest.main()
