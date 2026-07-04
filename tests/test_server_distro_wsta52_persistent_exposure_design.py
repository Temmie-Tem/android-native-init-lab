from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


wsta25 = load_script("workspace/public/src/scripts/server-distro/run_wsta25_confirmed_autoconnect_live.py")
wsta43 = load_script("workspace/public/src/scripts/server-distro/run_wsta43_orchestrated_native_uplink_dpublic.py")
DESIGN = Path("docs/operations/A90_WSTA_PERSISTENT_EXPOSURE_DESIGN.md")


class ServerDistroWsta52PersistentExposureDesignTests(unittest.TestCase):
    def test_design_builds_on_proven_wsta_flow(self) -> None:
        text = DESIGN.read_text(encoding="utf-8")

        self.assertIn("WSTA45 operator wrapper", text)
        self.assertIn("WSTA43 orchestrator", text)
        self.assertIn("WSTA28 reboot/materialization scan-green precondition", text)
        self.assertIn("WSTA42 native-owned STA uplink", text)
        self.assertIn("WSTA48 redacted aggregate", text)
        self.assertIn("Native init remains the Wi-Fi owner", text)
        self.assertIn("Debian remains a service surface", text)

    def test_persistent_mode_is_lease_bound_and_default_off(self) -> None:
        text = DESIGN.read_text(encoding="utf-8")

        for marker in (
            "default_state=public-off",
            "default_lease_ttl_sec=1800",
            "maximum_lease_ttl_sec=14400",
            "renewal_requires_host_gate=true",
            "boot_autostart_without_valid_private_lease=false",
            "raw_public_url_committed=false",
            "PUBLIC_RUNNING -> INCIDENT_STOP -> PUBLIC_OFF",
        ):
            self.assertIn(marker, text)

    def test_required_gates_keep_live_public_work_fail_closed(self) -> None:
        text = DESIGN.read_text(encoding="utf-8")

        for marker in (
            "bridge_status_ok=true",
            "selftest_fail_zero=true",
            "wsta45_preflight_pass=true",
            "wsta28_scan_green_recent=true",
            "credentialed_wifi_ack=true",
            "public_exposure_ack=true",
            "native_confirm_token_private=true",
            "public_confirm_token_private=true",
            "lease_ttl_within_cap=true",
            "native_owned_wifi_confirmed=true",
            "default_route_is_wlan=true",
            "resolver_ready=true",
            "loopback_smoke_ready=true",
            "secret_values_logged=0",
            "public_url_value_logged=false",
        ):
            self.assertIn(marker, text)

    def test_cleanup_and_supervision_are_required_before_success(self) -> None:
        text = DESIGN.read_text(encoding="utf-8")

        for marker in (
            "dpublic_cleanup_ok=true",
            "cloudflared_absent=true",
            "smoke_service_absent=true",
            "native_uplink_profile_cleanup_ok=true",
            "helper_cleanup_ok=true",
            "chroot_cleanup_ok=true",
            "wifi_cleanup_ok=true",
            "post_selftest_fail_zero=true",
            "wsta48_redaction_guard_ok=true",
            "duplicate_tunnel_is_failure=true",
            "ttl_expiry_stops_public=true",
            "manual_stop_stops_public=true",
            "cleanup_idempotent=true",
        ):
            self.assertIn(marker, text)

    def test_public_artifacts_remain_redacted(self) -> None:
        text = DESIGN.read_text(encoding="utf-8")
        lowered = text.lower()

        self.assertIn("public_url_storage=workspace/private-only", text)
        self.assertIn("status_redacts_url=true", text)
        self.assertIn("hud_shows_redacted_state_only=true", text)
        self.assertNotIn(wsta25.NATIVE_CONFIRM_TOKEN, text)
        self.assertNotIn(wsta43.PUBLIC_CONFIRM_TOKEN, text)
        self.assertNotIn("trycloudflare.com", lowered)
        self.assertNotIn("ssid=", lowered)
        self.assertNotIn("psk=", lowered)
        self.assertNotIn("http://", lowered)
        self.assertNotIn("https://", lowered)

    def test_rungs_do_not_authorize_flash_or_gate_weakening(self) -> None:
        text = DESIGN.read_text(encoding="utf-8")

        self.assertIn("WSTA53 source", text)
        self.assertIn("WSTA54 host-only", text)
        self.assertIn("WSTA55 live", text)
        self.assertIn("WSTA56 live", text)
        self.assertIn("WSTA57 native HUD", text)
        self.assertIn("No boot flash is part of the persistent exposure start path.", text)
        self.assertIn("No raw partition write is part of the persistent exposure path.", text)
        self.assertIn("No weakening of WSTA42/WSTA43/WSTA45 live gates is allowed.", text)


if __name__ == "__main__":
    unittest.main()
