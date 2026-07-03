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
            "0.11.130",
            args,
        )
        rendered = [str(item) for item in command]
        self.assertIn("workspace/public/src/scripts/revalidation/native_init_flash.py", rendered[1])
        self.assertIn("--from-native", rendered)
        self.assertIn("--expect-sha256", rendered)
        self.assertIn("a" * 64, rendered)
        self.assertIn("--expect-version", rendered)
        self.assertIn("0.11.130", rendered)
        self.assertIn("--verify-protocol", rendered)
        self.assertIn("selftest", rendered)

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


if __name__ == "__main__":
    unittest.main()
