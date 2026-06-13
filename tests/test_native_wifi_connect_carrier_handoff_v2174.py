from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_revalidation


connect = load_revalidation("native_wifi_connect_carrier_handoff_v2174.py")


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
        "wifi_secret_status": {
            "valid": True,
            "ssid_present": True,
            "psk_present": True,
        },
        "bridge_status": {"bridge_probe": "ok", "serial_candidates": [{"path": "/dev/ttyUSB0"}]},
        "transport_selection": {
            "selected": "tcpctl",
            "fallback_reason": "",
            "selector_contract": "v1",
        },
        "bridge_ready_for_a90ctl": True,
        "pre_native_ok": True,
        "test_flash_ok": True,
        "rollback": {"ok": True, "attempt": "from-native", "selftest_ok": True},
        "connect": {
            "ok": True,
            "decision": "wifi-connect-carrier-up",
            "carrier_up": "1",
            "secret_values_logged": "0",
            "credentials_logged": "0",
            "dhcp_routing": "0",
            "external_ping": "0",
            "wpa_state": "COMPLETED",
            "key_mgmt": "WPA2-PSK",
            "freq": "2412",
            "supplicant_log": {"ok": True, "redacted_log_file": "logs/wpa.log"},
        },
        "phase_timers": [],
        "out_dir": "workspace/private/runs/wifi/example",
    }
    manifest.update(overrides)
    return manifest


