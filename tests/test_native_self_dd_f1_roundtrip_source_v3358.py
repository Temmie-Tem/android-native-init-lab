import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace" / "public" / "src" / "scripts" / "revalidation"))

import build_native_init_boot_v3358_self_dd_f1_roundtrip as runner  # noqa: E402


class NativeSelfDdF1RoundtripSourceV3358Test(unittest.TestCase):
    def test_required_strings_cover_f1_roundtrip_contract(self) -> None:
        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.121", required)
        self.assertIn(b"v3358-self-dd-f1-roundtrip", required)
        self.assertIn(b"A90BWF1", required)
        self.assertIn(
            b"boot-flash-f1 <token> <candidate-path> <expected-sha256> <expected-version>",
            required,
        )
        self.assertIn(b"BOOT-FLASH-F1-PAIRED-ROUNDTRIP", required)
        self.assertIn(b"paired-content-roundtrip", required)
        self.assertIn(b"snapshot_existing=%s refused=preserve-retained-snapshot", required)
        self.assertIn(b"target_full_sha_after=%s target_full_match=%d", required)
        self.assertIn(b"restore_full_sha_after=%s restore_full_match=%d", required)
        self.assertIn(b"result=ok paired-roundtrip-restored", required)

    def test_report_states_live_policy_blocked(self) -> None:
        manifest = {
            "boot_image": "workspace/private/inputs/boot_images/boot_linux_v3358_self_dd_f1_roundtrip.img",
            "boot_sha256": "0" * 64,
            "helper_sha256": "1" * 64,
        }
        report = runner.render_report(manifest, ("flag-a",), ("flag-b",))
        self.assertIn("Decision: `v3358-self-dd-f1-roundtrip-source-build-pass-live-policy-blocked`", report)
        self.assertIn("boot-flash-f1 BOOT-FLASH-F1-PAIRED-ROUNDTRIP", report)
        self.assertIn("live execution remains blocked by the policy gate", report)
        self.assertIn("No live F1 content-changing write is claimed", report)

    def test_f1_registered_as_dangerous(self) -> None:
        dispatch = (
            ROOT
            / "workspace"
            / "public"
            / "src"
            / "native-init"
            / "v319"
            / "80_shell_dispatch.inc.c"
        ).read_text(encoding="utf-8")
        self.assertIn("static int handle_boot_flash_f1", dispatch)
        self.assertIn(
            '{ "boot-flash-f1", handle_boot_flash_f1, '
            '"boot-flash-f1 <token> <candidate-path> <expected-sha256> <expected-version>", '
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
        self.assertIn("int a90_boot_flash_f1_cmd", source)


if __name__ == "__main__":
    unittest.main()
