"""Regression tests for native_wifi_v2254_hold_reconnect_handoff_v2282."""

import unittest
from pathlib import Path
from unittest import mock

from _loader import load_revalidation

v2282 = load_revalidation("native_wifi_v2254_hold_reconnect_handoff_v2282")


def good_step(**extra):
    data = {"ok": True, "secret_values_logged": "0", "credentials_logged": "0"}
    data.update(extra)
    return data


def live_manifest(**overrides):
    manifest = {
        "execute": True,
        "preflight": {"wifi_secret_status": {"valid": True}},
        "transport_selection": {"status_ok": True},
        "current_preflight": {"selftest_ok": True},
        "test_flash_ok": True,
        "rollback": {"ok": True, "selftest_ok": True, "attempt": "from-native"},
        "initial": {
            "connect": good_step(decision="wifi-connect-ok", carrier_up="1", wpa_state="COMPLETED"),
            "dhcp_ping": good_step(dhcp_decision="dhcp-ok", external_ping_rc="0"),
        },
        "hold": {"ok": True, "hold_sec": 180, "samples": 6, "sample_ok": True, "final_ping_rc": "0"},
        "disconnect": {"ok": True, "cleanup_decision": "wifi-cleanup-ok", "residue_clean": True},
        "reconnect": {
            "connect": good_step(decision="wifi-connect-ok", carrier_up="1", wpa_state="COMPLETED"),
            "dhcp_ping": good_step(dhcp_decision="dhcp-ok", external_ping_rc="0"),
            "cleanup": good_step(cleanup_decision="wifi-cleanup-ok", residue_clean=True),
        },
    }
    manifest.update(overrides)
    return manifest


class PreflightAndCommandHelpers(unittest.TestCase):
    def test_preflight_redacts_credentials_and_checks_expected_images(self):
        fake_sha = {
            v2282.TEST_IMAGE: v2282.TEST_EXPECT_SHA256,
            v2282.ROLLBACK_IMAGE: v2282.ROLLBACK_EXPECT_SHA256,
            v2282.FALLBACK_IMAGE: v2282.FALLBACK_EXPECT_SHA256,
        }

        with mock.patch.object(v2282.v2174, "load_wifi_env", return_value=[{"path": "/private/env", "present": True}]), \
             mock.patch.object(v2282.v2174, "wifi_secret_status", return_value={
                 "profile": "unit", "ssid_present": True, "psk_present": True, "valid": True, "secret_values_logged": 0,
             }), \
             mock.patch.object(v2282.Path, "exists", return_value=True), \
             mock.patch.object(v2282, "sha256", side_effect=lambda path: fake_sha[path]):
            pre = v2282.preflight("unit", "9.9.9.9", 60, 15)

        self.assertTrue(pre["test_image_sha_matches_expected"])
        self.assertTrue(pre["rollback_image_sha_matches_expected"])
        self.assertTrue(pre["fallback_image_sha_matches_expected"])
        self.assertEqual(pre["profile"], "unit")
        self.assertFalse(pre["credential_values_logged"])
        self.assertEqual(pre["ping_target"], "9.9.9.9")

    def test_dry_run_commands_include_scoped_flash_wifi_and_rollback_steps(self):
        plan = v2282.dry_run_commands()

        self.assertIn("--from-native", plan["flash_v2254"])
        self.assertIn(v2282.TEST_EXPECT_SHA256, plan["flash_v2254"])
        self.assertEqual(plan["connect"], ["a90ctl", "wifi", "connect", "<profile>"])
        self.assertEqual(plan["dhcp"], ["a90ctl", "wifi", "dhcp", "<profile>"])
        self.assertEqual(plan["cleanup"], ["a90ctl", "wifi", "cleanup"])
        self.assertIn(v2282.ROLLBACK_EXPECT_SHA256, plan["rollback_v2237"])


