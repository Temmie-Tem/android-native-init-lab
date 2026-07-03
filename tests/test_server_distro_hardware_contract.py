"""Static checks for the server-distro Stage0 hardware-contract command."""

from __future__ import annotations

import unittest
from pathlib import Path


SERVER_DISTRO_C = Path("workspace/public/src/native-init/a90_server_distro.c")
SERVER_DISTRO_H = Path("workspace/public/src/native-init/a90_server_distro.h")
DISPATCH = Path("workspace/public/src/native-init/v319/80_shell_dispatch.inc.c")


class ServerDistroHardwareContractTests(unittest.TestCase):
    def test_contract_command_exports_expected_lines(self) -> None:
        source = SERVER_DISTRO_C.read_text(encoding="utf-8")
        for marker in (
            "A90DHW",
            "contract.version=1",
            "SERVER_DISTRO_STAGE0_HARDWARE_CONTRACT_2026-07-04.md",
            "default.active=boot-control,usb-acm-ncm,storage-rootfs-handoff,drm-kms-boot-hud-release,health-status",
            "default.drm_kms=optional-boot-hud release_rule=stop-autohud-and-native-init-drm-owners-before-switch_root",
            "next.required=wifi-sta-upstream",
            "next.wifi_sta=native-wlan0-materialization,debian-ip-route-tunnel",
            "optin=audio-adsp-acdb,kgsl-gpu,video-doom,touch-game-input,stress-longsoak",
            "denied.default_off=modem-cellular,camera,gnss,nfc,bluetooth,sensor-hubs,android-hal-services",
            "public_tunnel.owner=debian native=off inbound_public_ports=0",
            "safety.no=forbidden-partitions,raw-nonboot-flash,pmic-regulator-gdsc-gpio-backlight,panel-reinit",
        ):
            self.assertIn(marker, source)

    def test_contract_command_is_read_only_and_registered(self) -> None:
        header = SERVER_DISTRO_H.read_text(encoding="utf-8")
        dispatch = DISPATCH.read_text(encoding="utf-8")
        self.assertIn("int a90_server_distro_cmd(char **argv, int argc);", header)
        self.assertIn("static int handle_server_distro(char **argv, int argc)", dispatch)
        self.assertIn("return a90_server_distro_cmd(argv, argc);", dispatch)
        self.assertIn('{ "server-distro", handle_server_distro,', dispatch)
        self.assertIn('"server-distro [status|hardware-contract]"', dispatch)

        registration = dispatch[
            dispatch.index('{ "server-distro", handle_server_distro,') :
            dispatch.index('{ "switch-root-to-distro"', dispatch.index('{ "server-distro", handle_server_distro,'))
        ]
        self.assertIn("CMD_NONE", registration)
        self.assertIn("A90_CMD_GROUP_STORAGE", registration)
        self.assertNotIn("CMD_DANGEROUS", registration)
        self.assertNotIn("CMD_NO_DONE", registration)

    def test_command_accepts_status_alias_and_rejects_unknown_modes(self) -> None:
        source = SERVER_DISTRO_C.read_text(encoding="utf-8")
        self.assertIn('mode = "status";', source)
        self.assertIn('strcmp(mode, "status") == 0', source)
        self.assertIn('strcmp(mode, "hardware-contract") == 0', source)
        self.assertIn("refused=unknown-mode", source)
        self.assertIn("usage: server-distro [status|hardware-contract]", source)


if __name__ == "__main__":
    unittest.main()
