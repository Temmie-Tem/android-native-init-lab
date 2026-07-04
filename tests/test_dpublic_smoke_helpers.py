"""Static checks for the D-public smoke helper sources."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


SMOKE_HTTPD = Path("workspace/public/src/scripts/server-distro/a90_dpublic_smoke_httpd.c")
HTTP_GET = Path("workspace/public/src/scripts/server-distro/a90_dpublic_http_get.c")
HUD = Path("workspace/public/src/scripts/server-distro/a90_dpublic_hud.c")
HUD_INTENT = Path("workspace/public/src/scripts/server-distro/a90_dpublic_hud_intent.c")
HUD_PRESENTER = Path("workspace/public/src/scripts/server-distro/a90_dpublic_hud_presenter.c")
FIRSTBOOT = Path("workspace/public/src/scripts/server-distro/a90_dpublic_firstboot.sh")
WIFI_STA = Path("workspace/public/src/scripts/server-distro/a90_dpublic_wifi_sta.sh")
API_PROBE = Path("workspace/public/src/scripts/server-distro/a90_dpublic_api_probe.sh")
NATIVE_UPLINK_PROFILE = Path("workspace/public/src/scripts/server-distro/a90_dpublic_native_uplink_profile.sh")


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

    def test_split_hud_intent_producer_is_atomic_no_drm_no_network(self) -> None:
        source = HUD_INTENT.read_text(encoding="utf-8")

        self.assertIn('DEFAULT_INTENT_PATH "/run/a90-dpublic/hud-intent.json"', source)
        self.assertIn("write_atomic", source)
        self.assertIn("fsync(fd)", source)
        self.assertIn("rename(tmp, path)", source)
        self.assertIn("fchmod(fd, 0640)", source)
        self.assertIn("a90-dpublic-hud-intent-v1", source)
        self.assertIn("public_state", source)
        self.assertIn("PUBLIC_OFF", source)
        self.assertIn("A90WSTA132_INTENT_WRITTEN=1", source)
        self.assertIn("A90WSTA132_SECRET_VALUES_LOGGED=0", source)
        self.assertNotIn("/dev/dri", source)
        self.assertNotIn("DRM_IOCTL_MODE_SETCRTC", source)
        for token in ("socket(", "bind(", "listen(", "connect("):
            self.assertNotIn(token, source)

    def test_split_hud_presenter_parser_is_bounded_and_kms_owner_only(self) -> None:
        source = HUD_PRESENTER.read_text(encoding="utf-8")

        self.assertIn("MAX_INTENT_BYTES 4096U", source)
        self.assertIn("reject_unknown_top_level_keys", source)
        self.assertIn("forbidden key", source)
        self.assertIn('"command"', source)
        self.assertIn('"ssid"', source)
        self.assertIn('"psk"', source)
        self.assertIn('"secret"', source)
        self.assertIn("DRM_IOCTL_MODE_SETCRTC", source)
        self.assertIn("A90WSTA132_PRESENTER_KMS_MASTER=1", source)
        self.assertIn("A90WSTA132_SECRET_VALUES_LOGGED=0", source)
        for token in ("system(", "popen(", "execve(", "socket(", "bind(", "listen(", "connect("):
            self.assertNotIn(token, source)

    def test_firstboot_profile_removes_proof_autoreboot_and_starts_hud(self) -> None:
        source = FIRSTBOOT.read_text(encoding="utf-8")
        self.assertIn("autoreboot_sec=disabled", source)
        self.assertNotIn("sleep 120", source)
        self.assertNotIn("reboot -f", source)
        self.assertIn("/usr/local/bin/a90-dpublic-hud-intent", source)
        self.assertIn("/usr/local/bin/a90-service-launch dpublic-hud", source)
        self.assertIn("--output /run/a90-dpublic/hud-intent.json", source)
        self.assertIn("hud_split_mode=1", source)
        self.assertIn("hud_presenter_owner=native-init", source)
        self.assertIn("hud_presenter_started=0", source)
        self.assertIn("hud_legacy_direct_kms_started=0", source)
        self.assertIn("hud_legacy_direct_kms_fallback=1", source)
        self.assertIn("/usr/local/bin/a90-dpublic-hud", source)
        self.assertIn("cloudflared-quick-enable", source)
        self.assertIn("tunnel_started=manual", source)
        self.assertIn("kill_matching_cmdline", source)
        self.assertIn("wait_no_tcp_listen 1F90", source)
        self.assertIn('target=$(readlink "$fd"', source)
        self.assertIn("base_\"$line\"", source)
        self.assertIn("stage=*|autoreboot_sec=*", source)
        self.assertIn("native_uplink_profile_command=/usr/local/bin/a90-dpublic-native-uplink-profile", source)
        self.assertIn("native_uplink_decision=operator-profile-manual", source)
        self.assertIn("native_uplink_public_default=off", source)

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
        self.assertIn("https://[A-Za-z0-9-]+\\.trycloudflare\\.com", source)
        self.assertIn("grep -v '^https://api\\.trycloudflare\\.com$'", source)
        self.assertIn("chmod 600 \"$urlfile\"", source)
        self.assertIn("tunnel_process_alive=$alive", source)
        self.assertIn("tunnel_url_observed=$url_observed", source)
        self.assertIn("tunnel_decision=quick-url-ready", source)
        self.assertIn("tunnel_decision=quick-url-dead", source)
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
        self.assertIn("latest_wifi_sta_decision()", source)
        self.assertIn("tunnel_wifi_sta_gate_required=$wifi_sta_tunnel_gate_required", source)
        self.assertIn("tunnel_wifi_sta_gate_decision=$wifi_sta_tunnel_gate_decision", source)
        self.assertIn("tunnel_wifi_sta_gate_ok=$wifi_sta_tunnel_gate_ok", source)
        self.assertIn('[ "$wifi_sta_tunnel_gate_decision" != "wifi-sta-pass" ]', source)
        self.assertIn("tunnel_started=blocked-wifi-sta", source)
        self.assertIn("tunnel_decision=wifi-sta-not-ready", source)
        self.assertIn("wifi_sta_requested=0", source)
        self.assertIn("wifi_sta_started=0", source)
        self.assertIn("wifi_sta_secret_values_logged=0", source)

    def test_wifi_sta_helper_is_opt_in_and_redacted(self) -> None:
        source = WIFI_STA.read_text(encoding="utf-8")
        self.assertIn("/etc/a90-dpublic/wifi-sta-enable", source)
        self.assertIn("/etc/a90-dpublic/wpa_supplicant-wlan0.conf", source)
        self.assertIn("wpa_supplicant -B -q -i \"$IFACE\" -D nl80211", source)
        self.assertIn("wpa_cli -p \"$WPA_CTRL_DIR\" -i \"$IFACE\"", source)
        self.assertIn("wifi_sta_ctrl_driver_country_rc", source)
        self.assertIn("wifi_sta_ctrl_status_wpa_state", source)
        self.assertIn("wait_wpa_completed()", source)
        self.assertIn("WPA_COMPLETE_ATTEMPTS=3", source)
        self.assertIn("SCAN_VIS_SAMPLES=6", source)
        self.assertIn("LINK_REASSERT_SETTLE_SEC=2", source)
        self.assertIn("link_snapshot()", source)
        self.assertIn("wifi_sta_link_${snapshot_label}_operstate=$link_operstate", source)
        self.assertIn("wifi_sta_link_${snapshot_label}_flags_lower_up=$link_flags_lower_up", source)
        self.assertIn("wifi_sta_link_${snapshot_label}_wireless_present=$link_wireless_present", source)
        self.assertIn("sample_regulatory_state()", source)
        self.assertIn("scan_visibility_probe()", source)
        self.assertIn("/etc/a90-dpublic/wifi-sta-immediate-snapshot-only", source)
        self.assertIn("wifi_sta_immediate_snapshot_only=$immediate_snapshot_only", source)
        self.assertIn("wifi_sta_config_required=0", source)
        self.assertIn("direct_iw_probe \"immediate_before_link_up\"", source)
        self.assertIn("direct_iw_probe \"immediate_after_link_up\"", source)
        self.assertIn("wifi_sta_immediate_iw_scan_bss_count=$iw_scan_bss_count", source)
        self.assertIn("sample_handoff_state()", source)
        self.assertIn("wifi_sta_handoff_${handoff_label}_rfkill_wifi_blocked=$rfkill_wifi_blocked", source)
        self.assertIn("direct_iw_probe()", source)
        self.assertIn("try_handoff_materialization()", source)
        self.assertIn("wifi_sta_handoff_materialization_branch_order=link-cycle,managed-reassert,rfkill-unblock", source)
        self.assertIn("iw dev \"$IFACE\" set type managed", source)
        self.assertIn("wifi-sta-handoff-materialization-pass", source)
        self.assertIn("wifi-sta-handoff-materialization-scan-failed", source)
        self.assertIn("wifi-sta-immediate-snapshot-pass", source)
        immediate_idx = source.index("wifi-sta-immediate-snapshot-pass")
        supplicant_idx = source.index("wpa_supplicant -B -q -i \"$IFACE\" -D nl80211")
        self.assertLess(immediate_idx, supplicant_idx)
        self.assertIn("wifi_sta_reg_${reg_label}_country_get_rc=$country_get_rc", source)
        self.assertIn("wifi_sta_reg_${reg_label}_iw_present=$iw_present", source)
        self.assertIn("wifi_sta_reg_${reg_label}_iw_dev_info_rc=$iw_dev_info_rc", source)
        self.assertIn("wifi_sta_reg_${reg_label}_iw_scan_bss_count=$iw_scan_bss_count", source)
        self.assertIn("wifi_sta_scan_${label}_trigger_rc=$scan_visibility_trigger_rc", source)
        self.assertIn("wifi_sta_scan_${label}_sample_${sample}_results_count=$scan_count", source)
        self.assertIn("wifi_sta_scan_${label}_sample_${sample}_operstate=$operstate", source)
        self.assertIn("wifi_sta_scan_${label}_found=$scan_visibility_found", source)
        self.assertIn("wifi_sta_scan_${label}_final_results_count=$scan_visibility_final_count", source)
        self.assertIn("scan_visibility_probe \"initial\"", source)
        self.assertIn("link_snapshot \"before_link_up\"", source)
        self.assertIn("link_snapshot \"after_link_up\"", source)
        self.assertIn("link_snapshot \"after_wpa_start\"", source)
        self.assertIn("link_snapshot \"after_initial_scan\"", source)
        self.assertIn("link_snapshot \"after_reassociate\"", source)
        self.assertIn("wifi_sta_assoc_attempts_max=$WPA_COMPLETE_ATTEMPTS", source)
        self.assertIn("wifi_sta_assoc_attempt_${attempt}_scan_results_count=$scan_count", source)
        self.assertIn("scan_visibility_probe \"retry_${attempt}\"", source)
        self.assertIn("wifi_sta_assoc_attempt_${attempt}_retry_scan_rc=$scan_visibility_trigger_rc", source)
        self.assertIn("wifi_sta_assoc_attempt_${attempt}_retry_scan_found=$scan_visibility_found", source)
        self.assertIn("wifi_sta_assoc_attempt_${attempt}_retry_link_up_rc=$retry_link_up_rc", source)
        self.assertIn("link_snapshot \"assoc_retry_${attempt}_after_relink\"", source)
        self.assertIn("wifi_sta_assoc_attempt_${attempt}_retry_reassociate_rc=$?", source)
        self.assertIn("wifi_sta_wpa_completed=$wpa_completed", source)
        self.assertIn("wifi_sta_wpa_completed_attempts=$wpa_completed_attempts", source)
        self.assertIn("wifi-sta-assoc-failed", source)
        self.assertIn("wifi_sta_run_id=$RUN_ID", source)
        self.assertIn("wifi_sta_event=$RUN_ID:$PHASE_SEQ:$phase:$now_ms", source)
        self.assertIn("wifi_sta_decision_run_id=$RUN_ID", source)
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
        self.assertIn("wifi_sta_gateway_ping_attempts=$gateway_ping_attempts", source)
        self.assertIn("wifi_sta_gateway_ping_successes=$gateway_ping_successes", source)
        self.assertIn("wifi_sta_gateway_neigh_state_before=$gateway_neigh_state_before", source)
        self.assertIn("wifi_sta_gateway_neigh_state_after_get=$gateway_neigh_state_after_get", source)
        self.assertIn("wifi_sta_lease_router_matches_initial=$lease_router_matches_initial", source)
        self.assertIn(
            "wifi_sta_default_route_gateway_matches_initial=$default_route_gateway_matches_initial",
            source,
        )
        self.assertIn("wifi_sta_dns_probe_rc=$dns_probe_rc", source)
        self.assertIn("wifi_sta_tcp443_probe_rc=$tcp_probe_rc", source)
        self.assertIn("wifi-sta-l3-gateway-unreachable", source)
        self.assertIn("wifi-sta-l3-dns-failed", source)
        self.assertIn("wifi-sta-l3-tcp-failed", source)
        self.assertIn("DWELL_SAMPLES=6", source)
        self.assertIn("dwell_stability_probe()", source)
        self.assertIn("wifi_sta_dwell_started=1", source)
        self.assertIn("wifi_sta_dwell_sample_${sample}_wpa_state=$wpa_state", source)
        self.assertIn("sample_wpa_signal()", source)
        self.assertIn("SIGNAL_POLL", source)
        self.assertIn("wifi_sta_dwell_sample_${sample}_wpa_ping_rc=$wpa_ping_rc", source)
        self.assertIn("wifi_sta_dwell_sample_${sample}_signal_poll_rc=$signal_poll_rc", source)
        self.assertIn("wifi_sta_dwell_sample_${sample}_signal_rssi_dbm=$signal_rssi_dbm", source)
        self.assertIn("wifi_sta_dwell_sample_${sample}_signal_linkspeed_mbps=$signal_linkspeed_mbps", source)
        self.assertIn("wifi_sta_dwell_sample_${sample}_signal_frequency_mhz=$signal_frequency_mhz", source)
        self.assertIn("wifi_sta_dwell_sample_${sample}_gateway_ping_attempts=$gateway_ping_attempts", source)
        self.assertIn("wifi_sta_dwell_sample_${sample}_gateway_ping_successes=$gateway_ping_successes", source)
        self.assertIn(
            "wifi_sta_dwell_sample_${sample}_gateway_ping_first_success_ms=$gateway_ping_first_success_ms",
            source,
        )
        self.assertIn("wifi_sta_dwell_sample_${sample}_gateway_ping_total_ms=$gateway_ping_total_ms", source)
        self.assertIn(
            "wifi_sta_dwell_sample_${sample}_gateway_neigh_state_before=$gateway_neigh_state_before",
            source,
        )
        self.assertIn(
            "wifi_sta_dwell_sample_${sample}_gateway_neigh_get_rc=$gateway_neigh_get_rc",
            source,
        )
        self.assertIn(
            "wifi_sta_dwell_sample_${sample}_gateway_neigh_state_after_get=$gateway_neigh_state_after_get",
            source,
        )
        self.assertIn("wifi_sta_dwell_sample_${sample}_gateway_arp_resolved=$gateway_arp_resolved", source)
        self.assertIn(
            "wifi_sta_dwell_sample_${sample}_lease_router_matches_initial=$lease_router_matches_initial",
            source,
        )
        self.assertIn(
            "wifi_sta_dwell_sample_${sample}_default_route_gateway_matches_lease="
            "$default_route_gateway_matches_lease",
            source,
        )
        self.assertIn("wifi_sta_dwell_sample_${sample}_tcp443_rc=$tcp_probe_rc", source)
        self.assertIn("wifi_sta_dwell_sample_${sample}_failure=$sample_failure", source)
        self.assertIn("wifi_sta_dwell_pass=$dwell_pass", source)
        self.assertIn("wifi_sta_dwell_first_fail_sample=$first_fail_sample", source)
        self.assertIn("wifi_sta_dwell_first_fail_reason=$first_fail_reason", source)
        self.assertIn("wifi-sta-dwell-failed", source)
        self.assertIn("lease_default_router()", source)
        self.assertIn("wifi_sta_default_route_router_present=1", source)
        self.assertIn("wifi_sta_default_route_set_rc=$?", source)
        self.assertIn("wifi_sta_default_route_iface=$route_iface", source)
        self.assertIn("ncm_recovery_preserved_after_dhcp=1", source)
        self.assertIn("wifi_sta_secret_values_logged=0", source)
        self.assertNotIn("ssid=", source)
        self.assertNotIn("psk=", source)

    def test_api_probe_is_cloudflared_free_and_marker_safe(self) -> None:
        source = API_PROBE.read_text(encoding="utf-8")
        self.assertIn("POST /tunnel HTTP/1.1", source)
        self.assertIn("api.trycloudflare.com", source)
        self.assertIn("api_probe_dns_api_rc=$api_dns_rc", source)
        self.assertIn("api_probe_wget_success_json=$wget_success_json", source)
        self.assertIn("api_probe_openssl_success_json=$openssl_success_json", source)
        self.assertIn("api_probe_decision=$decision", source)
        self.assertIn("api_probe_secret_values_logged=0", source)
        self.assertIn("chmod 600 \"$WGET_RESPONSE\"", source)
        self.assertNotIn("/usr/local/bin/cloudflared", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("echo $url", source)

    def test_native_uplink_profile_is_operator_gated_and_public_off(self) -> None:
        source = NATIVE_UPLINK_PROFILE.read_text(encoding="utf-8")
        self.assertIn("/usr/local/bin/a90-native-wifi-uplink-client", source)
        self.assertIn("/etc/a90-dpublic/native-uplink-enable", source)
        self.assertIn("native_uplink_profile_public_default=off", source)
        self.assertIn("A90_NATIVE_WIFI_UPLINK_ALLOW_CONFIRMED", source)
        self.assertIn("A90_NATIVE_WIFI_UPLINK_CONFIRM_TOKEN", source)
        self.assertIn("native-uplink-profile-confirmed-disabled", source)
        self.assertIn("native-uplink-profile-confirm-token-missing", source)
        self.assertIn("native_uplink_profile_public_runner=wsta43", source)
        self.assertIn("native_uplink_profile_operator_wrapper=wsta45", source)
        self.assertIn("native_uplink_profile_secret_values_logged=0", source)
        self.assertNotIn("cloudflared tunnel", source)
        self.assertNotIn("ssid=", source.lower())
        self.assertNotIn("psk=", source.lower())

    def test_native_uplink_profile_preflight_writes_marker_without_network(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "profile.marker"
            completed = subprocess.run(
                ["sh", str(NATIVE_UPLINK_PROFILE), "profile"],
                text=True,
                capture_output=True,
                check=False,
                env={
                    "PATH": "/usr/bin:/bin",
                    "A90_DPUBLIC_NATIVE_UPLINK_PROFILE_MARKER": str(marker),
                    "A90_DPUBLIC_NATIVE_UPLINK_CLIENT": str(Path(tmp) / "missing-client"),
                },
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("native_uplink_profile_decision=native-uplink-profile-ready", completed.stdout)
            self.assertIn("native_uplink_profile_public_default=off", completed.stdout)
            self.assertIn("native_uplink_profile_secret_values_logged=0", completed.stdout)
            marker_text = marker.read_text(encoding="utf-8")
            self.assertIn("native_uplink_profile_client_present=0", marker_text)
            self.assertIn("native_uplink_profile_decision=native-uplink-profile-ready", marker_text)


if __name__ == "__main__":
    unittest.main()
