import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"))

import build_native_init_boot_v3360_self_dd_f3_self_rollback as runner  # noqa: E402


class NativeSelfDdF3SelfRollbackSourceV3360Test(unittest.TestCase):
    def test_required_strings_cover_f3_self_rollback_contract(self) -> None:
        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.123", required)
        self.assertIn(b"v3360-self-dd-f3-self-rollback", required)
        self.assertIn(b"A90BWF3", required)
        self.assertIn(
            b"boot-flash-f3 <token> <candidate-path> <expected-sha256> <expected-version>",
            required,
        )
        self.assertIn(b"BOOT-FLASH-F3-SELF-ROLLBACK", required)
        self.assertIn(b"self-rollback-write", required)
        self.assertIn(b"target_full_sha_after=%s target_full_match=%d", required)
        self.assertIn(b"restore_skipped=rollback-verified-host-reboot-required", required)
        self.assertIn(b"reboot_required=1 host_must_reboot_now=1", required)
        self.assertIn(b"result=ok rollback-written-ready-to-reboot", required)

    def test_report_states_live_policy_blocked(self) -> None:
        manifest = {
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3360_self_dd_f3_self_rollback.img",
            "boot_sha256": "0" * 64,
            "helper_sha256": "1" * 64,
        }
        report = runner.render_report(manifest, ("flag-a",), ("flag-b",))
        self.assertIn("Decision: `v3360-self-dd-f3-self-rollback-source-build-pass-live-policy-blocked`", report)
        self.assertIn("boot-flash-f3 BOOT-FLASH-F3-SELF-ROLLBACK", report)
        self.assertIn("live execution remains blocked by the F3 policy gate", report)
        self.assertIn("No live F3 self-rollback write", report)

    def test_f3_registered_as_dangerous(self) -> None:
        dispatch = (
            ROOT
            / "workspace"
            / "public"
            / "src"
            / "native-init"
            / "v319"
            / "80_shell_dispatch.inc.c"
        ).read_text(encoding="utf-8")
        self.assertIn("static int handle_boot_flash_f3", dispatch)
        self.assertIn(
            '{ "boot-flash-f3", handle_boot_flash_f3, '
            '"boot-flash-f3 <token> <candidate-path> <expected-sha256> <expected-version>", '
            "CMD_DANGEROUS",
            dispatch,
        )

    def test_boot_pwrite_call_site_stays_single_wrapper(self) -> None:
        source = (
            ROOT
            / "workspace"
            / "public"
            / "src"
            / "native-init"
            / "a90_boot_write_e1.c"
        ).read_text(encoding="utf-8")
        self.assertEqual(source.count("pwrite(fd, len"), 0)
        self.assertEqual(source.count("pwrite(fd, buf, len"), 1)
        self.assertIn("static int e_pwrite_exact", source)
        self.assertIn("int a90_boot_flash_f2_cmd", source)
        self.assertIn("int a90_boot_flash_f3_cmd", source)
        self.assertIn("F3_LEAVE_TARGET_SPEC", source)


if __name__ == "__main__":
    unittest.main()
