from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta27_materialization_preflight.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta27_materialization_preflight.py")


class ServerDistroWsta27MaterializationPreflightTests(unittest.TestCase):
    def test_default_gate_blocks_live_device_work(self) -> None:
        class Args:
            allow_materialization_live = False

        ok, decision = runner.explicit_live_gate(Args())
        self.assertFalse(ok)
        self.assertEqual(decision, "wsta27-blocked-explicit-materialization-live-allow-required")

    def test_iftype_probe_summary_keeps_operational_fields(self) -> None:
        record = {
            "text": "\n".join((
                "decision=softap-iftype-probe-pass",
                "wlan0_present=1",
                "wlan0_wait_elapsed_ms=1234",
                "link_up_rc=0",
                "link_up_errno=0",
                "ap_iftype_add_rc=0",
                "ap_iftype_cleanup_ok=1",
                "mac=xx:7f:3a",
            )),
        }
        summary = runner.probe_summary(record)
        self.assertEqual(summary["decision"], "softap-iftype-probe-pass")
        self.assertEqual(summary["link_up_errno"], "0")
        self.assertNotIn("mac", summary)

    def test_iftype_probe_ok_requires_cleanup(self) -> None:
        good = {
            "transport_ok": True,
            "text": "decision=softap-iftype-probe-pass\nlink_up_errno=0\nap_iftype_cleanup_ok=1\n",
        }
        dirty = {
            "transport_ok": True,
            "text": "decision=softap-iftype-probe-pass\nlink_up_errno=0\nap_iftype_cleanup_ok=0\n",
        }
        self.assertTrue(runner.iftype_probe_ok(good))
        self.assertFalse(runner.iftype_probe_ok(dirty))

    def test_classification_requires_scan_gate(self) -> None:
        base = {
            "checks": {
                "explicit_live_gate": True,
                "native_v3387": True,
                "baseline_selftest_fail_zero": True,
                "final_selftest_fail_zero": True,
                "autoconnect_disabled": True,
                "iftype_probe_pass": True,
                "admin_up_after_preflight": True,
            },
        }
        pass_case = {"checks": {**base["checks"], "scan_engine_ok": True, "scan_has_bss": True}}
        zero_case = {"checks": {**base["checks"], "scan_engine_ok": True, "scan_has_bss": False}}
        blocked = {"checks": {**base["checks"], "scan_engine_ok": False, "scan_has_bss": False}}
        self.assertEqual(runner.classify(pass_case), "wsta27-materialization-scan-gate-pass")
        self.assertEqual(runner.classify(zero_case), "wsta27-materialization-scan-engine-ok-zero-bss")
        self.assertEqual(runner.classify(blocked), "wsta27-materialization-scan-blocked")

    def test_public_summary_omits_raw_transcripts(self) -> None:
        result = {
            "decision": "wsta27-materialization-scan-gate-pass",
            "run_dir": "workspace/private/runs/server-distro/example",
            "checks": {"scan_engine_ok": True},
            "materialized_scan_window": {
                "best": {"decision": "wifi-scan-pass", "scan_result_count": 4},
                "attempts": [{"text": "raw scan transcript"}],
            },
        }
        summary = runner.public_summary(result)
        self.assertEqual(summary["scan_best"]["scan_result_count"], 4)
        self.assertNotIn("attempts", summary)

    def test_runner_surface_stays_below_connectivity(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        self.assertIn('["wifi", "softap", "iftype-probe", str(args.probe_timeout_ms)]', source)
        self.assertIn("run_scan_window_until_engine", source)
        self.assertIn('"service_connect_request": False', source)
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
