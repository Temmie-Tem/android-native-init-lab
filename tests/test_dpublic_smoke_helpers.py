"""Static checks for the D-public smoke helper sources."""

from __future__ import annotations

import unittest
from pathlib import Path


SMOKE_HTTPD = Path("workspace/public/src/scripts/server-distro/a90_dpublic_smoke_httpd.c")
HTTP_GET = Path("workspace/public/src/scripts/server-distro/a90_dpublic_http_get.c")
HUD = Path("workspace/public/src/scripts/server-distro/a90_dpublic_hud.c")
FIRSTBOOT = Path("workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh")
WIFI_STA = Path("workspace/public/src/scripts/server-distro/a90_dpublic_wifi_sta.sh")


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

    def test_firstboot_cleans_stale_cloudflared_runtime_in_manual_mode(self) -> None:
        source = FIRSTBOOT.read_text(encoding="utf-8")
        self.assertIn("cleanup_cloudflared_runtime", source)
        self.assertIn("kill_pidfile_if_matching", source)
        self.assertIn("cloudflared-*.pid", source)
        self.assertIn("cloudflared-*.log", source)
        self.assertIn("cloudflared-*.url", source)
        self.assertIn("public-url.txt", source)
        self.assertIn('kill_matching_cmdline "/usr/local/bin/cloudflared tunnel"', source)

        manual_idx = source.index("echo tunnel_started=manual")
        cleanup_idx = source.rindex("cleanup_cloudflared_runtime manual", 0, manual_idx)
        self.assertLess(cleanup_idx, manual_idx)

    def test_firstboot_cleans_tunnel_state_before_enabled_start(self) -> None:
        source = FIRSTBOOT.read_text(encoding="utf-8")
        branch_idx = source.index("if [ -s /etc/a90-dpublic/cloudflared-quick-enable ]")
        cleanup_idx = source.index("cleanup_cloudflared_runtime enabled-prestart", branch_idx)
        start_idx = source.index("/usr/local/bin/cloudflared tunnel --no-autoupdate", branch_idx)
        pid_idx = source.index("echo $! > /run/a90-dpublic/cloudflared-live.pid", start_idx)
        observe_idx = source.index("observe_cloudflared_start", pid_idx)
        self.assertLess(cleanup_idx, start_idx)
        self.assertLess(start_idx, pid_idx)
        self.assertLess(pid_idx, observe_idx)
        self.assertNotIn('kill "$(cat /run/a90-dpublic/cloudflared-live.pid)"', source)

    def test_firstboot_records_tunnel_readiness_without_public_url_in_marker(self) -> None:
        source = FIRSTBOOT.read_text(encoding="utf-8")
        self.assertIn("observe_cloudflared_start()", source)
        self.assertIn("cloudflared-live.url", source)
        self.assertIn("chmod 600 \"$urlfile\"", source)
        self.assertIn("tunnel_process_alive=$alive", source)
        self.assertIn("tunnel_url_observed=$url_observed", source)
        self.assertIn("tunnel_decision=quick-url-ready", source)
        self.assertIn("tunnel_decision=quick-url-pending", source)
        self.assertIn("tunnel_decision=quick-process-exited", source)
        self.assertIn("tunnel_decision=manual", source)
        self.assertNotIn('echo "$url"', source)
        self.assertNotIn(">> /run/a90-d3-marker \"$url\"", source)

    def test_firstboot_runs_wifi_sta_only_before_tunnel_when_enabled(self) -> None:
        source = FIRSTBOOT.read_text(encoding="utf-8")
        wifi_idx = source.index("if [ -s /etc/a90-dpublic/wifi-sta-enable ]")
        helper_idx = source.index("/usr/local/bin/a90-dpublic-wifi-sta", wifi_idx)
        manual_idx = source.index("wifi_sta_decision=wifi-sta-manual", helper_idx)
        tunnel_idx = source.index("if [ -s /etc/a90-dpublic/cloudflared-quick-enable ]")
        self.assertLess(helper_idx, tunnel_idx)
        self.assertLess(manual_idx, tunnel_idx)
        self.assertIn("wifi_sta_requested=0", source)
        self.assertIn("wifi_sta_started=0", source)
        self.assertIn("wifi_sta_secret_values_logged=0", source)

    def test_wifi_sta_helper_is_opt_in_and_redacted(self) -> None:
        source = WIFI_STA.read_text(encoding="utf-8")
        self.assertIn("/etc/a90-dpublic/wifi-sta-enable", source)
        self.assertIn("/etc/a90-dpublic/wpa_supplicant-wlan0.conf", source)
        self.assertIn("wpa_supplicant -B -q -i \"$IFACE\" -D nl80211", source)
        self.assertIn("dhclient -1 -q -4", source)
        self.assertIn("wifi_sta_link_set_up_rc=$link_set_up_rc", source)
        self.assertIn("wifi-sta-link-up-failed", source)
        self.assertIn("L3_HOST=cloudflare.com", source)
        self.assertIn("L3_PORT=443", source)
        self.assertIn("NC_BIN=$(command -v nc", source)
        self.assertIn("command -v nc.openbsd", source)
        self.assertIn("probe_l3_reachability", source)
        self.assertIn("wifi_sta_l3_attempted=1", source)
        self.assertIn("wifi_sta_l3_probe=cloudflare-443", source)
        self.assertIn("wifi_sta_tcp_probe_tool=$(basename \"$NC_BIN\")", source)
        self.assertIn("wifi_sta_gateway_arp_resolved=$gateway_arp_resolved", source)
        self.assertIn("wifi_sta_dns_probe_rc=$dns_probe_rc", source)
        self.assertIn("wifi_sta_tcp443_probe_rc=$tcp_probe_rc", source)
        self.assertIn("wifi-sta-l3-gateway-unreachable", source)
        self.assertIn("wifi-sta-l3-dns-failed", source)
        self.assertIn("wifi-sta-l3-tcp-failed", source)
        self.assertIn("lease_default_router()", source)
        self.assertIn("wifi_sta_default_route_router_present=1", source)
        self.assertIn("wifi_sta_default_route_set_rc=$?", source)
        self.assertIn("wifi_sta_default_route_iface=$route_iface", source)
        self.assertIn("ncm_recovery_preserved_after_dhcp=1", source)
        self.assertIn("wifi_sta_secret_values_logged=0", source)
        self.assertNotIn("ssid=", source)
        self.assertNotIn("psk=", source)


if __name__ == "__main__":
    unittest.main()
