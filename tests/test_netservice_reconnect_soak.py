from __future__ import annotations

import contextlib
import io
import unittest
from types import SimpleNamespace
from unittest import mock

from _loader import load_revalidation


netservice = load_revalidation("netservice_reconnect_soak.py")


def base_args(**overrides):
    values = {
        "bridge_host": "127.0.0.1",
        "bridge_port": 54321,
        "bridge_timeout": 45.0,
        "bridge_ready_timeout": 5.0,
        "device_protocol": "auto",
        "busy_retries": 2,
        "busy_retry_sleep": 0.0,
        "netservice_timeout": 45.0,
        "device_helper": netservice.DEFAULT_DEVICE_HELPER,
        "toybox": netservice.DEFAULT_TOYBOX,
        "device_ip": netservice.DEFAULT_DEVICE_IP,
        "host_ip": netservice.DEFAULT_HOST_IP,
        "prefix": netservice.DEFAULT_PREFIX,
        "interface_timeout": 1.0,
        "interface": None,
        "allow_auto_interface": False,
        "ping_count": 1,
        "ping_timeout": 1,
        "tcp_port": netservice.DEFAULT_TCP_PORT,
        "tcp_timeout": 2.0,
        "tcp_ready_timeout": 1.0,
        "token": None,
        "token_command": netservice.DEFAULT_TOKEN_COMMAND,
        "no_auth": False,
        "sudo": "sudo -n",
        "no_sudo": True,
        "no_configure_host": False,
        "manual_host_config": False,
        "manual_host_timeout": 1.0,
        "leave_running": False,
        "cycles": 2,
        "cycle_sleep": 0.0,
        "stop_on_failure": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class PureHelpers(unittest.TestCase):
    def test_parse_usbnet_status_normalizes_fields_and_tolerates_missing_values(self) -> None:
        text = "\n".join([
            "ncm.ifname: ncm0",
            "ncm.dev_addr: AA:BB:CC:DD:EE:01",
            "ncm.host_addr: AA:BB:CC:DD:EE:02",
        ])

        status = netservice.parse_usbnet_status(text)
        missing = netservice.parse_usbnet_status("ncm.ifname: ncm0\n")

        self.assertEqual(status.ifname, "ncm0")
        self.assertEqual(status.dev_addr, "aa:bb:cc:dd:ee:01")
        self.assertEqual(status.host_addr, "aa:bb:cc:dd:ee:02")
        self.assertEqual(status.raw, text)
        self.assertEqual(missing.ifname, "ncm0")
        self.assertIsNone(missing.dev_addr)
        self.assertIsNone(missing.host_addr)

    def test_host_interface_selection_requires_opt_in_or_matching_mac(self) -> None:
        status = netservice.UsbnetStatus("ncm0", "02:00:00:00:00:01", "02:00:00:00:00:02", "")

        with mock.patch.object(netservice, "os") as os_mock:
            os_mock.path.exists.return_value = True
            os_mock.geteuid.return_value = 1000
            with mock.patch.object(netservice, "sysfs_mac_for", return_value="02:00:00:00:00:02"):
                explicit = netservice.select_host_interface(base_args(interface="enx0"), status)
            self.assertEqual(explicit, "enx0")

        with self.assertRaisesRegex(RuntimeError, "refusing sudo host NIC"):
            netservice.select_host_interface(base_args(), status)

        with mock.patch.object(netservice, "wait_for_interface_by_mac", return_value="enxauto") as wait:
            selected = netservice.select_host_interface(base_args(allow_auto_interface=True), status)
        self.assertEqual(selected, "enxauto")
        wait.assert_called_once_with("02:00:00:00:00:02", 1.0)

    def test_tcpctl_auth_token_cache_and_auth_requirement_rules(self) -> None:
        args = base_args()
        with mock.patch.object(netservice, "device_command", return_value="tcpctl_token=0123456789abcdef0123456789ABCDEF\n") as device:
            token1 = netservice.get_tcpctl_token(args)
            token2 = netservice.get_tcpctl_token(args)

        self.assertEqual(token1, "0123456789abcdef0123456789ABCDEF")
        self.assertEqual(token2, token1)
        device.assert_called_once_with(args, args.token_command, timeout=args.bridge_timeout)
        self.assertTrue(netservice.tcpctl_command_requires_auth("run /cache/bin/toybox uptime"))
        self.assertTrue(netservice.tcpctl_command_requires_auth(" shutdown"))
        self.assertFalse(netservice.tcpctl_command_requires_auth("status"))
        with self.assertRaisesRegex(RuntimeError, "token was not found"):
            netservice.parse_tcpctl_token("no token")


class CommandFlow(unittest.TestCase):
    def test_start_and_stop_netservice_require_expected_ready_status_markers(self) -> None:
        args = base_args()
        commands: list[str] = []

        def fake_device(_args, command: str, **_kwargs) -> str:
            commands.append(command)
            if command == "netservice start":
                return "starting"
            if command == "netservice stop":
                return "stopping"
            raise AssertionError(command)

        with (
            mock.patch.object(netservice, "device_command", side_effect=fake_device),
            mock.patch.object(netservice, "wait_for_bridge_version", return_value="A90 Linux init\n") as wait,
            mock.patch.object(netservice, "netservice_status", side_effect=["ncm0=present tcpctl=running\n", "ncm0=absent tcpctl=stopped\n"]),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            netservice.start_netservice(args)
            netservice.stop_netservice(args)

        self.assertEqual(commands, ["netservice start", "netservice stop"])
        self.assertEqual(wait.call_count, 2)

        with (
            mock.patch.object(netservice, "device_command", return_value="starting"),
            mock.patch.object(netservice, "wait_for_bridge_version", return_value="A90 Linux init\n"),
            mock.patch.object(netservice, "netservice_status", return_value="ncm0=present tcpctl=stopped\n"),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            with self.assertRaisesRegex(RuntimeError, "did not report ready"):
                netservice.start_netservice(args)

    def test_verify_ncm_and_tcp_runs_ifconfig_host_setup_ping_and_tcpctl_checks(self) -> None:
        args = base_args(interface="enx0")
        status = netservice.UsbnetStatus(None, "02:00:00:00:00:01", "02:00:00:00:00:02", "")
        device_commands: list[str] = []
        tcp_commands: list[str] = []

        def fake_device(_args, command: str, **_kwargs) -> str:
            device_commands.append(command)
            return "[done]"

        def fake_tcp(_args, command: str, timeout=None) -> str:
            tcp_commands.append(command)
            return "OK\n"

        with (
            mock.patch.object(netservice, "get_usbnet_status", return_value=status),
            mock.patch.object(netservice, "device_command", side_effect=fake_device),
            mock.patch.object(netservice, "select_host_interface", return_value="enx0") as select,
            mock.patch.object(netservice, "configure_host_interface") as configure,
            mock.patch.object(netservice, "host_ping", return_value="0% packet loss\n") as ping,
            mock.patch.object(netservice, "wait_for_tcpctl", return_value="pong OK\n") as wait_tcp,
            mock.patch.object(netservice, "tcpctl_request", side_effect=fake_tcp),
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            netservice.verify_ncm_and_tcp(args)

        self.assertIn("run /cache/bin/toybox ifconfig ncm0 192.168.7.2 netmask 255.255.255.0 up", device_commands)
        select.assert_called_once_with(args, status)
        configure.assert_called_once_with(args, "enx0")
        ping.assert_called_once_with(args)
        wait_tcp.assert_called_once_with(args)
        self.assertEqual(tcp_commands, ["status", "run /cache/bin/toybox uptime"])

    def test_command_once_always_stops_final_when_not_left_running(self) -> None:
        args = base_args(leave_running=False)
        calls: list[str] = []

        def fake_stop(_args) -> None:
            calls.append("stop")

        def fake_start(_args) -> None:
            calls.append("start")

        def fake_verify(_args) -> None:
            calls.append("verify")

        with (
            mock.patch.object(netservice, "stop_netservice", side_effect=fake_stop),
            mock.patch.object(netservice, "start_netservice", side_effect=fake_start),
            mock.patch.object(netservice, "verify_ncm_and_tcp", side_effect=fake_verify),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            rc = netservice.command_once(args)

        self.assertEqual(rc, 0)
        self.assertEqual(calls, ["stop", "start", "verify", "stop"])

    def test_command_soak_collects_failures_and_final_stop_errors(self) -> None:
        args = base_args(cycles=2, stop_on_failure=True, leave_running=False)

        with (
            mock.patch.object(netservice, "stop_netservice", side_effect=[None, RuntimeError("final stop failed")]),
            mock.patch.object(netservice, "start_netservice", side_effect=RuntimeError("start failed")),
            mock.patch.object(netservice, "verify_ncm_and_tcp") as verify,
            mock.patch.object(netservice.time, "sleep") as sleep,
            contextlib.redirect_stdout(io.StringIO()),
        ):
            with self.assertRaisesRegex(RuntimeError, "netservice reconnect soak failed"):
                netservice.command_soak(args)

        verify.assert_not_called()
        sleep.assert_not_called()


class HostCommandHelpers(unittest.TestCase):
    def test_configure_host_interface_prints_manual_commands_when_config_disabled(self) -> None:
        args = base_args(no_configure_host=True)
        with (
            mock.patch.object(netservice, "interface_has_addr", return_value=False),
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            with self.assertRaisesRegex(RuntimeError, "does not have"):
                netservice.configure_host_interface(args, "enx0")

        self.assertIn("sudo ip addr replace 192.168.7.1/24 dev enx0", stderr.getvalue())

    def test_sudo_command_uses_prefix_only_for_non_root_without_no_sudo(self) -> None:
        args = base_args(no_sudo=False, sudo="sudo -n")
        with mock.patch.object(netservice.os, "geteuid", return_value=1000):
            self.assertEqual(netservice.sudo_command(args, ["ip", "link"]), ["sudo", "-n", "ip", "link"])
        self.assertEqual(netservice.sudo_command(base_args(no_sudo=True), ["ip", "link"]), ["ip", "link"])

    def test_device_command_falls_back_to_raw_when_cmdv1_marker_is_missing(self) -> None:
        args = base_args(device_protocol="auto")
        with (
            mock.patch.object(netservice, "run_device_cmdv1", side_effect=RuntimeError(netservice.CMDV1_END_MISSING_TEXT)) as cmdv1,
            mock.patch.object(netservice, "bridge_command", return_value="[done] raw\n") as bridge,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            output = netservice.device_command(args, "version")

        self.assertEqual(output, "[done] raw\n")
        cmdv1.assert_called_once()
        bridge.assert_called_once()


if __name__ == "__main__":
    unittest.main()
