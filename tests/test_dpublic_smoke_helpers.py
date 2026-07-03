"""Static checks for the D-public smoke helper sources."""

from __future__ import annotations

import unittest
from pathlib import Path


SMOKE_HTTPD = Path("workspace/public/src/scripts/server-distro/a90_dpublic_smoke_httpd.c")
HTTP_GET = Path("workspace/public/src/scripts/server-distro/a90_dpublic_http_get.c")
HUD = Path("workspace/public/src/scripts/server-distro/a90_dpublic_hud.c")
FIRSTBOOT = Path("workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh")


class DpublicSmokeHelperTests(unittest.TestCase):
    def test_smoke_httpd_defaults_to_loopback_only(self) -> None:
        source = SMOKE_HTTPD.read_text(encoding="utf-8")
        self.assertIn('const char *bind_ip = "127.0.0.1";', source)
        self.assertIn("A90_DPUBLIC_SMOKE_OK", source)
        self.assertIn("public_exposure=outbound-tunnel-only", source)
        self.assertNotIn('const char *bind_ip = "0.0.0.0";', source)

    def test_smoke_httpd_handles_partial_writes(self) -> None:
        source = SMOKE_HTTPD.read_text(encoding="utf-8")
        self.assertIn("write_all_best_effort", source)
        self.assertIn("Connection: close", source)
        self.assertIn("Cache-Control: no-store", source)
        self.assertIn("SIGPIPE", source)

    def test_http_get_is_device_local_validation_helper(self) -> None:
        source = HTTP_GET.read_text(encoding="utf-8")
        self.assertIn('const char *host = "127.0.0.1";', source)
        self.assertIn("GET / HTTP/1.1", source)
        self.assertIn("connect(fd", source)
        self.assertNotIn("trycloudflare.com", source)

    def test_debian_hud_materializes_card0_and_draws_status(self) -> None:
        source = HUD.read_text(encoding="utf-8")
        self.assertIn('/sys/class/drm/card0/dev', source)
        self.assertIn('/dev/dri/card0', source)
        self.assertIn("DRM_IOCTL_MODE_SETCRTC", source)
        self.assertIn("A90 DEBIAN APPLIANCE", source)
        self.assertIn("D-PUBLIC SERVER READY", source)
        self.assertIn("A90_DPUBLIC_SMOKE_OK", source)

    def test_firstboot_profile_removes_proof_autoreboot_and_starts_hud(self) -> None:
        source = FIRSTBOOT.read_text(encoding="utf-8")
        self.assertIn("autoreboot_sec=disabled", source)
        self.assertNotIn("sleep 120", source)
        self.assertNotIn("reboot -f", source)
        self.assertIn("/usr/local/bin/a90-dpublic-hud", source)
        self.assertIn("hud_started=1", source)
        self.assertIn("cloudflared-quick-enable", source)
        self.assertIn("tunnel_started=manual", source)
        self.assertIn("kill_matching_cmdline", source)
        self.assertIn("wait_no_tcp_listen 1F90", source)
        self.assertIn('target=$(readlink "$fd"', source)
        self.assertIn("base_\"$line\"", source)
        self.assertIn("stage=*|autoreboot_sec=*", source)


if __name__ == "__main__":
    unittest.main()
