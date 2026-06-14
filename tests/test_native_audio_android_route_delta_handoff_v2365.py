"""Host-only tests for the V2365 Android route-delta planner."""

from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation


v2365 = load_revalidation("native_audio_android_route_delta_handoff_v2365")


def args(**overrides: object) -> argparse.Namespace:
    defaults: dict[str, object] = {
        "stimulus_dex": None,
        "android_timeout": 420.0,
        "duration_ms": 2000,
        "sample_rate": 48000,
        "amplitude": 0.05,
        "from_native": True,
        "approval": None,
        "out_dir": None,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class AndroidRouteDeltaPlanner(unittest.TestCase):
    def test_dry_run_uses_checked_android_flash_target_and_blocks_live_without_stimulus(self) -> None:
        payload = v2365.dry_run_payload(args())

        self.assertTrue(payload["ok"])
        self.assertFalse(payload["live_ready"])
        self.assertIn("--stimulus-dex", " ".join(payload["live_blockers"]))
        flash_command = payload["commands"]["flash_android"]
        self.assertIn("native_init_flash.py", " ".join(flash_command))
        self.assertIn("--post-flash-target", flash_command)
        self.assertIn("android-adb", flash_command)
        self.assertIn("--expect-android-magic", flash_command)
        self.assertIn("--android-root-check", flash_command)

    def test_command_plan_keeps_forbidden_paths_out(self) -> None:
        payload = v2365.dry_run_payload(args())
        flat = json.dumps(payload["commands"], sort_keys=True)

        self.assertTrue(payload["command_safety"]["ok"])
        self.assertNotIn("tinyplay", flat)
        self.assertNotIn(" tinymix set ", flat)
        self.assertNotIn("/dev/snd", flat)
        self.assertNotIn(" dd if=", flat)
        self.assertNotIn("fastboot", flat)
        self.assertIn("app_process", flat)
        self.assertIn("A90AudioRouteStimulus", flat)
        self.assertIn("playback_start_background", payload["commands"])

    def test_android_boot_candidate_requires_sealed_copy_due_archive_mode(self) -> None:
        payload = v2365.dry_run_payload(args())

        self.assertTrue(payload["android_boot"]["ok"])
        self.assertTrue(payload["android_boot"]["sealed_copy_required"])
        selected = payload["android_boot"]["selected"]
        self.assertEqual(selected["sha256"], v2365.ANDROID_BOOT_SHA256)
        self.assertTrue(selected["android_magic"])

    def test_supplied_private_stimulus_dex_can_make_live_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stimulus = Path(temp_dir) / "A90AudioRouteStimulus.dex"
            stimulus.write_bytes(b"dex\n035\0placeholder")
            stimulus.chmod(0o600)
            payload = v2365.dry_run_payload(args(stimulus_dex=stimulus))

        self.assertTrue(payload["stimulus_dex"]["ok"])
        self.assertTrue(payload["live_ready"])
        self.assertEqual(payload["commands"]["stage"][2][-1], v2365.REMOTE_STIMULUS)

    def test_rollback_from_android_does_not_claim_native_bridge_origin(self) -> None:
        payload = v2365.dry_run_payload(args())

        self.assertEqual(payload["commands"]["android_reboot_recovery_for_rollback"], ["adb", "reboot", "recovery"])
        rollback = payload["commands"]["rollback_v2321"]
        self.assertIn("native_init_flash.py", " ".join(rollback))
        self.assertNotIn("--from-native", rollback)

    def test_run_live_requires_exact_approval_phrase(self) -> None:
        namespace = args(
            stimulus_dex=Path("workspace/private/builds/audio/v2366-android-route-stimulus/A90AudioRouteStimulus.dex"),
            approval="exact route-delta approval.",
        )

        with self.assertRaisesRegex(RuntimeError, "exact AUD-3D2 route-delta approval"):
            v2365.ensure_live_approval(namespace)

    def test_exact_approval_phrase_is_accepted_by_gate(self) -> None:
        namespace = args(approval=v2365.APPROVAL_PHRASE)

        v2365.ensure_live_approval(namespace)


if __name__ == "__main__":
    unittest.main()
