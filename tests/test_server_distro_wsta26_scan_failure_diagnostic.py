from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta26_scan_failure_diagnostic.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta26_scan_failure_diagnostic.py")


class ServerDistroWsta26ScanFailureDiagnosticTests(unittest.TestCase):
    def test_native_v3387_detector_requires_version_and_build(self) -> None:
        text = "A90 Linux init 0.11.143 (v3387-wifi-uplink-service-redacted)"
        self.assertTrue(runner.native_is_v3387(text))
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.144 (v3388-wifi-autoconnect-scan-recovery)"))
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.145 (v3389-wifi-connect-carrier-diagnostics)"))
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.146 (v3390-wifi-cache-enospc-fallback)"))
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.147 (v3391-wifi-wpa-handshake-diagnostics)"))
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.148 (v3392-wifi-tmp-ctrl-dir)"))
        self.assertTrue(runner.native_is_v3387("A90 Linux init 0.11.149 (v3393-wifi-ctrl-socket-unique)"))
        self.assertFalse(runner.native_is_v3387("A90 Linux init 0.11.143"))

    def test_status_summaries_keep_redacted_operational_fields(self) -> None:
        record = {
            "text": "\n".join((
                "decision=wifi-status-wlan0-present",
                "wlan0_present=1",
                "operstate=down",
                "ipv4=none",
                "default_route_present=0",
                "mac=xx:7f:3a",
                "gateway=none",
                "secret_values_logged=0",
            )),
        }
        summary = runner.status_summary(record)
        self.assertEqual(summary["decision"], "wifi-status-wlan0-present")
        self.assertEqual(summary["operstate"], "down")
        self.assertNotIn("mac", summary)
        self.assertNotIn("gateway", summary)

    def test_classification_splits_scan_ok_and_blocked(self) -> None:
        base = {
            "checks": {
                "native_v3387": True,
                "baseline_selftest_fail_zero": True,
                "final_selftest_fail_zero": True,
                "autoconnect_disabled": True,
            },
        }
        visible = {"checks": {**base["checks"], "direct_scan_engine_ok": True, "direct_scan_has_bss": True}}
        zero = {"checks": {**base["checks"], "direct_scan_engine_ok": True, "direct_scan_has_bss": False}}
        blocked = {"checks": {**base["checks"], "direct_scan_engine_ok": False, "direct_scan_has_bss": False}}
        self.assertEqual(runner.classify(visible), "wsta26-direct-native-scan-visible-after-wsta25-failure")
        self.assertEqual(runner.classify(zero), "wsta26-direct-native-scan-engine-ok-zero-bss")
        self.assertEqual(runner.classify(blocked), "wsta26-direct-native-scan-blocked")

    def test_public_summary_omits_raw_transcripts(self) -> None:
        result = {
            "decision": "wsta26-direct-native-scan-visible-after-wsta25-failure",
            "run_dir": "workspace/private/runs/server-distro/example",
            "checks": {"direct_scan_engine_ok": True},
            "direct_scan_window": {
                "best": {
                    "decision": "wifi-scan-pass",
                    "scan_result_count": 3,
                    "scan_engine_ok": True,
                    "scan_has_bss": True,
                },
                "attempts": [{"text": "raw ssid should not print"}],
            },
        }
        summary = runner.public_summary(result)
        self.assertEqual(summary["direct_scan_best"]["scan_result_count"], 3)
        self.assertNotIn("attempts", summary)

    def test_runner_surface_stays_below_association(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('wsta15.run_scan_attempt(args, "direct_scan_window", attempt)', source)
        self.assertIn('"confirmed_autoconnect": False', source)
        self.assertIn('"wifi_association": False', source)
        self.assertIn('"dhcp": False', source)
        self.assertIn('"public_tunnel": False', source)
        for forbidden in (
            '["wifi", "connect"',
            '["wifi", "dhcp"',
            '["wifi", "ping"',
            "autoconnect-confirmed",
            "cloudflared tunnel",
            "ssid=",
            "psk=",
            "native_init_flash.py",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
