from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3314_gpu_2d_d3_video_semantic_present.py"
)


class NativeGpu2dD3VideoSemanticPresentSourceV3314Tests(unittest.TestCase):
    def test_v3314_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3314")
        self.assertEqual(runner.INIT_VERSION, "0.11.86")
        self.assertEqual(runner.INIT_BUILD, "v3314-gpu-2d-d3-video-semantic-present")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3314_gpu_2d_d3_video_semantic_present.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.86", required)
        self.assertIn(b"v3314-gpu-2d-d3-video-semantic-present", required)
        self.assertIn(b"--start-frame", required)
        self.assertIn(b"gpu.d3.video.start_frame=%u", required)
        self.assertIn(b"gpu.d3.video.semantic.sample_count=%u", required)
        self.assertIn(b"gpu.d3.video.semantic.match_count=%u", required)
        self.assertIn(b"gpu.d3.video.semantic.mismatch_count=%u", required)
        self.assertIn(b"gpu.d3.video.semantic.output_other_count=%u", required)

    def test_dispatch_contains_d3_semantic_present_contract(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("semantic_sample_count", source)
        self.assertIn("semantic_sample_match_count", source)
        self.assertIn("semantic_sample_mismatch_count", source)
        self.assertIn("semantic_output_other_count", source)
        self.assertIn("gpu_d3_validate_linear_semantics", source)
        self.assertIn("gpu_d3_video_summary_passed", source)
        self.assertIn('strcmp(argv[index], "--start-frame") == 0', source)
        self.assertIn("gpu.d3.video.start_frame=%u", source)
        self.assertIn("gpu.d3.video.start_frame_actual=%u", source)
        self.assertIn("gpu.d3.video.skipped_frames=%u", source)
        self.assertIn("gpu.d3.video.last_frame_index=%u", source)
        self.assertIn("gpu.d3.video.semantic.sample_count=%u", source)
        self.assertIn("gpu.d3.video.semantic.match_count=%u", source)
        self.assertIn("gpu.d3.video.semantic.mismatch_count=%u", source)
        self.assertIn("gpu.d3.video.semantic.output_other_count=%u", source)
        self.assertIn("summary->semantic_sample_count == GPU_D1_CHECKER_SAMPLE_COUNT", source)
        self.assertIn("summary->semantic_sample_match_count == GPU_D1_CHECKER_SAMPLE_COUNT", source)
        self.assertIn("summary->semantic_sample_mismatch_count == 0U", source)
        self.assertIn("summary->semantic_output_other_count == 0U", source)

    def test_builder_manifest_records_semantic_live_validation(self) -> None:
        manifest = runner._minimal_gpu_d3_manifest()
        report = runner.render_report(
            {
                "decision": runner.DECISION,
                "boot_image": str(runner.BOOT_IMAGE),
                "boot_sha256": "0" * 64,
                "init_version": runner.INIT_VERSION,
                "init_build": runner.INIT_BUILD,
            },
            (),
            (),
        )

        self.assertEqual(manifest["scope"], "gpu-2d-d3-demo-player-texture-blit-present-semantic")
        self.assertEqual(manifest["start_frame"], 515)
        self.assertEqual(manifest["expected_semantic_sample_count"], 64)
        self.assertEqual(manifest["expected_semantic_match_count"], 64)
        self.assertEqual(manifest["expected_semantic_mismatch_count"], 0)
        self.assertEqual(manifest["expected_semantic_output_other_count"], 0)
        self.assertIn("gpu-d3-video-texture-present-probe-start-frame-515", manifest["next_live_validation"])
        self.assertIn("require-semantic-sample-count-64", manifest["next_live_validation"])
        self.assertIn("require-semantic-match-count-64", manifest["next_live_validation"])
        self.assertIn("require-semantic-mismatch-count-0", manifest["next_live_validation"])
        self.assertIn("require-semantic-output-other-count-0", manifest["next_live_validation"])
        self.assertIn("semantic video texture present gate", report)
        self.assertIn("start-frame", report)
        self.assertIn("semantic_sample_count=64", report)
        self.assertIn("not a new default menu policy", report)


if __name__ == "__main__":
    unittest.main()
