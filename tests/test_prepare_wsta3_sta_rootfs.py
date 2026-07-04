from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from _loader import load_script


wsta3 = load_script("workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py")
SOURCE = Path("workspace/public/src/scripts/server-distro/prepare_wsta3_sta_rootfs.py")


def make_args(tmp: Path, **overrides) -> argparse.Namespace:
    defaults = {
        "source_rootfs": tmp / "source",
        "run_base": tmp,
        "run_dir": tmp / "run",
        "run_id": "test-run",
        "wifi_env": tmp / "wifi.env",
        "wpa_conf": None,
        "immediate_snapshot_only": False,
        "no_tarball": True,
        "tar_timeout": 10.0,
        "apt_work": tmp / "apt",
        "suite": "bookworm",
        "arch": "arm64",
        "mirror": "http://deb.debian.org/debian",
        "apt_timeout": 10.0,
        "no_sta_tool_install": True,
        "no_packet_filter_tool_install": True,
        "stage_dpublic_binaries": False,
        "stage_api_probe_tools": False,
        "stage_syscall_trace_tools": False,
        "enable_quick_tunnel": False,
        "cloudflared": tmp / "cloudflared",
        "smoke_httpd": tmp / "a90-dpublic-smoke-httpd",
        "http_get": tmp / "a90-dpublic-http-get",
        "hud": tmp / "a90-dpublic-hud",
        "hud_intent": tmp / "a90-dpublic-hud-intent",
        "hud_presenter": tmp / "a90-dpublic-hud-presenter",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def write_private(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)


def stage_packet_filter_test_tools(rootfs: Path) -> None:
    (rootfs / "usr/sbin").mkdir(parents=True, exist_ok=True)
    for name in (
        "iptables-legacy",
        "ip6tables-legacy",
        "iptables-legacy-restore",
        "ip6tables-legacy-restore",
        "iptables-legacy-save",
        "ip6tables-legacy-save",
    ):
        (rootfs / "usr/sbin" / name).write_text("", encoding="utf-8")


def stage_syscall_trace_test_tools(rootfs: Path) -> None:
    (rootfs / "usr/bin").mkdir(parents=True, exist_ok=True)
    (rootfs / "usr/bin/strace").write_text("", encoding="utf-8")


class PrepareWsta3PrivateRootfsTests(unittest.TestCase):
    def test_wifi_env_loader_is_fail_closed_and_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / "wifi.env"
            self.assertEqual(wsta3.load_wifi_env(env)["reason"], "wifi-env-missing")

            write_private(env, "A90_WIFI_SSID='Test Net'\nA90_WIFI_PSK='12345678'\n", mode=0o644)
            self.assertEqual(wsta3.load_wifi_env(env)["reason"], "wifi-env-not-0600")

            env.chmod(0o600)
            loaded = wsta3.load_wifi_env(env)

        self.assertTrue(loaded["ok"])
        self.assertEqual(loaded["ssid_len"], 8)
        self.assertEqual(loaded["psk_len"], 8)
        compact = {k: v for k, v in loaded.items() if k not in {"ssid", "psk"}}
        self.assertNotIn("Test Net", repr(compact))
        self.assertNotIn("12345678", repr(compact))

    def test_generated_supplicant_text_is_validated_without_secret_metadata(self) -> None:
        env = {"ssid": 'Test "Net"', "psk": "12345678"}
        text = wsta3.supplicant_text_from_env(env)
        self.assertIn("network={", text)
        self.assertIn("key_mgmt=WPA-PSK", text)

        with tempfile.TemporaryDirectory() as tmp:
            conf = Path(tmp) / "wpa.conf"
            write_private(conf, text)
            meta = wsta3.supplicant_config_metadata(conf)

        self.assertTrue(meta["ok"])
        self.assertTrue(meta["has_network_block"])
        self.assertTrue(meta["has_ssid_field"])
        self.assertTrue(meta["has_auth_field"])
        self.assertEqual(meta["secret_values_logged"], 0)

    def test_stage_config_sets_enable_and_config_private_modes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp) / "rootfs"
            (rootfs / wsta3.TARGET_HELPER.parent).mkdir(parents=True)
            (rootfs / wsta3.TARGET_HELPER).write_text("#!/bin/sh\n", encoding="utf-8")
            conf = Path(tmp) / "wpa.conf"
            write_private(conf, "network={\nssid=\"x\"\npsk=\"12345678\"\n}\n")

            result = wsta3.stage_config(rootfs, conf)

            self.assertEqual(result["config_mode"], "0o600")
            self.assertEqual(result["enable_mode"], "0o600")
            self.assertTrue((rootfs / wsta3.TARGET_CONFIG).is_file())
            self.assertEqual((rootfs / wsta3.TARGET_ENABLE).read_text(encoding="utf-8"), "1\n")
            self.assertTrue(result["helper_present"])

    def test_stage_immediate_snapshot_only_avoids_supplicant_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp) / "rootfs"

            result = wsta3.stage_immediate_snapshot_only(rootfs)

            self.assertEqual(result["enable_mode"], "0o600")
            self.assertEqual(result["snapshot_only_mode"], "0o600")
            self.assertFalse(result["config_required"])
            self.assertFalse(result["config_target_present"])
            self.assertTrue((rootfs / wsta3.TARGET_ENABLE).is_file())
            self.assertTrue((rootfs / wsta3.TARGET_IMMEDIATE_SNAPSHOT_ONLY).is_file())
            self.assertFalse((rootfs / wsta3.TARGET_CONFIG).exists())

    def test_stage_dpublic_firstboot_installs_autostart_hook(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp) / "rootfs"

            result = wsta3.stage_dpublic_firstboot(rootfs)

            firstboot = rootfs / wsta3.TARGET_FIRSTBOOT
            self.assertTrue(firstboot.is_file())
            self.assertEqual(firstboot.stat().st_mode & 0o777, 0o755)
            text = firstboot.read_text(encoding="utf-8")
            self.assertIn("autoreboot_sec=disabled", text)
            self.assertIn("/usr/local/bin/a90-dpublic-wifi-sta", text)
            self.assertTrue(result["autoreboot_disabled_marker"])
            self.assertTrue(result["wifi_sta_helper_invoked"])
            self.assertTrue(result["native_uplink_profile_marker"])
            self.assertTrue(result["public_default_off_marker"])

    def test_stage_dpublic_wifi_sta_helper_overwrites_with_current_l3_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)
            target = rootfs / wsta3.TARGET_HELPER
            target.parent.mkdir(parents=True)
            target.write_text("#!/bin/sh\necho old-helper\n", encoding="utf-8")

            result = wsta3.stage_dpublic_wifi_sta_helper(rootfs)

            text = target.read_text(encoding="utf-8")
            self.assertTrue(result["latest_helper_staged"])
            self.assertTrue(result["l3_gate_present"])
            self.assertTrue(result["dwell_gate_present"])
            self.assertTrue(result["signal_dwell_present"])
            self.assertTrue(result["gateway_dwell_present"])
            self.assertTrue(result["assoc_retry_present"])
            self.assertTrue(result["scan_visibility_present"])
            self.assertTrue(result["linkstate_diag_present"])
            self.assertTrue(result["iw_diag_present"])
            self.assertTrue(result["immediate_snapshot_present"])
            self.assertTrue(result["handoff_materialization_present"])
            self.assertTrue(result["tcp_probe_fallback_present"])
            self.assertIn("probe_l3_reachability", text)
            self.assertIn("dwell_stability_probe", text)
            self.assertIn("SIGNAL_POLL", text)
            self.assertIn("gateway_ping_attempts", text)
            self.assertIn("wifi_sta_assoc_attempts_max", text)
            self.assertIn("scan_visibility_probe", text)
            self.assertIn("link_snapshot", text)
            self.assertIn("iw_scan_bss_count", text)
            self.assertIn("wifi-sta-immediate-snapshot-pass", text)
            self.assertIn("wifi-sta-handoff-materialization-scan-failed", text)
            self.assertIn("nc.openbsd", text)
            self.assertNotIn("old-helper", text)

    def test_stage_dpublic_api_probe_helper_is_manual_and_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)

            result = wsta3.stage_dpublic_api_probe_helper(rootfs)

            target = rootfs / wsta3.TARGET_API_PROBE
            text = target.read_text(encoding="utf-8")
            self.assertTrue(result["latest_helper_staged"])
            self.assertTrue(result["api_post_present"])
            self.assertTrue(result["secret_hygiene_marker"])
            self.assertTrue(result["cloudflared_not_started"])
            self.assertEqual(target.stat().st_mode & 0o777, 0o755)
            self.assertIn("api_probe_secret_values_logged=0", text)
            self.assertIn("api_probe_decision=", text)
            self.assertNotIn("/usr/local/bin/cloudflared", text)

    def test_stage_native_wifi_service_client_is_status_scan_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)

            result = wsta3.stage_native_wifi_service_client(rootfs)

            target = rootfs / wsta3.TARGET_NATIVE_WIFI_SERVICE_CLIENT
            text = target.read_text(encoding="utf-8")
            self.assertTrue(result["latest_helper_staged"])
            self.assertTrue(result["file_protocol_present"])
            self.assertTrue(result["atomic_request_present"])
            self.assertTrue(result["status_scan_only"])
            self.assertTrue(result["dangerous_ops_denied"])
            self.assertTrue(result["owner_check_present"])
            self.assertTrue(result["version_check_present"])
            self.assertTrue(result["redacted_response_filter_present"])
            self.assertTrue(result["secret_hygiene_marker"])
            self.assertEqual(target.stat().st_mode & 0o777, 0o755)
            self.assertIn("/tmp/a90-native-wifi-service", text)
            self.assertIn("native-wifi-service-op-denied", text)
            self.assertIn("owner\" != \"native-init\"", text)
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())

    def test_stage_native_wifi_uplink_client_has_confirmed_autoconnect_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)

            result = wsta3.stage_native_wifi_uplink_client(rootfs)

            target = rootfs / wsta3.TARGET_NATIVE_WIFI_UPLINK_CLIENT
            text = target.read_text(encoding="utf-8")
            self.assertTrue(result["latest_helper_staged"])
            self.assertTrue(result["file_protocol_present"])
            self.assertTrue(result["atomic_request_present"])
            self.assertTrue(result["status_no_confirm_and_confirmed_gate"])
            self.assertTrue(result["confirmed_autoconnect_env_gated"])
            self.assertTrue(result["confirmed_autoconnect_fail_closed"])
            self.assertTrue(result["dangerous_ops_denied"])
            self.assertTrue(result["owner_check_present"])
            self.assertTrue(result["version_check_present"])
            self.assertTrue(result["redacted_profile_filter_present"])
            self.assertTrue(result["secret_hygiene_marker"])
            self.assertEqual(target.stat().st_mode & 0o777, 0o755)
            self.assertIn("/tmp/a90-native-wifi-uplink-service", text)
            self.assertIn("native-wifi-uplink-client-op-denied", text)
            self.assertIn("native-wifi-uplink-client-confirmed-disabled", text)
            self.assertIn("native-wifi-uplink-client-confirm-token-missing", text)
            self.assertIn("owner\" != \"native-init\"", text)
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())

    def test_stage_native_uplink_profile_is_operator_gated_and_public_off(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)

            result = wsta3.stage_native_uplink_profile(rootfs)

            target = rootfs / wsta3.TARGET_NATIVE_UPLINK_PROFILE
            text = target.read_text(encoding="utf-8")
            self.assertTrue(result["latest_helper_staged"])
            self.assertTrue(result["native_client_delegation_present"])
            self.assertTrue(result["operator_enable_gate_present"])
            self.assertTrue(result["confirmed_autoconnect_env_gated"])
            self.assertTrue(result["public_default_off_marker"])
            self.assertTrue(result["public_tunnel_not_started"])
            self.assertTrue(result["wsta43_sequence_marker"])
            self.assertTrue(result["secret_hygiene_marker"])
            self.assertEqual(target.stat().st_mode & 0o777, 0o755)
            self.assertIn("/usr/local/bin/a90-native-wifi-uplink-client", text)
            self.assertIn("/etc/a90-dpublic/native-uplink-enable", text)
            self.assertIn("native_uplink_profile_public_default=off", text)
            self.assertNotIn("cloudflared tunnel", text)
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())

    def test_stage_packet_filter_helper_is_manual_and_restorable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)

            result = wsta3.stage_packet_filter_helper(rootfs)

            target = rootfs / wsta3.TARGET_PACKET_FILTER
            text = target.read_text(encoding="utf-8")
            self.assertTrue(result["latest_helper_staged"])
            self.assertTrue(result["preflight_op_present"])
            self.assertTrue(result["apply_op_present"])
            self.assertTrue(result["restore_op_present"])
            self.assertTrue(result["save_before_apply_present"])
            self.assertTrue(result["failure_restore_present"])
            self.assertTrue(result["loopback_accept_present"])
            self.assertTrue(result["default_drop_present"])
            self.assertTrue(result["output_accept_present"])
            self.assertIn("packet_filter_control_ssh_accept=1", text)
            self.assertIn("192.168.7.1/32", text)
            self.assertIn("--dport $CONTROL_SSH_PORT", text)
            self.assertTrue(result["auto_apply_absent"])
            self.assertTrue(result["secret_hygiene_marker"])
            self.assertEqual(target.stat().st_mode & 0o777, 0o755)
            self.assertIn("apply-loopback-default-drop)", text)
            self.assertIn("restore_saved_rules", text)
            self.assertIn("rules_to_restore", text)
            self.assertIn('"$IPT4" -S > "$BEFORE_RULES4"', text)
            self.assertNotIn("iptables-legacy-save", text)
            self.assertIn("packet_filter_tool_missing=", text)
            self.assertIn("packet_filter_apply_autostart=0", text)
            self.assertNotIn("cloudflared tunnel", text)
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())

    def test_stage_native_uplink_marker_merges_without_overwriting_existing_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)
            marker = rootfs / wsta3.TARGET_STAGE_MARKER
            marker.parent.mkdir(parents=True)
            marker.write_text("stage=old\nwifi-sta=old\n", encoding="utf-8")

            result = wsta3.stage_native_uplink_stage_marker(rootfs)

            text = marker.read_text(encoding="utf-8")
            self.assertIn("stage=old", text)
            self.assertIn("wifi-sta=old", text)
            self.assertTrue(result["profile_marker_present"])
            self.assertTrue(result["operator_control_marker_present"])
            self.assertTrue(result["public_default_off_marker"])
            self.assertIn("native-uplink-profile=/usr/local/bin/a90-dpublic-native-uplink-profile", text)
            self.assertIn("native-uplink=operator-controlled via /etc/a90-dpublic/native-uplink-enable", text)
            self.assertIn("public-exposure-default=off", text)

    def test_stage_dpublic_binaries_and_quick_tunnel_enable_are_private(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rootfs = tmp_path / "rootfs"
            rootfs.mkdir()
            for name in (
                "cloudflared",
                "a90-dpublic-smoke-httpd",
                "a90-dpublic-http-get",
                "a90-dpublic-hud",
                "a90-dpublic-hud-intent",
                "a90-dpublic-hud-presenter",
            ):
                (tmp_path / name).write_bytes((name + "\n").encode("utf-8"))
            args = make_args(
                tmp_path,
                cloudflared=tmp_path / "cloudflared",
                smoke_httpd=tmp_path / "a90-dpublic-smoke-httpd",
                http_get=tmp_path / "a90-dpublic-http-get",
                hud=tmp_path / "a90-dpublic-hud",
                hud_intent=tmp_path / "a90-dpublic-hud-intent",
                hud_presenter=tmp_path / "a90-dpublic-hud-presenter",
            )

            binaries = wsta3.stage_dpublic_binaries(rootfs, args)
            enable = wsta3.stage_quick_tunnel_enable(rootfs, True)

            self.assertTrue(binaries["staged"])
            self.assertEqual(binaries["binaries"]["cloudflared"]["mode"], "0o755")
            self.assertTrue((rootfs / "usr/local/bin/cloudflared").is_file())
            self.assertTrue((rootfs / "usr/local/bin/a90-dpublic-smoke-httpd").is_file())
            self.assertTrue((rootfs / "usr/local/bin/a90-dpublic-hud-intent").is_file())
            self.assertTrue((rootfs / "usr/local/bin/a90-dpublic-hud-presenter").is_file())
            self.assertEqual(binaries["binaries"]["hud_intent"]["target"], "usr/local/bin/a90-dpublic-hud-intent")
            self.assertEqual(binaries["binaries"]["hud_presenter"]["mode"], "0o755")
            quick = rootfs / wsta3.TARGET_QUICK_TUNNEL_ENABLE
            self.assertEqual(quick.read_text(encoding="utf-8"), "1\n")
            self.assertEqual(quick.stat().st_mode & 0o777, 0o600)
            self.assertTrue(enable["enabled"])
            self.assertEqual(enable["mode"], "0o600")

    def test_api_probe_tools_are_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp) / "rootfs"
            rootfs.mkdir()
            args = make_args(Path(tmp), stage_api_probe_tools=False)

            result = wsta3.ensure_api_probe_tools(rootfs, args)

            self.assertTrue(result["ok"])
            self.assertFalse(result["requested"])
            self.assertFalse(result["installed"])
            self.assertFalse(result["before"]["tools"]["wget"]["present"])

    def test_api_probe_tools_restore_usrmerge_when_wget_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp) / "rootfs"
            (rootfs / "usr/bin").mkdir(parents=True)
            (rootfs / "usr/lib").mkdir(parents=True)
            (rootfs / "bin").mkdir()
            (rootfs / "bin/wget").write_text("", encoding="utf-8")
            args = make_args(Path(tmp), stage_api_probe_tools=True)

            result = wsta3.ensure_api_probe_tools(rootfs, args)

            self.assertTrue(result["ok"])
            self.assertTrue(result["requested"])
            self.assertFalse(result["installed"])
            self.assertTrue((rootfs / "bin").is_symlink())
            self.assertTrue((rootfs / "usr/bin/wget").is_file())

    def test_sta_tools_missing_blocks_when_install_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp) / "rootfs"
            rootfs.mkdir()
            args = make_args(Path(tmp), no_sta_tool_install=True)

            result = wsta3.ensure_sta_tools(rootfs, args)

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "sta-tools-missing-install-disabled")
        self.assertFalse(result["before"]["tools"]["wpa_supplicant"]["present"])
        self.assertFalse(result["before"]["tools"]["wpa_cli"]["present"])
        self.assertFalse(result["before"]["tools"]["dhclient"]["present"])
        self.assertFalse(result["before"]["tools"]["nc"]["present"])
        self.assertFalse(result["before"]["tools"]["iw"]["present"])

    def test_ensure_sta_tools_restores_usrmerge_when_tools_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp) / "rootfs"
            (rootfs / "usr/sbin").mkdir(parents=True)
            (rootfs / "usr/bin").mkdir(parents=True)
            (rootfs / "usr/lib").mkdir(parents=True)
            (rootfs / "sbin").mkdir()
            (rootfs / "sbin/wpa_supplicant").write_text("", encoding="utf-8")
            (rootfs / "sbin/wpa_cli").write_text("", encoding="utf-8")
            (rootfs / "sbin/dhclient").write_text("", encoding="utf-8")
            (rootfs / "sbin/iw").write_text("", encoding="utf-8")
            (rootfs / "usr/sbin/ip").write_text("", encoding="utf-8")
            (rootfs / "usr/bin/ping").write_text("", encoding="utf-8")
            (rootfs / "usr/bin/getent").write_text("", encoding="utf-8")
            (rootfs / "usr/bin/nc").write_text("", encoding="utf-8")
            args = make_args(Path(tmp))

            result = wsta3.ensure_sta_tools(rootfs, args)

            self.assertTrue(result["ok"])
            self.assertFalse(result["installed"])
            self.assertTrue((rootfs / "sbin").is_symlink())
            self.assertEqual((rootfs / "sbin").readlink(), Path("usr/sbin"))
            self.assertTrue((rootfs / "usr/sbin/wpa_supplicant").is_file())
            self.assertTrue((rootfs / "usr/sbin/wpa_cli").is_file())
            self.assertTrue((rootfs / "usr/sbin/dhclient").is_file())
            self.assertTrue((rootfs / "usr/sbin/iw").is_file())

    def test_packet_filter_tools_missing_blocks_when_install_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp) / "rootfs"
            rootfs.mkdir()
            args = make_args(Path(tmp), no_packet_filter_tool_install=True)

            result = wsta3.ensure_packet_filter_tools(rootfs, args)

        self.assertFalse(result["ok"])
        self.assertEqual(result["backend"], "legacy-iptables")
        self.assertFalse(result["policy_enforced"])
        self.assertEqual(result["reason"], "packet-filter-tools-missing-install-disabled")
        self.assertFalse(result["before"]["tools"]["iptables_legacy"]["present"])
        self.assertFalse(result["before"]["tools"]["ip6tables_legacy"]["present"])

    def test_packet_filter_tools_restore_usrmerge_when_legacy_tools_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp) / "rootfs"
            (rootfs / "usr/lib").mkdir(parents=True)
            (rootfs / "sbin").mkdir()
            stage_packet_filter_test_tools(rootfs)
            args = make_args(Path(tmp))

            result = wsta3.ensure_packet_filter_tools(rootfs, args)

            self.assertTrue(result["ok"])
            self.assertEqual(result["backend"], "legacy-iptables")
            self.assertFalse(result["installed"])
            self.assertFalse(result["policy_enforced"])
            self.assertTrue(result["after"]["default_drop_ready_for_source"])
            self.assertTrue((rootfs / "sbin").is_symlink())
            self.assertTrue((rootfs / "usr/sbin/iptables-legacy").is_file())
            self.assertTrue((rootfs / "usr/sbin/ip6tables-legacy").is_file())

    def test_packet_filter_stage_marker_merges_without_enforcing_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)
            marker = rootfs / wsta3.TARGET_STAGE_MARKER
            marker.parent.mkdir(parents=True)
            marker.write_text("stage=old\npacket-filter-backend=old\n", encoding="utf-8")

            result = wsta3.stage_packet_filter_stage_marker(rootfs)

            text = marker.read_text(encoding="utf-8")
            self.assertIn("stage=old", text)
            self.assertNotIn("packet-filter-backend=old", text)
            self.assertTrue(result["backend_marker_present"])
            self.assertTrue(result["helper_marker_present"])
            self.assertTrue(result["tools_marker_present"])
            self.assertTrue(result["policy_not_enforced_marker_present"])
            self.assertTrue(result["default_drop_deferred_marker_present"])
            self.assertIn("packet-filter-backend=legacy-iptables", text)
            self.assertIn("packet-filter-helper=/usr/local/bin/a90-dpublic-packet-filter", text)
            self.assertIn("packet-filter-policy=not-enforced", text)
            self.assertIn("packet-filter-default-drop=deferred-WSTA93", text)

    def test_syscall_trace_tools_are_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp) / "rootfs"
            rootfs.mkdir()
            args = make_args(Path(tmp), stage_syscall_trace_tools=False)

            result = wsta3.ensure_syscall_trace_tools(rootfs, args)

        self.assertTrue(result["ok"])
        self.assertFalse(result["requested"])
        self.assertFalse(result["installed"])
        self.assertFalse(result["profile_capture_ready_for_source"])
        self.assertFalse(result["before"]["tools"]["strace"]["present"])
        self.assertFalse(result["after"]["tools"]["strace"]["present"])

    def test_syscall_trace_tools_restore_usrmerge_when_strace_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp) / "rootfs"
            (rootfs / "usr/lib").mkdir(parents=True)
            (rootfs / "bin").mkdir()
            stage_syscall_trace_test_tools(rootfs)
            args = make_args(Path(tmp), stage_syscall_trace_tools=True)

            result = wsta3.ensure_syscall_trace_tools(rootfs, args)

            self.assertTrue(result["ok"])
            self.assertTrue(result["requested"])
            self.assertFalse(result["installed"])
            self.assertTrue(result["profile_capture_ready_for_source"])
            self.assertTrue((rootfs / "bin").is_symlink())
            self.assertEqual((rootfs / "bin").readlink(), Path("usr/bin"))
            self.assertTrue((rootfs / "usr/bin/strace").is_file())

    def test_syscall_trace_stage_marker_merges_without_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)
            marker = rootfs / wsta3.TARGET_STAGE_MARKER
            marker.parent.mkdir(parents=True)
            marker.write_text("stage=old\nsyscall-trace-tool=old\n", encoding="utf-8")

            result = wsta3.stage_syscall_trace_stage_marker(rootfs)

            text = marker.read_text(encoding="utf-8")
            self.assertIn("stage=old", text)
            self.assertNotIn("syscall-trace-tool=old", text)
            self.assertTrue(result["tool_marker_present"])
            self.assertTrue(result["target_marker_present"])
            self.assertTrue(result["profile_deferred_marker_present"])
            self.assertTrue(result["public_default_off_marker"])
            self.assertIn("syscall-trace-tool=/usr/bin/strace", text)
            self.assertIn("syscall-trace-target=dpublic-smoke-httpd", text)
            self.assertIn("syscall-trace-profile-source=deferred-WSTA114", text)
            self.assertIn("syscall-trace-public-default=off", text)

    def test_stage_service_identities_adds_nonroot_service_accounts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)
            etc = rootfs / "etc"
            etc.mkdir()
            (etc / "passwd").write_text("root:x:0:0:root:/root:/bin/sh\n", encoding="utf-8")
            (etc / "group").write_text("root:x:0:\n", encoding="utf-8")

            result = wsta3.stage_service_identities(rootfs)

            passwd = (etc / "passwd").read_text(encoding="utf-8")
            group = (etc / "group").read_text(encoding="utf-8")
            self.assertIn("a90www:x:3901:3901:A90 service a90www:/nonexistent:/usr/sbin/nologin", passwd)
            self.assertIn("a90tunnel:x:3902:3902:A90 service a90tunnel:/nonexistent:/usr/sbin/nologin", passwd)
            self.assertIn("a90admin:x:3903:3903:A90 service a90admin:/nonexistent:/usr/sbin/nologin", passwd)
            self.assertIn("a90hud:x:3904:3904:A90 service a90hud:/nonexistent:/usr/sbin/nologin", passwd)
            self.assertIn("a90www:x:3901:", group)
            self.assertIn("a90tunnel:x:3902:", group)
            self.assertIn("a90admin:x:3903:", group)
            self.assertIn("a90hud:x:3904:", group)
            self.assertEqual((etc / "passwd").stat().st_mode & 0o777, 0o644)
            self.assertEqual((etc / "group").stat().st_mode & 0o777, 0o644)
            self.assertIn("wsta-native-uplink-helper", result["root_boundary_services"])
            self.assertEqual(result["secret_values_logged"], 0)

    def test_stage_service_identities_rejects_conflicting_account(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)
            etc = rootfs / "etc"
            etc.mkdir()
            (etc / "passwd").write_text("a90www:x:9999:9999:bad:/tmp:/bin/sh\n", encoding="utf-8")
            (etc / "group").write_text("", encoding="utf-8")

            with self.assertRaises(ValueError):
                wsta3.stage_service_identities(rootfs)

    def test_stage_no_new_privs_launcher_and_policy_are_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)

            launcher = wsta3.stage_no_new_privs_launcher(rootfs)
            policy = wsta3.stage_service_hardening_policy(rootfs)
            marker = wsta3.stage_service_hardening_stage_marker(rootfs)

            launcher_path = rootfs / wsta3.TARGET_SERVICE_LAUNCHER
            launcher_text = launcher_path.read_text(encoding="utf-8")
            policy_payload = json.loads((rootfs / wsta3.TARGET_SERVICE_HARDENING_POLICY).read_text(encoding="utf-8"))
            marker_text = (rootfs / wsta3.TARGET_STAGE_MARKER).read_text(encoding="utf-8")
            self.assertEqual(launcher_path.stat().st_mode & 0o777, 0o755)
            self.assertTrue(launcher["setpriv_required"])
            self.assertTrue(launcher["no_new_privs_present"])
            self.assertTrue(launcher["unknown_service_blocks"])
            self.assertTrue(launcher["command_required_blocks"])
            self.assertIn("exec setpriv --no-new-privs", launcher_text)
            self.assertIn("blocked-setpriv-missing", launcher_text)
            self.assertIn("dpublic-smoke-httpd)", launcher_text)
            self.assertIn("A90_USER=a90www", launcher_text)
            self.assertIn("cloudflared-quick-tunnel)", launcher_text)
            self.assertIn("A90_USER=a90tunnel", launcher_text)
            self.assertIn("dpublic-hud)", launcher_text)
            self.assertIn("A90_USER=a90hud", launcher_text)
            self.assertIn("no-network-intent-producer-only", launcher_text)
            self.assertNotIn("cloudflared tunnel", launcher_text)
            self.assertNotIn("ssid=", launcher_text.lower())
            self.assertNotIn("psk=", launcher_text.lower())
            self.assertEqual(policy["service_count"], 4)
            self.assertTrue(policy_payload["default_public_off"])
            self.assertEqual(policy_payload["services"]["dpublic-hud"]["user"], "a90hud")
            self.assertEqual(policy_payload["services"]["dpublic-hud"]["network_intent"], "no-network-intent-producer-only")
            self.assertEqual(policy_payload["services"]["cloudflared-quick-tunnel"]["ambient_capabilities"], [])
            self.assertIn("setpriv", policy_payload["launcher_requires"])
            self.assertTrue(marker["users_marker_present"])
            self.assertTrue(marker["no_new_privs_marker_present"])
            self.assertTrue(marker["public_default_off_marker"])
            self.assertIn("service-hardening-no-new-privs=setpriv-required", marker_text)

    def test_stage_hud_split_stage_marker_records_native_presenter_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)
            marker = rootfs / wsta3.TARGET_STAGE_MARKER
            marker.parent.mkdir(parents=True)
            marker.write_text("stage=old\nhud-split-boundary=old\n", encoding="utf-8")

            result = wsta3.stage_hud_split_stage_marker(rootfs)

            marker_text = marker.read_text(encoding="utf-8")
            self.assertTrue(result["intent_producer_marker_present"])
            self.assertTrue(result["presenter_marker_present"])
            self.assertTrue(result["boundary_marker_present"])
            self.assertTrue(result["direct_kms_disabled_marker_present"])
            self.assertTrue(result["presenter_owner_marker_present"])
            self.assertTrue(result["public_default_off_marker"])
            self.assertIn("stage=old", marker_text)
            self.assertIn("hud-split-intent-producer=/usr/local/bin/a90-dpublic-hud-intent", marker_text)
            self.assertIn("hud-split-presenter=/usr/local/bin/a90-dpublic-hud-presenter", marker_text)
            self.assertIn("hud-split-boundary=/run/a90-dpublic/hud-intent.json", marker_text)
            self.assertIn("hud-split-direct-kms-for-a90hud=disabled", marker_text)
            self.assertNotIn("hud-split-boundary=old", marker_text)

    def test_create_private_tarball_forces_owner_private_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rootfs = tmp_path / "rootfs"
            rootfs.mkdir()
            tarball = tmp_path / "rootfs.tar"

            def fake_create_tarball(_rootfs: Path, out: Path, _timeout: float) -> dict[str, object]:
                out.write_bytes(b"fake tar")
                out.chmod(0o664)
                return {"size_bytes": out.stat().st_size}

            with (
                mock.patch.object(wsta3.d4c, "create_tarball", side_effect=fake_create_tarball),
                mock.patch.object(
                    wsta3.d4c,
                    "verify_tarball",
                    return_value={"required_entries_present": ["./etc/a90-dpublic/wifi-sta-enable"]},
                ),
            ):
                result = wsta3.create_private_tarball(rootfs, tarball, 10.0)

            self.assertEqual(result["tarball_mode"], "0o600")
            self.assertEqual(tarball.stat().st_mode & 0o777, 0o600)
            self.assertTrue(result["sha256_redacted"])

    def test_prepare_blocks_without_credentials_before_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            args = make_args(tmp_path)

            result = wsta3.prepare(args)

            self.assertFalse(result["ok"])
            self.assertEqual(result["decision"], "wsta3-private-config-blocked-wifi-env-missing")
            self.assertFalse((tmp_path / "run" / "rootfs").exists())
            self.assertEqual(result["secret_values_logged"], 0)

    def test_prepare_copies_verified_rootfs_and_keeps_summary_secret_free(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source"
            (source / "usr/local/bin").mkdir(parents=True)
            (source / "usr/sbin").mkdir(parents=True)
            (source / "usr/bin").mkdir(parents=True)
            (source / "etc/a90-dpublic").mkdir(parents=True)
            (source / "usr/local/bin/a90-dpublic-wifi-sta").write_text("#!/bin/sh\n", encoding="utf-8")
            (source / "usr/sbin/ip").write_text("", encoding="utf-8")
            (source / "usr/sbin/wpa_supplicant").write_text("", encoding="utf-8")
            (source / "usr/sbin/wpa_cli").write_text("", encoding="utf-8")
            (source / "usr/sbin/dhclient").write_text("", encoding="utf-8")
            (source / "usr/sbin/iw").write_text("", encoding="utf-8")
            (source / "usr/bin/ping").write_text("", encoding="utf-8")
            (source / "usr/bin/getent").write_text("", encoding="utf-8")
            (source / "usr/bin/nc").write_text("", encoding="utf-8")
            stage_packet_filter_test_tools(source)
            env = tmp_path / "wifi.env"
            write_private(env, "A90_WIFI_SSID='Test Net'\nA90_WIFI_PSK='12345678'\n")

            with mock.patch.object(wsta3.d4c, "verify_rootfs", return_value={"ok": True}) as verify:
                result = wsta3.prepare(make_args(tmp_path, source_rootfs=source, wifi_env=env))

            target = tmp_path / "run" / "rootfs"
            self.assertTrue(result["ok"])
            self.assertEqual(result["decision"], "wsta3-private-rootfs-prepared")
            self.assertEqual((tmp_path / "run").stat().st_mode & 0o777, 0o700)
            self.assertTrue((target / wsta3.TARGET_CONFIG).is_file())
            self.assertTrue((target / wsta3.TARGET_ENABLE).is_file())
            self.assertTrue((target / wsta3.TARGET_FIRSTBOOT).is_file())
            self.assertTrue(result["sta_tools"]["ok"])
            self.assertTrue(result["wifi_sta_helper"]["latest_helper_staged"])
            self.assertTrue(result["wifi_sta_helper"]["l3_gate_present"])
            self.assertTrue(result["wifi_sta_helper"]["dwell_gate_present"])
            self.assertTrue(result["wifi_sta_helper"]["signal_dwell_present"])
            self.assertTrue(result["wifi_sta_helper"]["gateway_dwell_present"])
            self.assertTrue(result["wifi_sta_helper"]["assoc_retry_present"])
            self.assertTrue(result["wifi_sta_helper"]["scan_visibility_present"])
            self.assertTrue(result["wifi_sta_helper"]["linkstate_diag_present"])
            self.assertTrue(result["wifi_sta_helper"]["iw_diag_present"])
            self.assertTrue(result["wifi_sta_helper"]["immediate_snapshot_present"])
            self.assertTrue(result["wifi_sta_helper"]["handoff_materialization_present"])
            self.assertTrue(result["api_probe_helper"]["api_post_present"])
            self.assertTrue(result["native_wifi_service_client"]["latest_helper_staged"])
            self.assertTrue(result["native_wifi_service_client"]["dangerous_ops_denied"])
            self.assertTrue(result["native_wifi_uplink_client"]["latest_helper_staged"])
            self.assertTrue(result["native_wifi_uplink_client"]["confirmed_autoconnect_env_gated"])
            self.assertTrue(result["native_wifi_uplink_client"]["confirmed_autoconnect_fail_closed"])
            self.assertTrue(result["native_uplink_profile"]["latest_helper_staged"])
            self.assertTrue(result["native_uplink_profile"]["operator_enable_gate_present"])
            self.assertTrue(result["native_uplink_profile"]["public_default_off_marker"])
            self.assertTrue(result["packet_filter_helper"]["latest_helper_staged"])
            self.assertTrue(result["packet_filter_helper"]["restore_op_present"])
            self.assertTrue(result["packet_filter_helper"]["auto_apply_absent"])
            self.assertTrue(result["native_uplink_stage_marker"]["profile_marker_present"])
            self.assertTrue(result["native_uplink_stage_marker"]["public_default_off_marker"])
            self.assertTrue(result["packet_filter_tools"]["ok"])
            self.assertEqual(result["packet_filter_tools"]["backend"], "legacy-iptables")
            self.assertFalse(result["packet_filter_tools"]["policy_enforced"])
            self.assertTrue(result["packet_filter_stage_marker"]["backend_marker_present"])
            self.assertTrue(result["packet_filter_stage_marker"]["helper_marker_present"])
            self.assertTrue(result["packet_filter_stage_marker"]["default_drop_deferred_marker_present"])
            self.assertFalse(result["syscall_trace_tools"]["requested"])
            self.assertFalse(result["syscall_trace_tools"]["profile_capture_ready_for_source"])
            self.assertTrue(result["syscall_trace_stage_marker"]["tool_marker_present"])
            self.assertTrue(result["syscall_trace_stage_marker"]["target_marker_present"])
            self.assertTrue(result["syscall_trace_stage_marker"]["profile_deferred_marker_present"])
            self.assertTrue(result["syscall_trace_stage_marker"]["public_default_off_marker"])
            self.assertIn("a90www", result["service_identities"]["users"])
            self.assertIn("a90tunnel", result["service_identities"]["users"])
            self.assertTrue(result["service_launcher"]["no_new_privs_present"])
            self.assertTrue(result["service_launcher"]["unknown_service_blocks"])
            self.assertEqual(result["service_hardening_policy"]["service_count"], 4)
            self.assertTrue(result["service_hardening_policy"]["default_public_off"])
            self.assertTrue(result["service_hardening_stage_marker"]["launcher_marker_present"])
            self.assertTrue(result["hud_split_stage_marker"]["intent_producer_marker_present"])
            self.assertTrue(result["hud_split_stage_marker"]["presenter_marker_present"])
            self.assertTrue(result["hud_split_stage_marker"]["direct_kms_disabled_marker_present"])
            self.assertTrue((target / wsta3.TARGET_SERVICE_LAUNCHER).is_file())
            self.assertTrue((target / wsta3.TARGET_SERVICE_HARDENING_POLICY).is_file())
            self.assertTrue((target / wsta3.TARGET_NATIVE_WIFI_SERVICE_CLIENT).is_file())
            self.assertTrue((target / wsta3.TARGET_NATIVE_WIFI_UPLINK_CLIENT).is_file())
            self.assertTrue((target / wsta3.TARGET_NATIVE_UPLINK_PROFILE).is_file())
            self.assertTrue((target / wsta3.TARGET_PACKET_FILTER).is_file())
            self.assertIn(
                "service-hardening-launcher=/usr/local/bin/a90-service-launch",
                (target / wsta3.TARGET_STAGE_MARKER).read_text(encoding="utf-8"),
            )
            self.assertIn(
                "native-uplink-profile=/usr/local/bin/a90-dpublic-native-uplink-profile",
                (target / wsta3.TARGET_STAGE_MARKER).read_text(encoding="utf-8"),
            )
            self.assertIn(
                "packet-filter-backend=legacy-iptables",
                (target / wsta3.TARGET_STAGE_MARKER).read_text(encoding="utf-8"),
            )
            self.assertIn(
                "packet-filter-helper=/usr/local/bin/a90-dpublic-packet-filter",
                (target / wsta3.TARGET_STAGE_MARKER).read_text(encoding="utf-8"),
            )
            self.assertIn(
                "syscall-trace-profile-source=deferred-WSTA114",
                (target / wsta3.TARGET_STAGE_MARKER).read_text(encoding="utf-8"),
            )
            self.assertIn(
                "hud-split-intent-producer=/usr/local/bin/a90-dpublic-hud-intent",
                (target / wsta3.TARGET_STAGE_MARKER).read_text(encoding="utf-8"),
            )
            self.assertIn(
                "hud-split-direct-kms-for-a90hud=disabled",
                (target / wsta3.TARGET_STAGE_MARKER).read_text(encoding="utf-8"),
            )
            self.assertFalse(result["api_probe_tools"]["requested"])
            self.assertTrue(result["firstboot"]["wifi_sta_helper_invoked"])
            self.assertTrue(result["firstboot"]["hud_split_intent_invoked"])
            self.assertTrue(result["firstboot"]["hud_split_presenter_not_started_by_debian"])
            self.assertTrue(result["firstboot"]["legacy_direct_hud_fallback_only"])
            self.assertTrue(result["firstboot"]["autoreboot_disabled_marker"])
            self.assertTrue(result["firstboot"]["native_uplink_profile_marker"])
            self.assertTrue(result["firstboot"]["public_default_off_marker"])
            self.assertFalse(result["dpublic_binaries"]["staged"])
            self.assertFalse(result["quick_tunnel_enable"]["enabled"])
            self.assertEqual(verify.call_count, 2)
            summary = (tmp_path / "run" / "summary.json").read_text(encoding="utf-8")
            self.assertNotIn("Test Net", summary)
            self.assertNotIn("12345678", summary)
            self.assertIn('"sha256_redacted"', summary) if "tarball_result" in result else None

    def test_prepare_immediate_snapshot_only_skips_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source"
            (source / "usr/local/bin").mkdir(parents=True)
            (source / "usr/sbin").mkdir(parents=True)
            (source / "usr/bin").mkdir(parents=True)
            (source / "etc/a90-dpublic").mkdir(parents=True)
            (source / "usr/local/bin/a90-dpublic-wifi-sta").write_text("#!/bin/sh\n", encoding="utf-8")
            (source / "usr/sbin/ip").write_text("", encoding="utf-8")
            (source / "usr/sbin/wpa_supplicant").write_text("", encoding="utf-8")
            (source / "usr/sbin/wpa_cli").write_text("", encoding="utf-8")
            (source / "usr/sbin/dhclient").write_text("", encoding="utf-8")
            (source / "usr/sbin/iw").write_text("", encoding="utf-8")
            (source / "usr/bin/ping").write_text("", encoding="utf-8")
            (source / "usr/bin/getent").write_text("", encoding="utf-8")
            (source / "usr/bin/nc").write_text("", encoding="utf-8")
            stage_packet_filter_test_tools(source)

            with mock.patch.object(wsta3.d4c, "verify_rootfs", return_value={"ok": True}):
                result = wsta3.prepare(
                    make_args(
                        tmp_path,
                        source_rootfs=source,
                        immediate_snapshot_only=True,
                    )
                )

            target = tmp_path / "run" / "rootfs"
            self.assertTrue(result["ok"])
            self.assertEqual(result["config_source"]["type"], "immediate-snapshot-only")
            self.assertFalse(result["stage"]["config_required"])
            self.assertTrue((target / wsta3.TARGET_ENABLE).is_file())
            self.assertTrue((target / wsta3.TARGET_IMMEDIATE_SNAPSHOT_ONLY).is_file())
            self.assertFalse((target / wsta3.TARGET_CONFIG).exists())
            self.assertTrue(result["packet_filter_tools"]["ok"])

    def test_source_does_not_default_to_live_network_actions(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "os.system",
            "dhclient ",
            "wpa_supplicant -B",
            "cloudflared tunnel",
            "iptables -A",
            "iptables -F",
            "ip6tables -A",
            "ip6tables -F",
            "iptables-legacy -A",
            "iptables-legacy -F",
            "ip6tables-legacy -A",
            "ip6tables-legacy -F",
            " ping ",
            "native_init_flash.py",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
