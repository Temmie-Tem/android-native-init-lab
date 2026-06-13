from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from _loader import load_revalidation


dhcp = load_revalidation("native_wifi_dhcp_ping_handoff_v2176.py")


def base_manifest(**overrides):
    manifest = {
        "preflight": {
            "test_image_exists": True,
            "rollback_image_exists": True,
            "test_image": "workspace/private/inputs/boot_images/test.img",
            "test_image_sha256": "a" * 64,
            "rollback_image": "workspace/private/inputs/boot_images/rollback.img",
            "rollback_image_sha256": "b" * 64,
        },
        "wifi_secret_status": {"valid": True},
        "transport_selection": {"status_ok": True},
        "test_flash_ok": True,
        "rollback": {"ok": True, "attempt": "from-native", "selftest_ok": True},
        "connect": {
            "ok": True,
            "decision": "wifi-connect-pass",
            "carrier_up": "1",
            "wpa_state": "COMPLETED",
            "secret_values_logged": "0",
            "credentials_logged": "0",
        },
        "dhcp_ping": {
            "ok": True,
            "dhcp_decision": "wifi-dhcp-pass",
            "dhcp_rc": "0",
            "ipv4_assigned": "1",
            "route_default_present": "1",
            "resolv_conf_nameserver_count": "2",
            "external_ping_target": "example.test",
            "external_ping_rc": "0",
            "external_ping_bytes_from": "1",
            "cleanup_ok": True,
            "cleanup_decision": "wifi-cleanup-done",
            "secret_values_logged": "0",
            "credentials_logged": "0",
        },
        "phase_timers": [],
        "out_dir": "workspace/private/runs/wifi/example",
    }
    manifest.update(overrides)
    return manifest


