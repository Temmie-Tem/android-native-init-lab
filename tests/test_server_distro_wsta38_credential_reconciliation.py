from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


wsta38 = load_script("workspace/public/src/scripts/server-distro/run_wsta38_auth_material_reconcile.py")


def write_private(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)


class ServerDistroWsta38CredentialReconciliationTests(unittest.TestCase):
    def test_parse_supplicant_metadata_redacts_values(self) -> None:
        parsed = wsta38.parse_supplicant_config(
            'ctrl_interface=/run/wpa_supplicant\n'
            'update_config=0\n'
            'network={\n'
            '  ssid="Secret Net"\n'
            '  scan_ssid=1\n'
            '  key_mgmt=WPA-PSK\n'
            '  psk="secretpass"\n'
            '}\n'
        )
        meta = parsed["metadata"]

        self.assertEqual(meta["ctrl_interface_class"], "run-wpa-supplicant")
        self.assertEqual(meta["ssid_format"], "quoted")
        self.assertEqual(meta["psk_format"], "quoted-passphrase")
        self.assertEqual(meta["ssid_len"], 10)
        self.assertEqual(meta["psk_len"], 10)
        self.assertEqual(meta["secret_values_logged"], 0)
        self.assertNotIn("Secret Net", repr(meta))
        self.assertNotIn("secretpass", repr(meta))

    def test_material_comparison_uses_python_pbkdf2_reference(self) -> None:
        env = {"ssid": "Test Net", "psk": "12345678"}
        psk_hex = wsta38.pbkdf2_psk_hex(env["ssid"], env["psk"])
        self.assertIsNotNone(psk_hex)

        comparison = wsta38.compare_material(
            env,
            {"ssid": "Test Net", "psk": "12345678", "raw": {}},
            {"raw": {"ssid": env["ssid"].encode("utf-8").hex(), "psk": psk_hex}},
            {"raw": {"ssid": "Test Net", "psk": "12345678"}},
        )

        self.assertTrue(comparison["credential_material_consistent"])
        self.assertTrue(comparison["device_psk_secret_matches_env"])
        self.assertTrue(comparison["native_psk_hex_matches_python_reference"])
        self.assertEqual(comparison["secret_values_logged"], 0)
        self.assertNotIn("12345678", repr(comparison))

    def test_run_writes_only_redacted_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = root / "wifi.env"
            run_dir = root / "run"
            write_private(env, "A90_WIFI_SSID='Test Net'\nA90_WIFI_PSK='12345678'\n")
            wsta7 = root / "wsta7.conf"
            write_private(wsta7, wsta38.wsta3.supplicant_text_from_env({"ssid": "Test Net", "psk": "12345678"}))
            psk_hex = wsta38.pbkdf2_psk_hex("Test Net", "12345678")
            native_text = (
                "ctrl_interface=DIR=/tmp/a90-wifi/sockets GROUP=wifi\n"
                "update_config=0\n"
                "ap_scan=1\n"
                "network={\n"
                "  ssid=54657374204e6574\n"
                "  disabled=0\n"
                "  scan_ssid=1\n"
                "  key_mgmt=WPA-PSK\n"
                f"  psk={psk_hex}\n"
                "}\n"
            )
            args = argparse.Namespace(
                run_dir=run_dir,
                run_id=None,
                wifi_env=env,
                wsta7_config=wsta7,
                a90ctl=Path("a90ctl.py"),
                native_conf="/cache/a90-wifi/wpa_supplicant.conf",
                native_autoconnect_conf="/mnt/sdext/a90/config/wifi/autoconnect.conf",
                native_profile_root="/mnt/sdext/a90/config/wifi/profiles",
                timeout=1.0,
                read_native=True,
            )

            with mock.patch.object(wsta38, "run_a90ctl_cat", return_value={
                "payload": native_text,
                "metadata": {
                    "payload_present": True,
                    "end_rc": 0,
                    "returncode": 0,
                    "secret_values_logged": 0,
                },
            }), mock.patch.object(wsta38, "read_device_profile_material", return_value={
                "raw": {"ssid": "Test Net", "psk": "12345678"},
                "metadata": {
                    "ssid_secret_read": {"payload_present": True, "secret_len": 8, "secret_values_logged": 0},
                    "psk_secret_read": {"payload_present": True, "secret_len": 8, "secret_values_logged": 0},
                    "secret_values_logged": 0,
                },
            }):
                result = wsta38.run(args)

            text = (run_dir / "wsta38_result.json").read_text(encoding="utf-8")

        self.assertEqual(result["decision"], wsta38.PASS_DECISION)
        self.assertTrue(result["comparison"]["credential_material_consistent"])
        self.assertNotIn("Test Net", text)
        self.assertNotIn("12345678", text)
        self.assertNotIn(str(psk_hex), text)
        self.assertIn('"secret_values_logged": 0', text)

    def test_stale_device_psk_is_classified_before_native_pbkdf2(self) -> None:
        env = {"ssid": "Test Net", "psk": "12345678"}
        stale_psk = "87654321"
        stale_hex = wsta38.pbkdf2_psk_hex(env["ssid"], stale_psk)

        comparison = wsta38.compare_material(
            env,
            {"ssid": "Test Net", "psk": "12345678", "raw": {}},
            {"raw": {"ssid": env["ssid"].encode("utf-8").hex(), "psk": stale_hex}},
            {"raw": {"ssid": "Test Net", "psk": stale_psk}},
        )
        result = {
            "wifi_env": {"ok": True},
            "wsta7_config": {"present": True},
            "native_config_read": {"payload_present": True},
            "device_profile": {
                "ssid_secret_read": {"payload_present": True},
                "psk_secret_read": {"payload_present": True},
            },
            "comparison": comparison,
        }

        self.assertFalse(comparison["device_psk_secret_matches_env"])
        self.assertTrue(comparison["native_psk_hex_matches_device_secret_reference"])
        self.assertEqual(wsta38.classify(result), "wsta38-device-psk-secret-mismatch")

    def test_device_profile_paths_are_redacted(self) -> None:
        self.assertEqual(
            wsta38.redact_device_path_arg("/mnt/sdext/a90/config/wifi/profiles/private-profile.conf"),
            "/mnt/sdext/a90/config/wifi/profiles/<profile>.conf",
        )
        self.assertEqual(
            wsta38.redact_device_path_arg("/mnt/sdext/a90/secrets/wifi/private-profile.psk"),
            "/mnt/sdext/a90/secrets/wifi/<profile>.psk",
        )
        self.assertEqual(
            wsta38.redact_device_path_arg("/mnt/sdext/a90/secrets/wifi/private-profile.ssid"),
            "/mnt/sdext/a90/secrets/wifi/<profile>.ssid",
        )
        self.assertEqual(
            wsta38.redact_device_path_arg("/cache/a90-wifi/wpa_supplicant.conf"),
            "/cache/a90-wifi/wpa_supplicant.conf",
        )


if __name__ == "__main__":
    unittest.main()
