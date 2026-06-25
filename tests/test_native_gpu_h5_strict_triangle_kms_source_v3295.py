from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3295_gpu_h5_strict_triangle_kms_probe.py"
)
audit = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_h3_shader_byte_audit_v3246.py"
)


class NativeGpuH5StrictTriangleKmsSourceV3295Tests(unittest.TestCase):
    def test_v3295_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3295")
        self.assertEqual(runner.INIT_VERSION, "0.11.73")
        self.assertEqual(runner.INIT_BUILD, "v3295-gpu-h5-strict-triangle-kms-probe")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3295_gpu_h5_strict_triangle_kms_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.73", required)
        self.assertIn(b"v3295-gpu-h5-strict-triangle-kms-probe", required)
        self.assertIn(
            b"gpu.h5.kms.scope=first-triangle-h5-a2d-linearized-strict-sample-kms-probe",
            required,
        )
        self.assertIn(
            b"gpu.h5.kms.blit_mode=h3-private-buffer-a2d-linearized-snapshot-to-kms-dumb-framebuffer",
            required,
        )
        self.assertIn(b"gpu.h5.kms.raw_tile_order_visualization=0", required)
        self.assertIn(b"gpu.h5.kms.linearized_tile6_3_a2d_blit=1", required)
        self.assertIn(b"gpu.h5.kms.h3_linear_readback_nonzero_count=%u", required)
        self.assertIn(b"gpu.h5.kms.h3_linear_center_nonzero=%u", required)
        self.assertIn(b"gpu.h5.kms.h3_linear_exterior_corners_zero=%u", required)
        self.assertIn(b"gpu.h5.kms.strict_linear_triangle_sample_proof=%u", required)
        self.assertIn(b"h3-linear-readback-kms-presented", required)

    def test_dispatch_adds_a2d_tile6_3_to_linear_stage(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_G4_CMD_MAX_DWORDS 512U", source)
        self.assertIn("#define GPU_H5_A2D_BLT_CNTL_SCALE_RGBA8 0x10f03000U", source)
        self.assertIn("#define GPU_H5_A2D_OUTPUT_INFO_RGBA8 0x0000f180U", source)
        self.assertIn("#define GPU_H5_A2D_SRC_TEXTURE_INFO_TILE6_3_FLAGS", source)
        self.assertIn("#define GPU_H5_A2D_DEST_BUFFER_INFO_LINEAR GPU_H3_COLOR_FORMAT", source)
        self.assertIn("static bool gpu_h5_append_tile6_3_to_linear_a2d_pm4", source)
        self.assertIn("GPU_H5_REG_TPL1_A2D_SRC_TEXTURE_INFO", source)
        self.assertIn("GPU_H5_REG_TPL1_A2D_SRC_TEXTURE_FLAG_BASE", source)
        self.assertIn("GPU_H5_REG_RB_A2D_DEST_FLAG_BUFFER_BASE", source)
        self.assertIn("GPU_G4_A6XX_CP_SET_MARKER_RM6_BLIT2DSCALE", source)
        self.assertIn("GPU_G4_PM4_CP_BLIT", source)

    def test_h5_uses_linear_snapshot_and_stronger_success_gate(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn(
            "gpu_h3_draw_envelope_probe_child(pipefd[1], true, true)",
            source,
        )
        self.assertIn("uint32_t *linear_words = (uint32_t *)linear_map;", source)
        self.assertIn("memcpy(snapshot_words, linear_words, sizeof(snapshot_words));", source)
        self.assertIn("gpu.h5.kms.raw_tile_order_visualization=0", source)
        self.assertIn("gpu.h5.kms.linearized_tile6_3_a2d_blit=1", source)
        self.assertIn("gpu.h5.kms.h3_linear_readback_nonzero_count=%u", source)
        self.assertIn("#define GPU_H5_LINEAR_CLEAR_PATTERN 0x00000000U", source)
        self.assertIn("linear_words[index] = GPU_H5_LINEAR_CLEAR_PATTERN;", source)
        self.assertIn("h3->linear_readback_nonzero_count == 0U", source)
        self.assertIn("h3->linear_center_nonzero == 0U", source)
        self.assertIn("h3->linear_exterior_corners_zero == 0U", source)
        self.assertIn("gpu.h5.kms.strict_linear_triangle_sample_proof=%u", source)
        self.assertIn("gpu.h5.kms.result=h3-linear-readback-failed", source)
        self.assertTrue(
            "h3-linear-readback-kms-presented" in source
            or "h3-visual-triangle-kms-presented" in source
        )
        self.assertTrue(
            "A2D LINEAR H3 STRICT" in source
            or "GPU H5 VISUAL CLOSE" in source
        )

    def test_h5_keeps_existing_h3_shader_contract(self) -> None:
        result = audit.run_audit(ir3_disasm="/missing/ir3-disasm")
        checks = result["checks"]

        self.assertTrue(result["passed"])
        self.assertEqual(checks["vertex_stride"], 36)
        self.assertEqual(checks["vfd_cntl_0"], 0x303)
        self.assertEqual(checks["sp_blend_cntl"], 0x100)
        self.assertEqual(checks["rb_blend_cntl"], 0xFFFF0100)
        self.assertEqual(checks["rb_mrt0_blend_control"], 0x08040804)
        self.assertTrue(checks["rb_mrt0_buf_info_matches_a640_cffdump_tile6_3"])

    def test_builder_manifest_records_linearized_scope(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn('"source_baseline": "v3294-h5-a2d-linearized-kms-live-telemetry-proof"', source)
        self.assertIn('"h5_presentation": H5_PRESENTATION', source)
        self.assertIn('"a2d_linearization_attempted": True', source)
        self.assertIn('"raw_tile_order_visualization": False', source)
        self.assertIn("gpu-h5-strict-triangle-kms-probe-candidate", source)


if __name__ == "__main__":
    unittest.main()