class PureHelpers(unittest.TestCase):
    def test_classify_prioritizes_preflight_flash_rollback_failures(self) -> None:
        cases = [
            (
                {"preflight": {"test_image_exists": False, "rollback_image_exists": True}},
                "v2176-dhcp-preflight-image-missing",
                "image missing",
            ),
            (
                {"wifi_secret_status": {"valid": False}},
                "v2176-dhcp-preflight-wifi-env-missing-no-flash",
                "Wi-Fi env",
            ),
            (
                {"transport_selection": {"status_ok": False}},
                "v2176-dhcp-preflight-native-unavailable-no-flash",
                "native status",
            ),
            (
                {"test_flash_ok": False},
                "v2176-dhcp-test-flash-failed",
                "flash failed",
            ),
            (
                {"rollback": {"ok": True, "selftest_ok": False}},
                "v2176-dhcp-rollback-selftest-failed",
                "rollback",
            ),
        ]

        for override, decision, reason_fragment in cases:
            with self.subTest(decision=decision):
                result = dhcp.classify(base_manifest(**override))
                self.assertFalse(result["pass"])
                self.assertEqual(result["decision"], decision)
                self.assertIn(reason_fragment, result["reason"])

    def test_classify_pass_requires_connect_dhcp_cleanup_and_secret_hygiene(self) -> None:
        passed = dhcp.classify(base_manifest())
        self.assertTrue(passed["pass"])
        self.assertEqual(passed["decision"], "v2176-dhcp-ping-rollback-pass")

        failing_overrides = [
            {"connect": {"ok": False, "secret_values_logged": "0", "credentials_logged": "0"}},
            {"dhcp_ping": {"ok": False, "cleanup_ok": True, "secret_values_logged": "0", "credentials_logged": "0"}},
            {"dhcp_ping": {"ok": True, "cleanup_ok": False, "secret_values_logged": "0", "credentials_logged": "0"}},
            {"connect": {"ok": True, "secret_values_logged": "1", "credentials_logged": "0"}},
            {"dhcp_ping": {"ok": True, "cleanup_ok": True, "secret_values_logged": "0", "credentials_logged": "1"}},
        ]

        for override in failing_overrides:
            with self.subTest(override=override):
                result = dhcp.classify(base_manifest(**override))
                self.assertFalse(result["pass"])
                self.assertEqual(result["decision"], "v2176-dhcp-ping-failed-rollback-pass")

    def test_render_report_keeps_public_output_metadata_only(self) -> None:
        manifest = base_manifest(
            classification={
                "decision": "v2176-dhcp-ping-rollback-pass",
                "pass": True,
                "reason": "ok",
            },
            phase_timers=[{"name": "dhcp_ping_window", "elapsed_sec": 12.3}],
        )

        report = dhcp.render_report(manifest)

        self.assertIn("# Native Init V2176 Wi-Fi DHCP Ping Live Validation", report)
        self.assertIn("- Decision: `v2176-dhcp-ping-rollback-pass`", report)
        self.assertIn("Raw SSID, PSK, BSSID, MAC, assigned IP, route, DNS, DHCP lease", report)
        self.assertIn("- `dhcp_ping_window`: `12.3` sec", report)
        self.assertIn("- Rollback selftest fail=0: `True`", report)

    def test_run_ping_step_quotes_target_and_uses_a90ctl_run_scope(self) -> None:
        steps = []
        with mock.patch.object(dhcp.v2174, "a90ctl_step", return_value={"ok": True}) as a90ctl_step:
            result = dhcp.run_ping_step(object(), steps, "bad target; reboot")

        self.assertEqual(result, {"ok": True})
        args = a90ctl_step.call_args.args
        kwargs = a90ctl_step.call_args.kwargs
        self.assertEqual(args[2], "test-wifi-external-ping")
        self.assertEqual(args[3][:4], ["run", "/cache/bin/busybox", "sh", "-c"])
        self.assertIn("bad target; reboot", args[3][4])
        self.assertIn("'bad target; reboot'", args[3][4])
        self.assertEqual(kwargs["timeout"], 60)
        self.assertEqual(kwargs["bridge_timeout"], 45)

    def test_run_dhcp_window_skips_ping_when_dhcp_fails_but_still_cleans_up(self) -> None:
        steps = []

        def fake_a90ctl_step(store, step_list, name, command, **kwargs):
            step_list.append({"name": name, "command": command})
            return {"ok": True}

        def fake_step_stdout(store, step):
            if step and step.get("name") == "test-wifi-dhcp":
                return "decision=wifi-dhcp-failed\ndhcp_rc=1\nsecret_values_logged=0\ncredentials_logged=0\n"
            if step and step.get("name") == "test-wifi-cleanup":
                return "decision=wifi-cleanup-done\n"
            return ""

        with (
            mock.patch.object(dhcp.v2174, "a90ctl_step", side_effect=fake_a90ctl_step),
            mock.patch.object(dhcp.v2174, "step_stdout", side_effect=fake_step_stdout),
            mock.patch.object(dhcp, "run_ping_step") as run_ping_step,
        ):
            result = dhcp.run_dhcp_window(object(), steps, "temmie2.4G", "example.test")

        run_ping_step.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertEqual(result["dhcp_decision"], "wifi-dhcp-failed")
        self.assertEqual(result["external_ping_executed"], "0")
        self.assertTrue(result["cleanup_ok"])
        self.assertIn("test-wifi-residual-before-cleanup", [step["name"] for step in steps])
        self.assertIn("test-wifi-residual-after-cleanup", [step["name"] for step in steps])

    def test_run_dhcp_window_executes_ping_after_dhcp_pass(self) -> None:
        steps = []

        def fake_a90ctl_step(store, step_list, name, command, **kwargs):
            step_list.append({"name": name, "command": command})
            return {"ok": True}

        def fake_run_ping_step(store, step_list, target):
            step_list.append({"name": "test-wifi-external-ping", "target": target})
            return {"ok": True}

        def fake_step_stdout(store, step):
            if step and step.get("name") == "test-wifi-dhcp":
                return "\n".join([
                    "decision=wifi-dhcp-pass",
                    "dhcp_rc=0",
                    "ipv4_assigned=1",
                    "route_default_present=1",
                    "resolv_conf.present=1",
                    "resolv_conf.nameserver_count=2",
                    "secret_values_logged=0",
                    "credentials_logged=0",
                ])
            if step and step.get("name") == "test-wifi-external-ping":
                return "\n".join([
                    "external_ping_executed=1",
                    "external_ping_rc=0",
                    "external_ping_output.bytes_from=1",
                    "external_ping_output.bad_address=0",
                    "external_ping_output.network_unreachable=0",
                    "external_ping_output.packet_loss_100=0",
                ])
            if step and step.get("name") == "test-wifi-cleanup":
                return "decision=wifi-cleanup-done\n"
            return ""

        with (
            mock.patch.object(dhcp.v2174, "a90ctl_step", side_effect=fake_a90ctl_step),
            mock.patch.object(dhcp.v2174, "step_stdout", side_effect=fake_step_stdout),
            mock.patch.object(dhcp.v2174, "redact_wifi_evidence", side_effect=lambda text: text),
            mock.patch.object(dhcp, "run_ping_step", side_effect=fake_run_ping_step) as run_ping_step,
        ):
            result = dhcp.run_dhcp_window(object(), steps, None, "example.test")

        run_ping_step.assert_called_once()
        self.assertTrue(result["ok"])
        self.assertEqual(result["dhcp_decision"], "wifi-dhcp-pass")
        self.assertEqual(result["external_ping_executed"], "1")
        self.assertEqual(result["external_ping_bytes_from"], "1")
        self.assertTrue(result["cleanup_ok"])

    def test_rel_and_flash_command_delegate_to_v2174_helpers(self) -> None:
        inside = dhcp.REPO_ROOT / "docs"
        self.assertEqual(dhcp.rel(inside), "docs")

        with mock.patch.object(dhcp.v2174, "flash_command", return_value=["flash", "ok"]) as flash_command:
            result = dhcp.flash_command(Path("boot.img"), "expected-version", from_native=True)

        self.assertEqual(result, ["flash", "ok"])
        flash_command.assert_called_once_with(Path("boot.img"), "expected-version", from_native=True)


if __name__ == "__main__":
    unittest.main()
