"""Host-only tests for the V2420 dynamic-M0 ACDB capture handoff."""

from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2420 = load_revalidation("native_audio_acdb_payload_capture_dynamic_live_handoff_v2420")


def args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "materialize_capture_helper": False,
        "helper_out_dir": v2420.v2415.DEFAULT_HELPER_OUT_DIR,
        "cc": v2420.v2415.DEFAULT_CC,
        "stimulus_apk": v2420.v2396.DEFAULT_STIMULUS_APK,
        "adb": "adb",
        "serial": None,
        "android_timeout": 420.0,
        "adb_command_timeout": 120.0,
        "flash_timeout": 900.0,
        "duration_ms": v2420.v2396.DEFAULT_DURATION_MS,
        "sample_rate": v2420.v2396.DEFAULT_SAMPLE_RATE,
        "amplitude": v2420.v2396.DEFAULT_AMPLITUDE,
        "active_delay_sec": 0.75,
        "post_delay_sec": 1.0,
        "capture_duration_sec": v2420.v2415.DEFAULT_DURATION_SEC,
        "capture_warmup_sec": v2420.v2416.DEFAULT_CAPTURE_WARMUP_SEC,
        "max_bytes": v2420.v2415.DEFAULT_MAX_BYTES,
        "from_native": True,
        "approval": None,
        "out_dir": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class AcdbDynamicM0LiveHandoff(unittest.TestCase):
    def test_dry_run_declares_v2420_dynamic_m0(self) -> None:
        payload = v2420.dry_run(args())

        self.assertEqual(payload["run_id"], "V2420")
        self.assertEqual(payload["decision"], "v2420-acdb-dynamic-m0-capture-live-dry-run")
        self.assertTrue(payload["dynamic_m0_task_watcher"])
        self.assertEqual(payload["approval_phrase_required_for_live"], v2420.APPROVAL_PHRASE)
        self.assertEqual(payload["capture_contract"]["task_watcher"]["mode"], "dynamic-polling")
        self.assertEqual(
            payload["magisk_module_escalation"],
            "clone-following-m0-before-m1-temporary-boot-module",
        )

    def test_rewrite_payload_identity_preserves_summary_and_relabels_decision(self) -> None:
        payload = {
            "run_id": "V2416",
            "build_tag": "old",
            "decision": "v2416-acdb-payload-capture-events-before-rollback-rollback-pass",
            "payload_capture_summary": {"classification": "captured-msm-audio-cal-payload-events"},
        }

        rewritten = v2420.rewrite_payload_identity(payload)

        self.assertEqual(rewritten["run_id"], "V2420")
        self.assertEqual(rewritten["build_tag"], "v2420-audio-acdb-dynamic-m0-live")
        self.assertEqual(rewritten["decision"], "v2420-acdb-dynamic-m0-capture-events-before-rollback-rollback-pass")
        self.assertTrue(rewritten["dynamic_m0_task_watcher"])
        self.assertEqual(rewritten["v2419_observer_fix"]["dedupe_file"], "seen-tids.txt")

    def test_run_live_sets_v2420_out_dir_before_delegating(self) -> None:
        original_run_live = v2420.v2416.run_live

        def fake_run_live(namespace: argparse.Namespace) -> dict[str, object]:
            self.assertIsNotNone(namespace.out_dir)
            out_dir = Path(namespace.out_dir)
            self.assertIn("v2420-acdb-dynamic-m0-capture", str(out_dir))
            out_dir.mkdir(parents=True)
            (out_dir / "result.json").write_text("{}\n")
            return {
                "run_id": "V2416",
                "build_tag": "old",
                "decision": "v2416-acdb-payload-capture-no-msm-audio-cal-ioctl-observed-before-rollback-rollback-pass",
                "out_dir": v2420.rel(out_dir),
                "ok": True,
                "rolled_back": True,
            }

        v2420.v2416.run_live = fake_run_live
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                payload = v2420.run_live(args(out_dir=Path(temp_dir) / "v2420-acdb-dynamic-m0-capture-test"))
                saved = (Path(temp_dir) / "v2420-acdb-dynamic-m0-capture-test" / "result.json").read_text()
        finally:
            v2420.v2416.run_live = original_run_live

        self.assertEqual(payload["run_id"], "V2420")
        self.assertIn("dynamic-m0", payload["decision"])
        self.assertIn('"run_id": "V2420"', saved)


if __name__ == "__main__":
    unittest.main()
