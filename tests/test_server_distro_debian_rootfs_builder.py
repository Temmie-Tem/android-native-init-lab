from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _loader import load_script


builder = load_script("workspace/public/src/scripts/server-distro/build_debian_aarch64_rootfs.py")


class ServerDistroDebianRootfsBuilderTests(unittest.TestCase):
    def test_rootfs_package_set_includes_debian_sta_client_tools(self) -> None:
        packages = set(builder.INCLUDE_PKGS.split(","))

        self.assertIn("wpasupplicant", packages)
        self.assertIn("isc-dhcp-client", packages)
        self.assertIn("iproute2", packages)
        self.assertIn("iputils-ping", packages)
        self.assertIn("netcat-openbsd", packages)
        self.assertIn("ca-certificates", packages)
        self.assertNotIn("network-manager", packages)

    def test_stage_server_distro_helpers_installs_wifi_sta_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)

            builder.stage_server_distro_helpers(rootfs)

            helper = rootfs / builder.DPUBLIC_WIFI_STA_TARGET
            native_client = rootfs / builder.NATIVE_WIFI_SERVICE_CLIENT_TARGET
            uplink_client = rootfs / builder.NATIVE_WIFI_UPLINK_CLIENT_TARGET
            uplink_profile = rootfs / builder.DPUBLIC_NATIVE_UPLINK_PROFILE_TARGET
            self.assertTrue(helper.is_file())
            self.assertEqual(helper.stat().st_mode & 0o777, 0o755)
            self.assertIn("wifi_sta_secret_values_logged=0", helper.read_text(encoding="utf-8"))
            self.assertTrue(native_client.is_file())
            self.assertEqual(native_client.stat().st_mode & 0o777, 0o755)
            self.assertIn(
                "native_wifi_service_client_secret_values_logged=0",
                native_client.read_text(encoding="utf-8"),
            )
            self.assertTrue(uplink_client.is_file())
            self.assertEqual(uplink_client.stat().st_mode & 0o777, 0o755)
            self.assertIn(
                "native_wifi_uplink_client_secret_values_logged=0",
                uplink_client.read_text(encoding="utf-8"),
            )
            self.assertTrue(uplink_profile.is_file())
            self.assertEqual(uplink_profile.stat().st_mode & 0o777, 0o755)
            self.assertIn(
                "native_uplink_profile_public_default=off",
                uplink_profile.read_text(encoding="utf-8"),
            )
            self.assertTrue((rootfs / "etc/a90-dpublic").is_dir())

    def test_stage_customize_records_wifi_sta_as_private_opt_in(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rootfs = Path(tmp)
            (rootfs / "etc").mkdir()

            def fake_chroot_run(_rootfs: Path, _script: str) -> None:
                self.assertEqual(_rootfs, rootfs)

            original = builder.chroot_run
            builder.chroot_run = fake_chroot_run
            try:
                builder.stage_customize(rootfs, "a90-test")
            finally:
                builder.chroot_run = original

            marker = (rootfs / "etc/a90-server-distro-stage").read_text(encoding="utf-8")
            self.assertIn("wifi-sta=opt-in via /etc/a90-dpublic/wifi-sta-enable", marker)
            self.assertIn("private config not included", marker)
            self.assertIn("wifi-sta-helper=/usr/local/bin/a90-dpublic-wifi-sta", marker)
            self.assertIn("native-wifi-service-client=/usr/local/bin/a90-native-wifi-service-client", marker)
            self.assertIn("native-wifi-uplink-client=/usr/local/bin/a90-native-wifi-uplink-client", marker)
            self.assertIn("native-uplink-profile=/usr/local/bin/a90-dpublic-native-uplink-profile", marker)
            self.assertIn("native-uplink=operator-controlled via /etc/a90-dpublic/native-uplink-enable", marker)
            self.assertIn("public-exposure-default=off", marker)
            self.assertIn("WARNING: configure credentials/keys before any network/public exposure", marker)


if __name__ == "__main__":
    unittest.main()