class ManifestClassification(unittest.TestCase):
    def test_classify_covers_dry_run_ready_and_image_blocked(self):
        ready_preflight = {
            "test_image_exists": True,
            "test_image_sha_matches_expected": True,
            "rollback_image_exists": True,
            "rollback_image_sha_matches_expected": True,
            "fallback_image_exists": True,
            "fallback_image_sha_matches_expected": True,
        }
        ready = v2282.classify({"execute": False, "preflight": ready_preflight})
        blocked = v2282.classify({"execute": False, "preflight": {**ready_preflight, "fallback_image_sha_matches_expected": False}})

        self.assertEqual(ready["decision"], "v2282-v2254-hold-reconnect-dry-run-ready")
        self.assertTrue(ready["pass"])
        self.assertEqual(blocked["decision"], "v2282-v2254-hold-reconnect-dry-run-blocked")
        self.assertFalse(blocked["pass"])

    def test_classify_covers_live_pre_flash_gates(self):
        cases = [
            ({"execute": True, "confirm_missing": True}, "v2282-v2254-hold-reconnect-confirmation-missing"),
            ({"execute": True, "preflight": {"wifi_secret_status": {"valid": False}}}, "v2282-v2254-hold-reconnect-wifi-env-missing-no-flash"),
            (live_manifest(transport_selection={"status_ok": False}), "v2282-v2254-hold-reconnect-native-unavailable-no-flash"),
            (live_manifest(current_preflight={"selftest_ok": False}), "v2282-v2254-hold-reconnect-current-selftest-failed-no-flash"),
        ]

        for manifest, decision in cases:
            with self.subTest(decision=decision):
                classified = v2282.classify(manifest)
                self.assertEqual(classified["decision"], decision)
                self.assertFalse(classified["pass"])

    def test_classify_covers_flash_rollback_success_and_failure_branches(self):
        flash_failed = live_manifest(test_flash_ok=False, rollback={"selftest_ok": True})
        rollback_failed = live_manifest(rollback={"ok": False, "selftest_ok": False})
        success = live_manifest()
        safety_failed = live_manifest(initial={
            "connect": good_step(decision="wifi-connect-ok", carrier_up="1", wpa_state="COMPLETED", secret_values_logged="1"),
            "dhcp_ping": good_step(dhcp_decision="dhcp-ok", external_ping_rc="0"),
        })

        self.assertEqual(v2282.classify(flash_failed)["decision"], "v2282-v2254-hold-reconnect-test-flash-failed-rollback-pass")
        self.assertEqual(v2282.classify(rollback_failed)["decision"], "v2282-v2254-hold-reconnect-rollback-selftest-failed")
        self.assertEqual(v2282.classify(success)["decision"], "v2282-v2254-hold-reconnect-rollback-pass")
        self.assertTrue(v2282.classify(success)["pass"])
        self.assertEqual(v2282.classify(safety_failed)["decision"], "v2282-v2254-hold-reconnect-failed-rollback-pass")
        self.assertFalse(v2282.classify(safety_failed)["pass"])


class RedactionAndReportRendering(unittest.TestCase):
    def test_redacted_secret_status_and_env_load_preserve_presence_not_values(self):
        status = v2282.redacted_secret_status({
            "profile": "unit", "ssid_present": True, "psk_present": True, "valid": True,
            "ssid": "raw-ssid", "psk": "raw-psk", "secret_values_logged": 0,
        })
        env = v2282.redacted_env_load([{
            "path": str(v2282.REPO_ROOT / "workspace/private/secrets/wifi.env"),
            "present": True,
            "loaded_keys": ["A90_WIFI_SSID", "A90_WIFI_PSK"],
            "A90_WIFI_PSK": "raw-psk",
        }])

        self.assertEqual(status, {
            "profile": "unit",
            "ssid_present": True,
            "psk_present": True,
            "valid": True,
            "secret_values_logged": 0,
        })
        self.assertEqual(env[0]["path"], "workspace/private/secrets/wifi.env")
        self.assertEqual(env[0]["loaded_keys"], ["A90_WIFI_SSID", "A90_WIFI_PSK"])
        self.assertNotIn("raw-psk", str(status) + str(env))

    def manifest(self, *, execute=False, classification=None):
        manifest = live_manifest()
        manifest.update({
            "classification": classification or {"decision": "v2282-v2254-hold-reconnect-dry-run-ready", "pass": True, "reason": "ready"},
            "execute": execute,
            "out_dir": "workspace/private/runs/wifi/unit",
            "preflight": {
                "test_image": "workspace/private/inputs/boot_images/test.img",
                "test_image_sha256": "test-sha",
                "test_expect_version": v2282.TEST_EXPECT_VERSION,
                "rollback_image": "workspace/private/inputs/boot_images/rollback.img",
                "rollback_image_sha256": "rollback-sha",
                "rollback_expect_version": v2282.ROLLBACK_EXPECT_VERSION,
                "fallback_image_exists": True,
                "fallback_image_sha_matches_expected": True,
                "wifi_secret_status": {"profile": "unit", "ssid_present": True, "psk_present": True, "valid": True, "secret_values_logged": 0},
                "env_load": [{"path": str(v2282.REPO_ROOT / "workspace/private/secrets/wifi.env"), "present": True, "loaded_keys": ["A90_WIFI_SSID"]}],
            },
            "dry_run_commands": {"connect": ["a90ctl", "wifi", "connect", "<profile>"]},
            "phase_timers": [{"name": "host_preflight", "elapsed_sec": 0.1}],
            "test_health": {"version_ok": True, "status_ok": True, "selftest_ok": True},
        })
        return manifest

    def test_render_report_dry_run_records_gate_and_redacts_raw_network_values(self):
        report = v2282.render_report(self.manifest())

        self.assertIn("# Native Init V2282 V2254 Wi-Fi Hold Reconnect Runner", report)
        self.assertIn("Credential Gate", report)
        self.assertIn("Dry-Run Plan", report)
        self.assertIn('"connect"', report)
        self.assertIn("Live mode exits before flash if Wi-Fi credentials are absent", report)
        self.assertNotIn("raw-psk", report)
        self.assertNotIn("raw-ssid", report)

    def test_render_report_live_records_hold_reconnect_and_rollback_scope(self):
        report = v2282.render_report(self.manifest(
            execute=True,
            classification={"decision": "v2282-v2254-hold-reconnect-rollback-pass", "pass": True, "reason": "ok"},
        ))

        self.assertIn("Live Evidence", report)
        self.assertIn("Hold window", report)
        self.assertIn("Reconnect DHCP", report)
        self.assertIn("Rollback OK: `True`", report)
        self.assertIn("No Wi-Fi scan is run by this runner", report)


if __name__ == "__main__":
    unittest.main()
