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
        "no_tarball": True,
        "tar_timeout": 10.0,
        "apt_work": tmp / "apt",
        "suite": "bookworm",
        "arch": "arm64",
        "mirror": "http://deb.debian.org/debian",
        "apt_timeout": 10.0,
        "no_sta_tool_install": True,
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

    def test_sta_tools_missing_blocks_when_install_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp) / "rootfs"
            rootfs.mkdir()
            args = make_args(Path(tmp), no_sta_tool_install=True)

            result = wsta3.ensure_sta_tools(rootfs, args)

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "sta-tools-missing-install-disabled")
        self.assertFalse(result["before"]["tools"]["wpa_supplicant"]["present"])
        self.assertFalse(result["before"]["tools"]["dhclient"]["present"])
        self.assertFalse(result["before"]["tools"]["nc"]["present"])

    def test_ensure_sta_tools_restores_usrmerge_when_tools_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp) / "rootfs"
            (rootfs / "usr/sbin").mkdir(parents=True)
            (rootfs / "usr/bin").mkdir(parents=True)
            (rootfs / "usr/lib").mkdir(parents=True)
            (rootfs / "sbin").mkdir()
            (rootfs / "sbin/wpa_supplicant").write_text("", encoding="utf-8")
            (rootfs / "sbin/dhclient").write_text("", encoding="utf-8")
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
            self.assertTrue((rootfs / "usr/sbin/dhclient").is_file())

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
            (source / "usr/sbin/dhclient").write_text("", encoding="utf-8")
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
            self.assertTrue(result["firstboot"]["wifi_sta_helper_invoked"])
            self.assertTrue(result["firstboot"]["autoreboot_disabled_marker"])
            self.assertEqual(verify.call_count, 2)
            summary = (tmp_path / "run" / "summary.json").read_text(encoding="utf-8")
            self.assertNotIn("Test Net", summary)
            self.assertNotIn("12345678", summary)
            self.assertIn('"sha256_redacted"', summary) if "tarball_result" in result else None

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
