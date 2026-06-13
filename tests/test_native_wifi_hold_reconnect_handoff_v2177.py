from __future__ import annotations

import unittest
from unittest import mock

from _loader import load_revalidation


hold = load_revalidation("native_wifi_hold_reconnect_handoff_v2177.py")


def clean_connect():
    return {
        "ok": True,
        "decision": "wifi-connect-carrier-up",
        "carrier_up": "1",
        "wpa_state": "COMPLETED",
        "secret_values_logged": "0",
        "credentials_logged": "0",
    }


def clean_dhcp():
    return {
        "ok": True,
        "dhcp_decision": "wifi-dhcp-pass",
        "external_ping_rc": "0",
        "secret_values_logged": "0",
        "credentials_logged": "0",
    }


def clean_cleanup():
    return {
        "ok": True,
        "cleanup_decision": "wifi-cleanup-done",
        "residue_clean": True,
    }


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
        "initial": {"connect": clean_connect(), "dhcp_ping": clean_dhcp()},
        "hold": {
            "ok": True,
            "hold_sec": 180,
            "samples": 2,
            "sample_ok": True,
            "final_ping_rc": "0",
            "carrier_values": ["1", "1"],
            "route_values": ["1", "1"],
            "resolv_conf_values": ["1", "1"],
            "operstate_values": ["up", "up"],
            "supplicant_count_values": ["1", "1"],
            "udhcpc_pidfile_values": ["1", "1"],
        },
        "disconnect": clean_cleanup(),
        "reconnect": {
            "connect": clean_connect(),
            "dhcp_ping": clean_dhcp(),
            "cleanup": clean_cleanup(),
        },
        "phase_timers": [],
        "out_dir": "workspace/private/runs/wifi/example",
    }
    manifest.update(overrides)
    return manifest


