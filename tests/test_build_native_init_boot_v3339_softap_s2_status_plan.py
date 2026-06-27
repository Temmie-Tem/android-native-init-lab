from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
WIFI_C = ROOT / "workspace/public/src/native-init/a90_wifi.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3339_softap_s2_status_plan.py"
)


class BuildNativeInitBootV3339SoftapS2StatusPlanTests(unittest.TestCase):
    def test_v3339_identity(self) -> None:
        self.assertEqual(runner.CYCLE, "V3339")
        self.assertEqual(runner.INIT_VERSION, "0.11.104")
        self.assertEqual(runner.INIT_BUILD, "v3339-softap-s2-status-plan")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3339_softap_s2_status_plan.img",
        )
        self.assertEqual(runner.BASE_BOOT.name, "boot_linux_v3335_gpu_z3_primary_setcrtc.img")

    def test_required_strings_include_softap_no_start_markers(self) -> None:
        required = b"\n".join(runner.REQUIRED_STRINGS)

        self.assertIn(b"0.11.104", required)
        self.assertIn(b"v3339-softap-s2-status-plan", required)
        self.assertIn(b"a90-native-wifi-softap-v1", required)
        self.assertIn(b"/cache/a90-softap", required)
        self.assertIn(b"wifi softap [status|plan|prepare [profile]|cleanup]", required)
        self.assertIn(b"softap-status-blocked-wlan-gate", required)
        self.assertIn(b"softap-prepare-blocked-wlan-gate", required)
        self.assertIn(b"hostapd_start_attempted=0", required)
        self.assertIn(b"dhcp_server_start_attempted=0", required)
        self.assertIn(b"listener_start_attempted=0", required)
        self.assertIn(b"server_exposure_attempted=0", required)
        self.assertIn(b"start_allowed=0", required)

    def test_softap_manifest_is_no_start_contract(self) -> None:
        manifest = runner._softap_manifest()

        self.assertEqual(manifest["rung"], "S2")
        self.assertEqual(manifest["scope"], "softap-status-plan-prepare-no-start")
        self.assertEqual(
            manifest["commands"],
            ["wifi softap status", "wifi softap plan", "wifi softap prepare"],
        )
        self.assertIn("softap-prepare-blocked-wlan-gate", manifest["expected_current_decisions"])
        self.assertIn("hostapd_start_attempted=0", manifest["hard_no_start_fields"])
        self.assertIn("start_allowed=0", manifest["hard_no_start_fields"])
        self.assertIn("no-hostapd-ap-mode-listener-start", manifest["pass_requirements"])

    def test_report_describes_flash_candidate_without_ap_start(self) -> None:
        report = runner.render_report(
            {
                "boot_image": str(runner.BOOT_IMAGE),
                "boot_sha256": "0" * 64,
            },
            (),
            (),
        )

        self.assertIn("V3339", report)
        self.assertIn("0.11.104", report)
        self.assertIn("wifi softap status", report)
        self.assertIn("no hostapd start", report)
        self.assertIn("start_allowed=0", report)
        self.assertIn("no scan/connect/DHCP/ping", report)

    def test_current_source_contains_softap_surface(self) -> None:
        source = WIFI_C.read_text(encoding="utf-8")

        self.assertIn("wifi_softap_cmd", source)
        self.assertIn("a90_wififeas_evaluate(&feasibility)", source)
        self.assertIn("hostapd_start_attempted=0", source)
        self.assertIn("start_allowed=0", source)


if __name__ == "__main__":
    unittest.main()