class PureHelpers(unittest.TestCase):
    def test_profile_name_validation_and_selection(self) -> None:
        for name in ("default", "temmie2.4G", "profile_1", "a-b.c"):
            with self.subTest(name=name):
                self.assertTrue(connect.profile_name_valid(name))

        for name in ("", "bad/name", "bad name", "x" * 96):
            with self.subTest(name=name):
                self.assertFalse(connect.profile_name_valid(name))

        with mock.patch.dict(connect.os.environ, {}, clear=True):
            self.assertEqual(connect.selected_profile_name(None), "default")
        with mock.patch.dict(connect.os.environ, {"A90_WIFI_PROFILE": "env.profile"}, clear=True):
            self.assertEqual(connect.selected_profile_name(None), "env.profile")
            self.assertEqual(connect.selected_profile_name("explicit"), "explicit")
        with mock.patch.dict(connect.os.environ, {"A90_WIFI_PROFILE": "bad/name"}, clear=True):
            with self.assertRaises(ValueError):
                connect.selected_profile_name(None)

    def test_load_local_env_file_accepts_safe_exports_and_ignores_unknown_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / "wifi.env"
            env_path.write_text(
                "\n".join([
                    "# comment",
                    "export A90_WIFI_SSID='ssid value'",
                    "A90_WIFI_PSK=12345678",
                    "A90_WIFI_PROFILE=lab-profile",
                    "UNRELATED=ignored",
                ]),
                encoding="utf-8",
            )
            env_path.chmod(0o600)

            with mock.patch.dict(connect.os.environ, {"A90_WIFI_PSK": "existing-secret"}, clear=True):
                result = connect.load_local_env_file(env_path)
                self.assertEqual(result["loaded_keys"], ["A90_WIFI_SSID", "A90_WIFI_PROFILE"])
                self.assertEqual(connect.os.environ["A90_WIFI_SSID"], "ssid value")
                self.assertEqual(connect.os.environ["A90_WIFI_PSK"], "existing-secret")
                self.assertEqual(connect.os.environ["A90_WIFI_PROFILE"], "lab-profile")

        missing = connect.load_local_env_file(Path("/tmp/a90-no-such-env-file"))
        self.assertFalse(missing["present"])
        self.assertEqual(missing["loaded_keys"], [])

    def test_load_local_env_file_rejects_unsafe_mode_and_bad_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / "wifi.env"
            env_path.write_text("A90_WIFI_SSID=x\n", encoding="utf-8")
            env_path.chmod(0o644)
            with self.assertRaisesRegex(ValueError, "must not be group/world readable"):
                connect.load_local_env_file(env_path)

            env_path.chmod(0o600)
            env_path.write_text("export A90_WIFI_SSID value\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "expected KEY=value"):
                connect.load_local_env_file(env_path)

    def test_wifi_secret_status_exposes_lengths_only_and_validates_bounds(self) -> None:
        with mock.patch.dict(connect.os.environ, {"A90_WIFI_SSID": "temmie", "A90_WIFI_PSK": "12345678"}, clear=True):
            status = connect.wifi_secret_status("lab")
        self.assertEqual(status["profile"], "lab")
        self.assertEqual(status["ssid_len"], 6)
        self.assertEqual(status["psk_len"], 8)
        self.assertTrue(status["valid"])
        self.assertEqual(status["secret_values_logged"], 0)

        invalid_cases = [
            {"A90_WIFI_SSID": "", "A90_WIFI_PSK": "12345678"},
            {"A90_WIFI_SSID": "x" * 33, "A90_WIFI_PSK": "12345678"},
            {"A90_WIFI_SSID": "temmie", "A90_WIFI_PSK": "short"},
            {"A90_WIFI_SSID": "temmie", "A90_WIFI_PSK": "x" * 64},
        ]
        for env in invalid_cases:
            with self.subTest(env=env), mock.patch.dict(connect.os.environ, env, clear=True):
                self.assertFalse(connect.wifi_secret_status(None)["valid"])

    def test_redaction_masks_secret_values_hex_mac_ipv4_and_tcpctl_token(self) -> None:
        token = "tcpctl_token=0123456789abcdef0123456789abcdef"
        secret_text = "ssidsecret psksecret 70736b736563726574 192.168.7.2 aa:bb:cc:dd:ee:ff " + token
        with mock.patch.dict(connect.os.environ, {"A90_WIFI_SSID": "ssidsecret", "A90_WIFI_PSK": "psksecret"}, clear=True):
            redacted = connect.redact_wifi_evidence(secret_text)
            self.assertTrue(connect.redaction_leaked_secret(secret_text))
            self.assertFalse(connect.redaction_leaked_secret(redacted))

        self.assertNotIn("ssidsecret", redacted)
        self.assertNotIn("psksecret", redacted)
        self.assertNotIn("70736b736563726574", redacted)
        self.assertIn("<redacted:a90_wifi_ssid>", redacted)
        self.assertIn("<redacted:a90_wifi_psk_hex>", redacted)
        self.assertIn("<ipv4>", redacted)
        self.assertIn("<mac>", redacted)
        self.assertIn("tcpctl_token=<redacted>", redacted)

    def test_parse_key_values_and_step_stdout_helpers(self) -> None:
        parsed = connect.parse_key_values("alpha=1\n[noise]\n beta = two=2 \nno-equals\n")
        self.assertEqual(parsed, {"alpha": "1", "beta": "two=2"})
        self.assertEqual(connect.redacted_connect_command("profile"), ["wifi", "connect", "profile"])
        self.assertEqual(connect.redacted_connect_command(None), ["wifi", "connect"])

        with tempfile.TemporaryDirectory() as temp_dir:
            run_dir = Path(temp_dir)
            (run_dir / "stdout.txt").write_text("hello\n", encoding="utf-8")
            store = type("Store", (), {"run_dir": run_dir})()
            steps = [{"name": "old"}, {"name": "target", "stdout_file": "stdout.txt"}]

            self.assertIs(connect.find_step(steps, "target"), steps[1])
            self.assertEqual(connect.step_stdout(store, steps[1]), "hello\n")
            self.assertEqual(connect.step_stdout(store, {"stdout_file": "missing.txt"}), "")
            self.assertIsNone(connect.find_step(steps, "missing"))

    def test_classify_prioritizes_preflight_flash_rollback_and_connect_safety(self) -> None:
        cases = [
            (
                {"preflight": {"test_image_exists": False, "rollback_image_exists": True}},
                "v2174-connect-preflight-image-missing",
            ),
            (
                {"wifi_secret_status": {"valid": False, "ssid_present": True, "psk_present": False}},
                "v2174-connect-preflight-wifi-env-missing-no-flash",
            ),
            (
                {"pre_native_ok": False, "bridge_status": {"bridge_probe": "down", "serial_candidates": []}},
                "v2174-connect-preflight-bridge-or-native-unavailable-no-flash",
            ),
            (
                {"test_flash_ok": False},
                "v2174-connect-test-flash-failed",
            ),
            (
                {"rollback": {"ok": True, "selftest_ok": False}},
                "v2174-connect-rollback-selftest-failed",
            ),
        ]

        for override, decision in cases:
            with self.subTest(decision=decision):
                result = connect.classify(base_manifest(**override))
                self.assertFalse(result["pass"])
                self.assertEqual(result["decision"], decision)

        passed = connect.classify(base_manifest())
        self.assertTrue(passed["pass"])
        self.assertEqual(passed["decision"], "v2174-connect-carrier-up-rollback-pass")

        for unsafe_connect in (
            {"ok": False, "secret_values_logged": "0", "credentials_logged": "0", "dhcp_routing": "0", "external_ping": "0"},
            {"ok": True, "secret_values_logged": "1", "credentials_logged": "0", "dhcp_routing": "0", "external_ping": "0"},
            {"ok": True, "secret_values_logged": "0", "credentials_logged": "0", "dhcp_routing": "1", "external_ping": "0"},
            {"ok": True, "secret_values_logged": "0", "credentials_logged": "0", "dhcp_routing": "0", "external_ping": "1"},
        ):
            with self.subTest(connect=unsafe_connect):
                result = connect.classify(base_manifest(connect=unsafe_connect))
                self.assertFalse(result["pass"])
                self.assertEqual(result["decision"], "v2174-connect-no-carrier-or-safety-mismatch-rollback-pass")

    def test_render_report_records_connect_scope_without_raw_private_values(self) -> None:
        manifest = base_manifest(
            classification={
                "decision": "v2174-connect-carrier-up-rollback-pass",
                "pass": True,
                "reason": "ok",
            },
            phase_timers=[{"name": "connect_window", "elapsed_sec": 3.5}],
        )

        report = connect.render_report(manifest)

        self.assertIn("# Native Init V2174 Wi-Fi Urandom Connect Live Validation", report)
        self.assertIn("- Decision: `v2174-connect-carrier-up-rollback-pass`", report)
        self.assertIn("Explicitly excluded: DHCP, route installation, DNS, external ping", report)
        self.assertIn("- Secret values logged: `0`", report)
        self.assertIn("- `connect_window`: `3.5` sec", report)
        self.assertIn("- Rollback selftest fail=0: `True`", report)


if __name__ == "__main__":
    unittest.main()