class PureHelpers(unittest.TestCase):
    def test_classify_prioritizes_preflight_flash_and_rollback_failures(self) -> None:
        cases = [
            (
                {"preflight": {"test_image_exists": False, "rollback_image_exists": True}},
                "v2177-hold-reconnect-preflight-image-missing",
            ),
            (
                {"wifi_secret_status": {"valid": False}},
                "v2177-hold-reconnect-wifi-env-missing-no-flash",
            ),
            (
                {"transport_selection": {"status_ok": False}},
                "v2177-hold-reconnect-native-unavailable-no-flash",
            ),
            (
                {"test_flash_ok": False},
                "v2177-hold-reconnect-test-flash-failed",
            ),
            (
                {"rollback": {"ok": True, "selftest_ok": False}},
                "v2177-hold-reconnect-rollback-selftest-failed",
            ),
        ]

        for override, decision in cases:
            with self.subTest(decision=decision):
                result = hold.classify(base_manifest(**override))
                self.assertFalse(result["pass"])
                self.assertEqual(result["decision"], decision)

    def test_classify_pass_requires_hold_disconnect_reconnect_cleanup_and_safety(self) -> None:
        passed = hold.classify(base_manifest())
        self.assertTrue(passed["pass"])
        self.assertEqual(passed["decision"], "v2177-hold-reconnect-rollback-pass")

        failing_overrides = [
            {"initial": {"connect": {**clean_connect(), "ok": False}, "dhcp_ping": clean_dhcp()}},
            {"initial": {"connect": clean_connect(), "dhcp_ping": {**clean_dhcp(), "ok": False}}},
            {"hold": {"ok": False}},
            {"disconnect": {"ok": False}},
            {"reconnect": {"connect": {**clean_connect(), "ok": False}, "dhcp_ping": clean_dhcp(), "cleanup": clean_cleanup()}},
            {"reconnect": {"connect": clean_connect(), "dhcp_ping": {**clean_dhcp(), "ok": False}, "cleanup": clean_cleanup()}},
            {"reconnect": {"connect": clean_connect(), "dhcp_ping": clean_dhcp(), "cleanup": {"ok": False}}},
            {"initial": {"connect": {**clean_connect(), "secret_values_logged": "1"}, "dhcp_ping": clean_dhcp()}},
            {"reconnect": {"connect": clean_connect(), "dhcp_ping": {**clean_dhcp(), "credentials_logged": "1"}, "cleanup": clean_cleanup()}},
        ]

        for override in failing_overrides:
            with self.subTest(override=override):
                result = hold.classify(base_manifest(**override))
                self.assertFalse(result["pass"])
                self.assertEqual(result["decision"], "v2177-hold-reconnect-failed-rollback-pass")

    def test_run_ping_step_quotes_target_and_parses_redacted_fields(self) -> None:
        steps = []

        def fake_serial_step(store, step_list, name, command, **kwargs):
            step_list.append({"name": name, "command": command})
            return {"ok": True}

        with (
            mock.patch.object(hold, "serial_step", side_effect=fake_serial_step),
            mock.patch.object(hold.v2174, "step_stdout", return_value="external_ping_rc=0\nexternal_ping_output.bytes_from=1\n"),
            mock.patch.object(hold.v2174, "redact_wifi_evidence", side_effect=lambda text: text),
        ):
            fields = hold.run_ping_step(object(), steps, name="hold-ping", target="bad target; reboot")

        self.assertEqual(fields["command_ok"], "1")
        self.assertEqual(fields["external_ping_rc"], "0")
        self.assertEqual(fields["external_ping_output.bytes_from"], "1")
        script = steps[0]["command"][4]
        self.assertIn("'bad target; reboot'", script)

    def test_run_dhcp_ping_no_cleanup_skips_ping_on_dhcp_failure_and_samples_residual(self) -> None:
        steps = []

        def fake_serial_step(store, step_list, name, command, **kwargs):
            step_list.append({"name": name, "command": command})
            return {"ok": True}

        def fake_step_fields(store, step_list, name):
            if name == "initial-wifi-dhcp":
                return {
                    "decision": "wifi-dhcp-failed",
                    "dhcp_rc": "1",
                    "secret_values_logged": "0",
                    "credentials_logged": "0",
                }
            return {}

        with (
            mock.patch.object(hold, "serial_step", side_effect=fake_serial_step),
            mock.patch.object(hold, "step_fields", side_effect=fake_step_fields),
            mock.patch.object(hold, "run_ping_step") as run_ping_step,
        ):
            result = hold.run_dhcp_ping_no_cleanup(
                object(),
                steps,
                prefix="initial",
                profile_name="profile",
                ping_target="example.test",
            )

        run_ping_step.assert_not_called()
        self.assertFalse(result["ok"])
        self.assertEqual(result["dhcp_decision"], "wifi-dhcp-failed")
        self.assertEqual(result["external_ping_rc"], "")
        self.assertIn("initial-residual-before-cleanup", [step["name"] for step in steps])

    def test_run_dhcp_ping_no_cleanup_runs_ping_after_dhcp_pass(self) -> None:
        steps = []

        def fake_serial_step(store, step_list, name, command, **kwargs):
            step_list.append({"name": name, "command": command})
            return {"ok": True}

        def fake_step_fields(store, step_list, name):
            if name == "reconnect-wifi-dhcp":
                return {
                    "decision": "wifi-dhcp-pass",
                    "dhcp_rc": "0",
                    "ipv4_assigned": "1",
                    "route_default_present": "1",
                    "resolv_conf.present": "1",
                    "resolv_conf.nameserver_count": "2",
                    "secret_values_logged": "0",
                    "credentials_logged": "0",
                }
            return {}

        with (
            mock.patch.object(hold, "serial_step", side_effect=fake_serial_step),
            mock.patch.object(hold, "step_fields", side_effect=fake_step_fields),
            mock.patch.object(
                hold,
                "run_ping_step",
                return_value={"external_ping_rc": "0", "external_ping_output.bytes_from": "1", "external_ping_output.bad_address": "0"},
            ) as run_ping_step,
        ):
            result = hold.run_dhcp_ping_no_cleanup(
                object(),
                steps,
                prefix="reconnect",
                profile_name=None,
                ping_target="example.test",
            )

        run_ping_step.assert_called_once()
        self.assertTrue(result["ok"])
        self.assertEqual(result["dhcp_decision"], "wifi-dhcp-pass")
        self.assertEqual(result["external_ping_bytes_from"], "1")

    def test_run_cleanup_check_requires_done_decision_and_no_residual_files(self) -> None:
        steps = []

        def fake_serial_step(store, step_list, name, command, **kwargs):
            step_list.append({"name": name, "command": command})
            return {"ok": True}

        def fake_step_fields_clean(store, step_list, name):
            if name == "final-wifi-cleanup":
                return {"decision": "wifi-cleanup-done"}
            if name == "final-residual-after-cleanup":
                return {
                    "supplicant_count": "0",
                    "udhcpc_pidfile": "0",
                    "resolv_conf": "0",
                    "carrier": "0",
                    "route_default_present": "0",
                }
            return {}

        with (
            mock.patch.object(hold, "serial_step", side_effect=fake_serial_step),
            mock.patch.object(hold, "step_fields", side_effect=fake_step_fields_clean),
        ):
            clean = hold.run_cleanup_check(object(), steps, prefix="final")

        self.assertTrue(clean["ok"])
        self.assertTrue(clean["residue_clean"])
        self.assertEqual(clean["cleanup_decision"], "wifi-cleanup-done")

        with (
            mock.patch.object(hold, "serial_step", side_effect=fake_serial_step),
            mock.patch.object(
                hold,
                "step_fields",
                side_effect=lambda store, step_list, name: {"decision": "wifi-cleanup-done"} if name.endswith("wifi-cleanup") else {
                    "supplicant_count": "1",
                    "udhcpc_pidfile": "0",
                    "resolv_conf": "0",
                },
            ),
        ):
            dirty = hold.run_cleanup_check(object(), [], prefix="final")

        self.assertFalse(dirty["ok"])
        self.assertFalse(dirty["residue_clean"])
        self.assertEqual(dirty["supplicant_count"], "1")

    def test_run_hold_idle_samples_until_window_then_runs_final_ping(self) -> None:
        steps = []

        def fake_serial_step(store, step_list, name, command, **kwargs):
            step_list.append({"name": name, "command": command})
            return {"ok": True}

        def fake_step_fields(store, step_list, name):
            return {
                "carrier": "1",
                "operstate": "up",
                "route_default_present": "1",
                "resolv_conf": "1",
                "supplicant_count": "1",
                "udhcpc_pidfile": "1",
            }

        with (
            mock.patch.object(hold.time, "monotonic", side_effect=[0.0, 0.0, 1.0, 2.0]),
            mock.patch.object(hold.time, "sleep") as sleep,
            mock.patch.object(hold, "serial_step", side_effect=fake_serial_step),
            mock.patch.object(hold, "step_fields", side_effect=fake_step_fields),
            mock.patch.object(hold, "run_ping_step", return_value={"external_ping_rc": "0", "external_ping_output.bytes_from": "1"}),
        ):
            result = hold.run_hold_idle(object(), steps, hold_sec=2, interval_sec=1, ping_target="example.test")

        self.assertTrue(result["ok"])
        self.assertEqual(result["samples"], 2)
        self.assertEqual(result["carrier_values"], ["1", "1"])
        self.assertEqual(result["route_values"], ["1", "1"])
        self.assertEqual(result["final_ping_rc"], "0")
        self.assertEqual(sleep.call_count, 2)

    def test_render_report_records_hold_scope_and_redaction_statement(self) -> None:
        manifest = base_manifest(
            classification={
                "decision": "v2177-hold-reconnect-rollback-pass",
                "pass": True,
                "reason": "ok",
            },
            phase_timers=[{"name": "hold_idle_window", "elapsed_sec": 180.0}],
        )

        report = hold.render_report(manifest)

        self.assertIn("# Native Init V2177 Wi-Fi Hold Reconnect Live Validation", report)
        self.assertIn("- Decision: `v2177-hold-reconnect-rollback-pass`", report)
        self.assertIn("Raw SSID, PSK, BSSID, MAC, assigned IP, route, DNS, DHCP lease", report)
        self.assertIn("- Hold window: `180` sec; samples `2`; sample OK `True`", report)
        self.assertIn("- `hold_idle_window`: `180.0` sec", report)
        self.assertIn("- Rollback selftest fail=0: `True`", report)


if __name__ == "__main__":
    unittest.main()
