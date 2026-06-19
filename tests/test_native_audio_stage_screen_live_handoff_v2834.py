"""Tests for V2834 audio stage screen live handoff wrapper."""

from __future__ import annotations

import importlib
import tempfile
from pathlib import Path
import unittest

v2834 = importlib.import_module("native_audio_stage_screen_live_handoff_v2834")


class NativeAudioStageScreenLiveHandoffV2834Test(unittest.TestCase):
    def test_wrapper_targets_v2833_stage_screen_candidate(self) -> None:
        self.assertEqual(v2834.CYCLE, "V2834")
        self.assertEqual(v2834.CANDIDATE_VERSION, "0.10.8")
        self.assertEqual(v2834.CANDIDATE_TAG, "v2833-audio-stage-screen")
        self.assertIn("v2833-audio-stage-screen", str(v2834.BUILD_MANIFEST))
        self.assertIn("boot_linux_v2833_audio_stage_screen.img", str(v2834.CANDIDATE_IMAGE))

    def test_screenapp_stage_markers_are_required(self) -> None:
        self.assertEqual(v2834.SCREENAPP_COMMAND, ["screenapp", "audio-stages"])
        markers = v2834.REQUIRED_SCREENAPP_MARKERS
        self.assertIn("screenapp.app=audio-stages", markers)
        self.assertIn("screenapp.title=AUDIO STAGES", markers)
        self.assertIn("screenapp.presented=1", markers)

    def test_report_names_read_only_stage_validation(self) -> None:
        rendered = v2834.render_report({
            "decision": "v2834-test",
            "out_dir": "workspace/private/runs/audio/test",
            "candidate_sha256": "b" * 64,
            "candidate_version_ok": True,
            "rollback_attempted": True,
            "rollback_recovery_fallback_used": False,
            "rollback_version_ok": True,
            "rollback_selftest_fail0": True,
            "audio_status_markers": {"ok": True, "count": 16, "required": 16, "missing": []},
            "selftest_markers": {"ok": True, "count": 8, "required": 8, "missing": []},
            "screenapp_markers": {"ok": True, "count": 6, "required": 6, "missing": []},
        })
        self.assertIn("screenapp audio-stages", rendered)
        self.assertIn("display-only", rendered)
        self.assertIn("no ADSP boot", rendered)
        self.assertIn("Rollback health", rendered)

    def test_marker_collection_retries_partial_serial_transcript(self) -> None:
        calls: list[str] = []
        old_run_serial_step = v2834.runner.base.run_serial_step

        def fake_run_serial_step(out_dir, steps, name, command, *, timeout, retry_unsafe=True):
            calls.append(name)
            text = "marker-a only" if len(calls) == 1 else "marker-a marker-b"
            stdout_path = out_dir / f"{len(steps):02d}_{name}.txt"
            stdout_path.write_text(text, encoding="utf-8")
            step = {
                "name": name,
                "ok": True,
                "stdout_path": v2834.runner.rel(stdout_path),
                "protocol": {"status": "ok"},
            }
            steps.append(step)
            return step

        try:
            v2834.runner.base.run_serial_step = fake_run_serial_step
            with tempfile.TemporaryDirectory() as temp_dir:
                out_dir = Path(temp_dir)
                _step, markers = v2834.runner.run_serial_marker_step(
                    out_dir,
                    [],
                    "probe",
                    ["audio", "status"],
                    ["marker-a", "marker-b"],
                    timeout=1.0,
                )
        finally:
            v2834.runner.base.run_serial_step = old_run_serial_step

        self.assertEqual(calls, ["probe", "probe-marker-retry1"])
        self.assertTrue(markers["ok"])
        self.assertEqual(markers["count"], 2)
        self.assertEqual(markers["best_step"], "probe-marker-retry1")
        self.assertEqual(len(markers["attempts"]), 2)


if __name__ == "__main__":
    unittest.main()
