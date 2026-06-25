from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3291_gpu_h5_triangle_kms_probe.py"
)
audit = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_h3_shader_byte_audit_v3246.py"
)


class NativeGpuH5TriangleKmsSourceV3291Tests(unittest.TestCase):
    def test_v3291_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3291")
        self.assertEqual(runner.INIT_VERSION, "0.11.71")
        self.assertEqual(runner.INIT_BUILD, "v3291-gpu-h5-triangle-kms-probe")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3291_gpu_h5_triangle_kms_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.71", required)
        self.assertIn(b"v3291-gpu-h5-triangle-kms-probe", required)
        self.assertIn(b"h5-triangle-kms-probe", required)
        self.assertIn(b"triangle-kms-probe", required)
        self.assertIn(
            b"gpu.h5.kms.scope=first-triangle-h5-h3-readback-to-kms-dumb-blit-probe",
            required,
        )
        self.assertIn(
            b"gpu.h5.kms.blit_mode=h3-private-buffer-readback-snapshot-to-kms-dumb-framebuffer",
            required,
        )
        self.assertIn(b"gpu.h5.kms.raw_tile_order_visualization=1", required)
        self.assertIn(b"gpu-h5-triangle-kms", required)

    def test_dispatch_adds_bounded_h3_snapshot_payload(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_H5_H3_SNAPSHOT_WORDS (GPU_H2_COLOR_WIDTH * GPU_H2_COLOR_HEIGHT)", source)
        self.assertIn("struct gpu_h3_draw_snapshot_payload", source)
        self.assertIn("uint32_t color_words[GPU_H5_H3_SNAPSHOT_WORDS];", source)
        self.assertTrue(
            "gpu_h3_draw_envelope_probe_child(int write_fd, bool include_snapshot)" in source
            or "gpu_h3_draw_envelope_probe_child(int write_fd,\n                                            bool include_snapshot,\n                                            bool linearize_snapshot)" in source
        )
        self.assertIn("memcpy(snapshot_words, color_words, sizeof(snapshot_words));", source)
        self.assertTrue(
            "return gpu_h3_draw_envelope_probe_child(pipefd[1], false);" in source
            or "return gpu_h3_draw_envelope_probe_child(pipefd[1], false, false);" in source
        )
        self.assertTrue(
            "return gpu_h3_draw_envelope_probe_child(pipefd[1], true);" in source
            or "return gpu_h3_draw_envelope_probe_child(pipefd[1], true, true);" in source
        )

    def test_dispatch_adds_parent_owned_h5_kms_command(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("static int gpu_h3_draw_snapshot_collect_child", source)
        self.assertIn("static int gpu_h5_blit_h3_readback_to_kms", source)
        self.assertIn("static int gpu_h5_triangle_kms_probe", source)
        self.assertTrue(
            "gpu.h5.kms.scope=first-triangle-h5-h3-readback-to-kms-dumb-blit-probe" in source
            or "gpu.h5.kms.scope=first-triangle-h5-visual-close-held-kms-probe" in source
        )
        self.assertTrue(
            "gpu.h5.kms.raw_tile_order_visualization=1" in source
            or "gpu.h5.kms.raw_tile_order_visualization=0" in source
        )
        self.assertIn("gpu.h5.kms.zero_copy_attempted=0", source)
        self.assertIn("gpu.h5.kms.scaled_plane_attempted=0", source)
        self.assertIn("a90_kms_begin_frame(0x050505)", source)
        self.assertIn("a90_kms_present(\"gpu-h5-triangle-kms\", true)", source)
        self.assertIn("h5-triangle-kms-probe", source)
        self.assertIn("triangle-kms-probe", source)

    def test_h5_keeps_existing_h3_shader_contract(self) -> None:
        result = audit.run_audit(ir3_disasm="/missing/ir3-disasm")
        checks = result["checks"]

        self.assertTrue(result["passed"])
        self.assertEqual([entry["disasm"] for entry in result["decoded"]["vs_shader"][:5]], [
            "mov.f32f32 r2.x, r1.x",
            "mov.f32f32 r2.y, r1.y",
            "mov.f32f32 r2.z, r1.z",
            "mov.f32f32 r2.w, r1.w",
            "end",
        ])
        self.assertEqual(checks["vertex_stride"], 36)
        self.assertEqual(checks["vfd_cntl_0"], 0x303)
        self.assertEqual(checks["sp_blend_cntl"], 0x100)
        self.assertEqual(checks["rb_blend_cntl"], 0xFFFF0100)
        self.assertEqual(checks["rb_mrt0_blend_control"], 0x08040804)

    def test_builder_manifest_records_h5_scope(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn('"source_baseline": "v3290-h3-readback-proof-plus-existing-g5-kms-dumb-blit"', source)
        self.assertIn('"h5_presentation": H5_PRESENTATION', source)
        self.assertIn('"command": H5_COMMAND', source)
        self.assertIn('"candidate_type": "gpu-h5-triangle-kms-probe-candidate"', source)
        self.assertIn('"h3_snapshot_words_expected": 128 * 128', source)
        self.assertIn('"zero_copy_attempted": False', source)
        self.assertIn("gpu-h5-triangle-kms-timeout-guard", source)


if __name__ == "__main__":
    unittest.main()
