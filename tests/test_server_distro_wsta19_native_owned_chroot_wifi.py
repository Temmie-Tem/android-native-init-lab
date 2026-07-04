from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


runner = load_script("workspace/public/src/scripts/server-distro/run_wsta19_native_owned_chroot_wifi.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/run_wsta19_native_owned_chroot_wifi.py")


class ServerDistroWsta19NativeOwnedChrootWifiTests(unittest.TestCase):
    def test_classify_requires_pre_scan_ssh_during_scan_cleanup_and_health(self) -> None:
        base = {
            "checks": {
                "native_v3384": True,
                "baseline_selftest_fail_zero": True,
                "final_selftest_fail_zero": True,
                "pre_scan_has_bss": True,
                "debian_ssh_marker": True,
                "during_scan_has_bss": True,
                "cleanup_ok": True,
            }
        }

        self.assertEqual(runner.classify(base), "wsta19-native-owned-chroot-wifi-boundary-pass")

        for key, decision in (
            ("pre_scan_has_bss", "wsta19-blocked-native-pre-scan"),
            ("debian_ssh_marker", "wsta19-blocked-debian-chroot-ssh"),
            ("during_scan_has_bss", "wsta19-blocked-native-scan-under-chroot"),
            ("cleanup_ok", "wsta19-blocked-cleanup"),
        ):
            variant = {"checks": {**base["checks"], key: False}}
            self.assertEqual(runner.classify(variant), decision)

    def test_runner_surface_is_native_owned_chroot_not_switchroot_or_public_tunnel(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn("d2.d2_mount_script", source)
        self.assertIn("d2.d2_start_dropbear_script", source)
        self.assertIn("run_materialization_preflight", source)
        self.assertIn('["wifi", "softap", "iftype-probe"', source)
        self.assertIn("native_pre_chroot_scan_window", source)
        self.assertIn("native_during_chroot_scan_window", source)
        self.assertIn('"materialization_admin_up"', source)
        self.assertIn('"switch_root": False', source)
        self.assertIn('"no_wifi_association": True', source)
        self.assertIn('"no_public_tunnel": True', source)
        self.assertNotIn("switch-root-to-distro", source)
        self.assertNotIn("userdata-appliance", source)
        self.assertNotIn("native_init_flash.py", source)
        self.assertNotIn("cloudflared tunnel", source)

        for forbidden_command in (
            '["wifi", "connect"',
            '["wifi", "dhcp"',
            '["wifi", "ping"',
            "ssid=",
            "psk=",
        ):
            self.assertNotIn(forbidden_command, source)


if __name__ == "__main__":
    unittest.main()
