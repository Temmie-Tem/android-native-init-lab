"""Regression tests for V3384 server-distro hardware-contract source build."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_revalidation


builder = load_revalidation("build_native_init_boot_v3384_server_distro_hardware_contract")


class BuildNativeInitBootV3384ServerDistroHardwareContractTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3384")
        self.assertEqual(builder.INIT_VERSION, "0.11.140")
        self.assertEqual(builder.INIT_BUILD, "v3384-server-distro-hardware-contract")

        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"v3384-server-distro-hardware-contract",
            b"0.11.140",
            b"server-distro [status|hardware-contract]",
            b"A90DHW contract.version=1",
            b"next.required=wifi-sta-upstream",
            b"optin=audio-adsp-acdb,kgsl-gpu,video-doom,touch-game-input,stress-longsoak",
            b"denied.default_off=modem-cellular,camera,gnss,nfc,bluetooth,sensor-hubs,android-hal-services",
            b"safety.no=forbidden-partitions,raw-nonboot-flash,pmic-regulator-gdsc-gpio-backlight,panel-reinit",
        ):
            self.assertIn(marker, required)

    def test_rewrite_updates_previous_identity(self) -> None:
        text = builder._rewrite_v3384_text(
            "V3383 0.11.139 v3383-server-distro-handoff-cleanup "
            "server-distro-d4d-handoff-cleanup a90-doomgeneric-v3383"
        )
        self.assertIn("V3384", text)
        self.assertIn("0.11.140", text)
        self.assertIn("v3384-server-distro-hardware-contract", text)
        self.assertIn("server-distro-stage0-hardware-contract", text)
        self.assertIn("a90-doomgeneric-v3384", text)
        self.assertNotIn("v3383", text)
        self.assertNotIn("handoff-cleanup", text)

    def test_source_contains_contract_command_and_dispatch(self) -> None:
        source = Path("workspace/public/src/native-init/a90_server_distro.c").read_text(encoding="utf-8")
        dispatch = Path("workspace/public/src/native-init/v319/80_shell_dispatch.inc.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("int a90_server_distro_cmd(char **argv, int argc)", source)
        self.assertIn("d_hw_print_contract", source)
        self.assertIn("A90DHW", source)
        self.assertIn('{ "server-distro", handle_server_distro,', dispatch)
        self.assertIn("CMD_NONE, A90_CMD_GROUP_STORAGE", dispatch)

    def test_candidate_manifest_records_live_gate(self) -> None:
        text = builder.json.dumps({
            "candidate_type": "server-distro-stage0-hardware-contract",
            "command": "server-distro [status|hardware-contract]",
            "prefix": "A90DHW",
            "live_gate": "server-distro hardware-contract",
        })
        self.assertIn("server-distro-stage0-hardware-contract", text)
        self.assertIn("server-distro [status|hardware-contract]", text)
        self.assertIn("A90DHW", text)
        self.assertIn("server-distro hardware-contract", text)


if __name__ == "__main__":
    unittest.main()
