from __future__ import annotations

import argparse
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
        "stage_dpublic_binaries": False,
        "stage_api_probe_tools": False,
        "enable_quick_tunnel": False,
        "cloudflared": tmp / "cloudflared",
        "smoke_httpd": tmp / "a90-dpublic-smoke-httpd",
        "http_get": tmp / "a90-dpublic-http-get",
        "hud": tmp / "a90-dpublic-hud",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def write_private(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)


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

    def test_stage_native_wifi_uplink_client_is_status_and_no_confirm_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)

            result = wsta3.stage_native_wifi_uplink_client(rootfs)

            target = rootfs / wsta3.TARGET_NATIVE_WIFI_UPLINK_CLIENT
            text = target.read_text(encoding="utf-8")
            self.assertTrue(result["latest_helper_staged"])
            self.assertTrue(result["file_protocol_present"])
            self.assertTrue(result["atomic_request_present"])
            self.assertTrue(result["status_no_confirm_only"])
            self.assertTrue(result["confirmed_autoconnect_denied"])
            self.assertTrue(result["dangerous_ops_denied"])
            self.assertTrue(result["owner_check_present"])
            self.assertTrue(result["version_check_present"])
            self.assertTrue(result["redacted_profile_filter_present"])
            self.assertTrue(result["secret_hygiene_marker"])
            self.assertEqual(target.stat().st_mode & 0o777, 0o755)
            self.assertIn("/tmp/a90-native-wifi-uplink-service", text)
            self.assertIn("native-wifi-uplink-client-op-denied", text)
            self.assertIn("owner\" != \"native-init\"", text)
            self.assertNotIn("ssid=", text.lower())
            self.assertNotIn("psk=", text.lower())

    def test_stage_dpublic_binaries_and_quick_tunnel_enable_are_private(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            rootfs = tmp_path / "rootfs"
            rootfs.mkdir()
            for name in ("cloudflared", "a90-dpublic-smoke-httpd", "a90-dpublic-http-get", "a90-dpublic-hud"):
                (tmp_path / name).write_bytes((name + "\n").encode("utf-8"))
            args = make_args(
                tmp_path,
                cloudflared=tmp_path / "cloudflared",
                smoke_httpd=tmp_path / "a90-dpublic-smoke-httpd",
                http_get=tmp_path / "a90-dpublic-http-get",
                hud=tmp_path / "a90-dpublic-hud",
            )

            binaries = wsta3.stage_dpublic_binaries(rootfs, args)
            enable = wsta3.stage_quick_tunnel_enable(rootfs, True)

            self.assertTrue(binaries["staged"])
            self.assertEqual(binaries["binaries"]["cloudflared"]["mode"], "0o755")
            self.assertTrue((rootfs / "usr/local/bin/cloudflared").is_file())
            self.assertTrue((rootfs / "usr/local/bin/a90-dpublic-smoke-httpd").is_file())
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
            self.assertTrue(result["native_wifi_uplink_client"]["confirmed_autoconnect_denied"])
            self.assertTrue((target / wsta3.TARGET_NATIVE_WIFI_SERVICE_CLIENT).is_file())
            self.assertTrue((target / wsta3.TARGET_NATIVE_WIFI_UPLINK_CLIENT).is_file())
            self.assertFalse(result["api_probe_tools"]["requested"])
            self.assertTrue(result["firstboot"]["wifi_sta_helper_invoked"])
            self.assertTrue(result["firstboot"]["autoreboot_disabled_marker"])
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

    def test_source_does_not_default_to_live_network_actions(self) -> None:
        source = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "os.system",
            "dhclient ",
            "wpa_supplicant -B",
            "cloudflared tunnel",
            " ping ",
            "native_init_flash.py",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
