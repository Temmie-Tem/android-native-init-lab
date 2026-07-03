"""Regression tests for V3370 server-distro D3B switch_root source build."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


builder = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3370_server_distro_switchroot_loopfix.py"
)


class BuildNativeInitBootV3370ServerDistroSwitchrootTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3370")
        self.assertEqual(builder.INIT_VERSION, "0.11.131")
        self.assertEqual(builder.INIT_BUILD, "v3370-server-distro-switchroot-loopfix")
        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"switch-root-to-distro",
            b"SERVER-DISTRO-D3B-SWITCHROOT",
            b"A90D3B",
            b"/mnt/sdext/a90/runtime/",
            b"/mnt/sdext/a90/runtime/distro-root",
            b"loop_node_created=1",
            b"exec_switch_root_now",
            b"expected_sha_match=1",
        ):
            self.assertIn(marker, required)

    def test_switchroot_module_is_gated_sd_only_and_execs_switch_root(self) -> None:
        source = Path("workspace/public/src/native-init/a90_server_distro.c").read_text(encoding="utf-8")
        self.assertIn('#define A90_D3_TOKEN "SERVER-DISTRO-D3B-SWITCHROOT"', source)
        self.assertIn('#define A90_D3_ALLOWED_IMAGE_ROOT "/mnt/sdext/a90/runtime/"', source)
        self.assertIn('#define A90_D3_ROOT "/mnt/sdext/a90/runtime/distro-root"', source)
        self.assertIn("while (fgets(line, sizeof(line), fp) != NULL)", source)
        self.assertIn('sscanf(line, " %u %63s", &major_num, name) != 2', source)
        self.assertIn("a90_helper_sha256_file(image, actual_sha", source)
        self.assertIn('expected_sha_match=1', source)
        self.assertIn('"switch_root"', source)
        self.assertIn('execve(A90_D3_BUSYBOX, switch_argv, newenv);', source)
        self.assertIn("MS_MOVE", source)
        for forbidden in ("/data", "userdata", "/dev/block/by-name/userdata"):
            self.assertNotIn(forbidden, source)

    def test_command_table_registers_no_done_dangerous_handoff(self) -> None:
        dispatch = Path("workspace/public/src/native-init/v319/80_shell_dispatch.inc.c").read_text(
            encoding="utf-8"
        )
        self.assertIn("static int handle_switch_root_to_distro", dispatch)
        self.assertIn("stop_auto_hud(false);", dispatch)
        self.assertIn("a90_server_distro_switch_root_cmd(argv, argc);", dispatch)
        self.assertIn(
            '{ "switch-root-to-distro", handle_switch_root_to_distro,',
            dispatch,
        )
        self.assertIn("CMD_DANGEROUS | CMD_NO_DONE, A90_CMD_GROUP_POWER", dispatch)


if __name__ == "__main__":
    unittest.main()
