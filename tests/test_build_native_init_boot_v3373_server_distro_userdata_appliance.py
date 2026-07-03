"""Regression tests for V3373 server-distro D4B userdata appliance source build."""

from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


builder = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3373_server_distro_userdata_appliance.py"
)


class BuildNativeInitBootV3373ServerDistroUserdataApplianceTests(unittest.TestCase):
    def test_builder_identity_and_required_markers(self) -> None:
        self.assertEqual(builder.CYCLE, "V3373")
        self.assertEqual(builder.INIT_VERSION, "0.11.134")
        self.assertEqual(builder.INIT_BUILD, "v3373-server-distro-userdata-appliance")
        required = b"\n".join(builder.REQUIRED_STRINGS)
        for marker in (
            b"userdata-appliance-preflight",
            b"userdata-appliance-format",
            b"userdata-appliance-populate",
            b"switch-root-to-userdata",
            b"SERVER-DISTRO-D4-USERDATA-APPLIANCE",
            b"A90D4",
            b"/sys/class/block",
            b"PARTNAME=",
            b"/dev/block/a90-userdata",
            b"/mnt/a90-userdata-root",
            b"busybox-mke2fs-ext4",
            b"userdata=appliance-root",
            b"target.source=partname-scan",
            b"format=done",
            b"populate=done",
        ):
            self.assertIn(marker, required)

    def test_userdata_surface_is_token_gated_and_partname_derived(self) -> None:
        source = Path("workspace/public/src/native-init/a90_server_distro.c").read_text(encoding="utf-8")
        self.assertIn('#define A90_D4_TOKEN "SERVER-DISTRO-D4-USERDATA-APPLIANCE"', source)
        self.assertIn('#define A90_D4_NODE "/dev/block/a90-userdata"', source)
        self.assertIn('#define A90_D4_ROOT "/mnt/a90-userdata-root"', source)
        self.assertIn('#define A90_D4_EXPECTED_PARTNAME "userdata"', source)
        self.assertIn('opendir("/sys/class/block")', source)
        self.assertIn('strncmp(line, "PARTNAME=", 9) == 0', source)
        self.assertIn('strcmp(partname, A90_D4_EXPECTED_PARTNAME) != 0', source)
        self.assertIn("found_count != 1", source)
        self.assertIn("d4_check_optional_byname(&found)", source)
        self.assertIn("d4_check_private_node(&found)", source)
        self.assertIn("d4_target_is_mounted(&found)", source)
        self.assertIn("d4_compare_expected(&target, argv[2], argv[3], argv[4])", source)
        self.assertIn("mknod(A90_D4_NODE, S_IFBLK | 0600, wanted)", source)
        self.assertIn("formatter=e2fsprogs-mkfs.ext4", source)
        self.assertNotIn("formatter=busybox-mke2fs", source)
        self.assertIn('#define A90_D4_E2FS_TOOLROOT "/mnt/sdext/a90/runtime/d4c-format-toolroot"', source)
        self.assertIn("d4_verify_e2fs_toolroot()", source)
        self.assertIn("d4_check_ext_has_journal(A90_D4_NODE, \"format\")", source)
        self.assertIn("a90_helper_sha256_file(source_tar, actual_sha", source)
        self.assertIn("d4_source_path_clean(source_tar)", source)
        self.assertIn("d4_regular_file_ok(source_tar)", source)
        self.assertIn("d4_write_marker()", source)
        self.assertIn("d4_read_marker(actual_marker", source)
        self.assertIn("execve(A90_D4_BUSYBOX, switch_argv, newenv);", source)

    def test_userdata_surface_keeps_forbidden_partition_deny_list(self) -> None:
        source = Path("workspace/public/src/native-init/a90_server_distro.c").read_text(encoding="utf-8")
        for forbidden in (
            '"efs"',
            '"sec_efs"',
            '"modem"',
            '"rpmb"',
            '"keymaster"',
            '"vbmeta"',
            '"dsp"',
            '"keydata"',
            '"keyrefuge"',
            '"bootloader"',
            '"persist"',
            '"gpt"',
        ):
            self.assertIn(forbidden, source)
        self.assertIn("d4_has_forbidden_name(found.sysname)", source)
        self.assertIn("d4_has_forbidden_name(found.devname)", source)

    def test_command_table_registers_d4_surface_with_expected_risk_flags(self) -> None:
        dispatch = Path("workspace/public/src/native-init/v319/80_shell_dispatch.inc.c").read_text(
            encoding="utf-8"
        )
        for handler in (
            "handle_userdata_appliance_preflight",
            "handle_userdata_appliance_format",
            "handle_userdata_appliance_populate",
            "handle_switch_root_to_userdata",
        ):
            self.assertIn(f"static int {handler}", dispatch)
        self.assertIn(
            '{ "userdata-appliance-preflight", handle_userdata_appliance_preflight,',
            dispatch,
        )
        self.assertIn("CMD_NONE, A90_CMD_GROUP_STORAGE", dispatch)
        self.assertIn(
            '{ "userdata-appliance-format", handle_userdata_appliance_format,',
            dispatch,
        )
        self.assertIn(
            '{ "userdata-appliance-populate", handle_userdata_appliance_populate,',
            dispatch,
        )
        self.assertIn("CMD_DANGEROUS, A90_CMD_GROUP_STORAGE", dispatch)
        self.assertIn(
            '{ "switch-root-to-userdata", handle_switch_root_to_userdata,',
            dispatch,
        )
        self.assertIn("CMD_DANGEROUS | CMD_NO_DONE, A90_CMD_GROUP_POWER", dispatch)
        self.assertIn("a90_server_distro_userdata_preflight_cmd(argv, argc);", dispatch)
        self.assertIn("a90_server_distro_userdata_format_cmd(argv, argc);", dispatch)
        self.assertIn("a90_server_distro_userdata_populate_cmd(argv, argc);", dispatch)
        self.assertIn("a90_server_distro_switch_root_userdata_cmd(argv, argc);", dispatch)


if __name__ == "__main__":
    unittest.main()
