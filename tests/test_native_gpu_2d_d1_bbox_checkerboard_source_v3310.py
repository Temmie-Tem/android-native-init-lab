from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3310_gpu_2d_d1_bbox_checkerboard_probe.py"
)
d0_reference = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_2d_d0_texture_reference_v3304.py"
)
d1_shader_bytes = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_2d_d1_textured_shader_bytes_v3305.py"
)


class NativeGpu2dD1BboxCheckerboardSourceV3310Tests(unittest.TestCase):
    def test_v3310_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3310")
        self.assertEqual(runner.INIT_VERSION, "0.11.82")
        self.assertEqual(runner.INIT_BUILD, "v3310-gpu-2d-d1-bbox-checkerboard-probe")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3310_gpu_2d_d1_bbox_checkerboard_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.82", required)
        self.assertIn(b"v3310-gpu-2d-d1-bbox-checkerboard-probe", required)
        self.assertIn(
            b"gpu.d1.texture.scope=gpu-2d-d1-static-checkerboard-texture-readback",
            required,
        )
        self.assertIn(b"gpu.d1.texture.label=GPU BBOX CHECKERBOARD", required)
        self.assertIn(b"bbox-checkerboard-readback-pass", required)
        self.assertIn(b"gpu.d1.texture.texture_sample_match_count=%u", required)
        self.assertIn(b"gpu.d1.texture.texture_sample_mismatch_count=%u", required)
        self.assertIn(b"gpu.d1.texture.texture_bbox_sample_match_count=%u", required)

    def test_dispatch_contains_d1_texture_pipeline_contract(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_D1_TEXTURE_WIDTH 128U", source)
        self.assertIn("#define GPU_D1_TEXTURE_HEIGHT 128U", source)
        self.assertIn("#define GPU_D1_CHECKER_BLOCK 16U", source)
        self.assertIn("#define GPU_D1_CHECKER_SAMPLE_GRID 8U", source)
        self.assertIn("#define GPU_D1_SP_PS_CONFIG_TEXTURED", source)
        self.assertIn("GPU_H1_SP_CONFIG_ENABLED | (1U << 9) | (1U << 17)", source)
        self.assertIn("#define GPU_D1_VIEWPORT_SCALE_X (GPU_H2_COLOR_WIDTH / 2U)", source)
        self.assertIn("#define GPU_D1_VIEWPORT_SCALE_Y (GPU_H2_COLOR_HEIGHT / 2U)", source)
        self.assertIn("#define GPU_D1_VIEWPORT_OFFSET_X (GPU_H2_COLOR_WIDTH / 2U)", source)
        self.assertIn("#define GPU_D1_VIEWPORT_OFFSET_Y (GPU_H2_COLOR_HEIGHT / 2U)", source)
        self.assertIn("gpu_d1_write_sampler_descriptor", source)
        self.assertIn("gpu_d1_write_texture_descriptor", source)
        self.assertIn("GPU_D1_CP_LOAD_STATE6_STATE_TYPE_SHADER", source)
        self.assertIn("GPU_D1_CP_LOAD_STATE6_STATE_TYPE_CONSTANTS", source)
        self.assertIn("GPU_D1_CP_LOAD_STATE6_SB_FS_TEX", source)
        self.assertIn("gpu_d1_pm4_emit_texture_state", source)
        self.assertNotIn("gpu_d1_pm4_emit_fullscreen_viewport_override", source)
        self.assertIn("gpu_d1_build_texture_checkerboard_pm4", source)
        self.assertIn("gpu_d1_texture_checkerboard_probe", source)
        self.assertIn("0xbf800000U, 0xbf800000U", source)

    def test_dispatch_routes_gpu_d1_command_and_reports_pattern_gate(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn('strcmp(subcommand, "d1-texture-checkerboard-probe") == 0', source)
        self.assertIn('strcmp(subcommand, "texture-checkerboard-probe") == 0', source)
        self.assertIn("gpu.d1.texture.command=gpu d1-texture-checkerboard-probe", source)
        self.assertIn("gpu.d1.texture.result=%s", source)
        self.assertIn("bbox-checkerboard-readback-pass", source)
        self.assertIn("linear_readback_changed_count > 0U", source)
        self.assertIn("texture_bbox_sample_match_count == GPU_D1_CHECKER_SAMPLE_COUNT", source)
        self.assertIn("texture_bbox_sample_mismatch_count == 0U", source)
        self.assertIn("gpu.d1.texture.viewport_scale_mode=inherited-default-clip-space-bbox", source)
        self.assertIn("gpu.d1.texture.linear_readback_bbox=%u,%u,%u,%u", source)
        self.assertIn("gpu.d1.texture.texture_bbox_sample_count=%u", source)
        self.assertIn("gpu.d1.texture.texture_bbox_sample_match_count=%u", source)
        self.assertIn("gpu.d1.texture.texture_bbox_sample_mismatch_count=%u", source)
        self.assertIn("gpu.d1.texture.texture_dark_count=%u", source)
        self.assertIn("gpu.d1.texture.texture_light_count=%u", source)
        self.assertIn("gpu.d1.texture.texture_other_count=%u", source)
        self.assertIn("usage: gpu d1-texture-checkerboard-probe", source)

    def test_builder_manifest_records_d1_live_validation_and_report_gate(self) -> None:
        manifest = runner._minimal_gpu_d1_manifest()
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

        self.assertEqual(manifest["scope"], "gpu-2d-d1-static-checkerboard-texture-readback")
        self.assertEqual(manifest["expected_bbox_sample_matches"], 64)
        self.assertEqual(manifest["expected_bbox_sample_mismatches"], 0)
        self.assertEqual(manifest["expected_linear_bbox"], "non-empty, device-measured")
        self.assertEqual(manifest["expected_linear_changed_count"], "greater-than-zero")
        self.assertIn("require-linear-readback-bbox-found", manifest["next_live_validation"])
        self.assertIn("require-linear-readback-changed-count-positive", manifest["next_live_validation"])
        self.assertIn("require-texture-bbox-sample-match-count-64", manifest["next_live_validation"])
        self.assertIn("require-texture-bbox-sample-mismatch-count-0", manifest["next_live_validation"])
        self.assertIn("texture_bbox_sample_count=64", report)
        self.assertIn("texture_bbox_sample_match_count=64", report)
        self.assertIn("texture_bbox_sample_mismatch_count=0", report)
        self.assertIn("Full 128x128 viewport coverage is parked", report)

    def test_v3304_v3305_prerequisites_still_pass_host_gates(self) -> None:
        d0 = d0_reference.run_recon()
        d1 = d1_shader_bytes.run_verification(require_disasm=False)

        self.assertTrue(d0["passed"])
        self.assertTrue(d0["checks"]["d0_texture_reference_recon_passed"])
        self.assertTrue(d1["passed"])
        self.assertTrue(d1["ready_for_d1_source"])
        self.assertEqual(
            d1["shader"]["binary_sha256"],
            "4e8ad0a934d236149af999619a1fe99690e7b732d2e4ca69a2b345100d8d04a3",
        )


if __name__ == "__main__":
    unittest.main()
