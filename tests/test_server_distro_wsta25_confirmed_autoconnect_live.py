from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py")


class ServerDistroWsta25ConfirmedAutoconnectLiveTests(unittest.TestCase):
    def test_explicit_live_gate_is_fail_closed(self) -> None:
        args = SimpleNamespace(
            allow_confirmed_live=False,
            ack_credentialed_wifi=False,
            confirm_token="",
        )
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta25-blocked-explicit-live-allow-required"),
        )

        args.allow_confirmed_live = True
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta25-blocked-credentialed-wifi-ack-required"),
        )

        args.ack_credentialed_wifi = True
        args.confirm_token = "wrong"
        self.assertEqual(
            runner.explicit_live_gate(args),
            (False, "wsta25-blocked-confirm-token-required"),
        )

        args.confirm_token = runner.NATIVE_CONFIRM_TOKEN
        self.assertEqual(runner.explicit_live_gate(args), (True, "ok"))

    def test_status_ready_requires_profile_valid_enabled_and_ready(self) -> None:
        payload = {
            "native_wifi_uplink_client_decision": "native-wifi-uplink-client-pass",
            "native_wifi_uplink_client_secret_values_logged": "0",
            "version": runner.wsta24.UPLINK_SERVICE_VERSION,
            "op": "status",
            "owner": "native-init",
            "decision": "wifi-uplink-service-status-pass",
            "credentials": "0",
            "connect": "0",
            "dhcp_routing": "observed-only",
            "public_tunnel": "0",
            "secret_values_logged": "0",
            "config_profile_present": "1",
            "profile_valid": "1",
            "autoconnect_ready": "1",
            "autoconnect_enabled": "1",
        }

        self.assertTrue(runner.status_ready_for_confirmed_autoconnect(payload))
        for key in ("config_profile_present", "profile_valid", "autoconnect_ready", "autoconnect_enabled"):
            variant = {**payload, key: "0"}
            self.assertFalse(runner.status_ready_for_confirmed_autoconnect(variant))

    def test_helper_confirmed_ok_requires_pass_and_redaction(self) -> None:
        payload = {
            "native_wifi_uplink_client_decision": "native-wifi-uplink-client-pass",
            "native_wifi_uplink_client_requested_op": "autoconnect-confirmed",
            "native_wifi_uplink_client_secret_values_logged": "0",
            "version": runner.wsta24.UPLINK_SERVICE_VERSION,
            "op": "autoconnect",
            "owner": "native-init",
            "credentials": "private-config-gated",
            "connect": "confirm-gated",
            "dhcp_routing": "config-gated",
            "external_ping_execution": "0",
            "public_tunnel": "0",
            "secret_values_logged": "0",
            "rc": "0",
            "decision": "wifi-uplink-service-autoconnect-pass",
        }

        self.assertTrue(runner.helper_confirmed_ok(payload))
        self.assertFalse(runner.helper_confirmed_ok({**payload, "rc": "-1"}))
        self.assertFalse(runner.helper_confirmed_ok({**payload, "decision": "wifi-uplink-service-autoconnect-failed"}))
        self.assertFalse(runner.helper_confirmed_ok({**payload, "owner": "debian"}))
        self.assertFalse(runner.helper_confirmed_ok({**payload, "public_tunnel": "1"}))

    def test_classify_separates_gate_ready_confirmed_and_cleanup_failures(self) -> None:
        base = {
            "checks": {
                "explicit_live_gate": True,
                "native_v3387": True,
                "baseline_selftest_fail_zero": True,
                "final_selftest_fail_zero": True,
                "debian_ssh_marker": True,
                "helper_staged": True,
                "service_start_pass": True,
                "helper_status_pass": True,
                "autoconnect_ready": True,
                "helper_confirmed_pass": True,
                "service_stop_pass": True,
                "helper_cleanup_ok": True,
                "cleanup_ok": True,
            }
        }

        self.assertEqual(runner.classify(base), runner.PASS_DECISION)
        for key, decision in (
            ("explicit_live_gate", "wsta25-blocked-explicit-live-gate"),
            ("native_v3387", "wsta25-blocked-v3387-not-resident"),
            ("helper_status_pass", "wsta25-blocked-helper-status"),
            ("autoconnect_ready", "wsta25-blocked-autoconnect-not-ready"),
            ("helper_confirmed_pass", "wsta25-blocked-helper-confirmed-autoconnect"),
            ("cleanup_ok", "wsta25-blocked-cleanup"),
        ):
            variant = {"checks": {**base["checks"], key: False}}
            self.assertEqual(runner.classify(variant), decision)

    def test_redacted_script_executor_does_not_store_token_input(self) -> None:
        args = SimpleNamespace(
            ssh_port=2222,
            ssh_connect_timeout=8,
            device_ip="device.example",
        )
        run_dir = Path("/tmp/a90-wsta25-test")
        captured: dict[str, object] = {}

        def fake_run(command, **kwargs):  # type: ignore[no-untyped-def]
            captured["command"] = command
            captured["input"] = kwargs.get("input")
            return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

        with mock.patch.object(runner.subprocess, "run", side_effect=fake_run):
            record = runner.ssh_exec_redacted_script(
                args,
                run_dir,
                "secret-token-in-stdin",
                timeout=5.0,
                redacted_label="unit",
            )

        self.assertTrue(record["input_redacted"])
        self.assertEqual(record["redacted_label"], "unit")
        self.assertNotIn("secret-token-in-stdin", " ".join(record["command"]))
        self.assertEqual(captured["input"], "secret-token-in-stdin")

    def test_runner_surface_is_fail_closed_and_does_not_start_public_network_work(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("--allow-confirmed-live", source)
        self.assertIn("--ack-credentialed-wifi", source)
        self.assertIn("--confirm-token", source)
        self.assertIn("confirm_token_value_logged", source)
        self.assertIn("allow_not_ready_confirmed", source)
        self.assertIn("status_ready_for_confirmed_autoconnect", source)
        self.assertIn("input_redacted", source)
        self.assertIn('"boot_flash": False', source)
        self.assertIn('"switch_root": False', source)
        self.assertIn('"userdata_touch": False', source)
        self.assertIn('"public_tunnel": False', source)
        self.assertIn('"external_ping": False', source)
        self.assertNotIn("native_init_flash.py", source)

        for forbidden_command in (
            '["wifi", "connect"',
            '["wifi", "dhcp"',
            '["wifi", "ping"',
            "cloudflared tunnel",
            "ssid=",
            "psk=",
        ):
            self.assertNotIn(forbidden_command, source)


if __name__ == "__main__":
    unittest.main()
