"""Static contract tests for the D3B switch_root live runner."""

from __future__ import annotations

import types
import unittest
from pathlib import Path

from _loader import load_script


d3b = load_script("workspace/public/src/scripts/server-distro/run_d3_switchroot_handoff.py")


class ServerDistroD3SwitchrootHandoffTests(unittest.TestCase):
    def test_required_timeline_events_are_single_events_schema(self) -> None:
        self.assertEqual(
            d3b.REQUIRED_TIMELINE_EVENTS,
            (
                "candidate_flash_start",
                "candidate_flash_done",
                "candidate_boot_ready",
                "live_session_start",
                "live_session_end",
                "rollback_flash_start",
                "rollback_flash_done",
                "rollback_boot_ready",
            ),
        )

    def test_flash_command_uses_checked_helper_and_pinned_expectations(self) -> None:
        args = types.SimpleNamespace(
            host="127.0.0.1",
            port=54321,
            flash_bridge_timeout=180.0,
            flash_reboot_timeout=180.0,
        )
        command = d3b.flash_command(
            Path("candidate.img"),
            "a" * 64,
            d3b.EXPECTED_CANDIDATE_VERSION,
            args,
        )
        rendered = [str(item) for item in command]
        self.assertIn("workspace/public/src/scripts/revalidation/native_init_flash.py", rendered[1])
        self.assertIn("--from-native", rendered)
        self.assertIn("--expect-sha256", rendered)
        self.assertIn("a" * 64, rendered)
        self.assertIn("--expect-version", rendered)
        self.assertIn("0.11.133", rendered)
        self.assertIn("--verify-protocol", rendered)
        self.assertIn("selftest", rendered)

    def test_default_candidate_is_pinned_v3372_stdio_image(self) -> None:
        self.assertTrue(str(d3b.DEFAULT_CANDIDATE_BOOT).endswith(
            "boot_linux_v3372_server_distro_switchroot_stdio.img"
        ))
        self.assertEqual(
            d3b.EXPECTED_CANDIDATE_SHA256,
            "09db071ae6bebe538d0f9c6c62f6e86b28a4b1a2a6954f1910f8d189675cc653",
        )
        self.assertEqual(d3b.EXPECTED_CANDIDATE_VERSION, "0.11.133")
        self.assertEqual(d3b.EXPECTED_CANDIDATE_BUILD, "v3372-server-distro-switchroot-stdio")

    def test_default_d3_source_is_usrmerge_fixed_image(self) -> None:
        self.assertTrue(str(d3b.DEFAULT_D3_SOURCE_IMAGE).endswith(
            "d3-sysvinit-usrmerge-20260703T101657Z.img"
        ))
        self.assertEqual(
            d3b.EXPECTED_D3_SOURCE_SHA256,
            "6f1960eb4332e1a22d5da1c98e990352c58d80157fbe6286b53ec9fe8ebe59f7",
        )

    def test_runner_contract_uses_switchroot_token_and_avoids_raw_flash_paths(self) -> None:
        source = Path("workspace/public/src/scripts/server-distro/run_d3_switchroot_handoff.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("switch-root-to-distro", source)
        self.assertIn("SERVER-DISTRO-D3B-SWITCHROOT", source)
        self.assertIn("exec_switch_root_now", source)
        self.assertIn("A90D3_MARKER", source)
        for forbidden in (" fastboot ", " of=/dev/block", " by-name/userdata", "mkfs.ext4"):
            self.assertNotIn(forbidden, source)

    def test_staging_defaults_match_d1_d2_and_cancel_foreground_run_before_rollback(self) -> None:
        source = Path("workspace/public/src/scripts/server-distro/run_d3_switchroot_handoff.py").read_text(
            encoding="utf-8"
        )
        self.assertEqual(d3b.DEFAULT_TRANSFER_DELAY, 2.0)
        self.assertIn("default=DEFAULT_TRANSFER_DELAY", source)
        self.assertIn("def cancel_foreground_run", source)
        self.assertIn("cancel_foreground_run_after_stage_error", source)
        self.assertIn('sock.sendall(b"q\\n")', source)

    def test_runner_prestages_sd_image_before_candidate_flash(self) -> None:
        source = Path("workspace/public/src/scripts/server-distro/run_d3_switchroot_handoff.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('save_step("prestage_keyed_image"', source)
        self.assertIn('save_step("prestage_remote_image_sha"', source)
        self.assertIn("pre-staged D3 image sha mismatch", source)
        run_live_source = source[source.index("def run_live"):]
        self.assertLess(run_live_source.index('save_step("prestage_keyed_image"'), run_live_source.index('"candidate_flash"'))
        self.assertLess(run_live_source.index('save_step("remote_image_sha"'), run_live_source.index('run_switch_root_command'))

    def test_post_flash_remote_sha_hides_auto_menu_and_retries(self) -> None:
        source = Path("workspace/public/src/scripts/server-distro/run_d3_switchroot_handoff.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("def hide_auto_menu", source)
        self.assertIn("def remote_image_sha_with_hide_retry", source)
        self.assertIn('"hide"', source)
        self.assertIn('record.get("status") != "busy"', source)
        self.assertIn("expected in text.lower()", source)
        self.assertIn('remote_image_sha_with_hide_retry(args, str(keyed["keyed_sha256"]))', source)

    def test_error_path_closes_live_session_before_rollback(self) -> None:
        source = Path("workspace/public/src/scripts/server-distro/run_d3_switchroot_handoff.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('if "live_session_start" in event_names and "live_session_end" not in event_names:', source)
        self.assertIn('add_event(events, run_dir, "live_session_end")', source)


if __name__ == "__main__":
    unittest.main()
