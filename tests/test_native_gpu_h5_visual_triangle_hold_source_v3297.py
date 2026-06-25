from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3297_gpu_h5_visual_triangle_hold_probe.py"
)
strict_runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3295_gpu_h5_strict_triangle_kms_probe.py"
)


class NativeGpuH5VisualTriangleHoldSourceV3297Tests(unittest.TestCase):
    def test_v3297_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3297")
        self.assertEqual(runner.INIT_VERSION, "0.11.74")
        self.assertEqual(runner.INIT_BUILD, "v3297-gpu-h5-visual-triangle-hold-probe")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3297_gpu_h5_visual_triangle_hold_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.74", required)
        self.assertIn(b"v3297-gpu-h5-visual-triangle-hold-probe", required)
        self.assertIn(
            b"gpu.h5.kms.scope=first-triangle-h5-visual-close-held-kms-probe",
            required,
        )
        self.assertIn(b"gpu.h5.vis.result=triangle-presented-held", required)
        self.assertIn(b"h3-visual-triangle-kms-presented", required)
        self.assertIn(b"GPU H5 VISUAL CLOSE", required)
        self.assertIn(b"RECOGNIZABLE TRIANGLE HOLD", required)

    def test_dispatch_draws_centered_visual_mask_and_holds(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_H5_VISUAL_HOLD_DEFAULT_MS 30000", source)
        self.assertIn("#define GPU_H5_VISUAL_HOLD_MAX_MS 60000", source)
        self.assertIn("gpu_h5_find_linear_nonzero_bounds", source)
        self.assertIn("gpu.h5.vis.source_bbox=%u,%u,%u,%u", source)
        self.assertIn("gpu.h5.vis.mode=linear-nonzero-mask-solid-fill-centered", source)
        self.assertIn("gpu.h5.vis.visual_shape=solid-mask-centered", source)
        self.assertIn("GPU H5 VISUAL CLOSE", source)
        self.assertIn("RECOGNIZABLE TRIANGLE HOLD", source)
        self.assertIn("stop_auto_hud(false);", source)
        self.assertIn("gpu.h5.vis.autohud_stop_attempted=1", source)
        self.assertIn("gpu.h5.vis.hold_begin=1", source)
        self.assertIn("gpu.h5.vis.hold_elapsed_ms=%ld", source)
        self.assertIn("gpu.h5.vis.result=triangle-presented-held", source)

    def test_dispatch_keeps_strict_gpu_proof_gate(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("gpu.h5.kms.h3_linear_readback_nonzero_count=%u", source)
        self.assertIn("h3->linear_readback_nonzero_count == 0U", source)
        self.assertIn("h3->linear_center_nonzero == 0U", source)
        self.assertIn("h3->linear_exterior_corners_zero == 0U", source)
        self.assertIn("gpu.h5.kms.strict_linear_triangle_sample_proof=%u", source)
        self.assertIn("h3-private-linear-snapshot-solid-triangle-mask-to-kms-dumb-framebuffer", source)
        self.assertIn("h3-visual-triangle-kms-presented", source)

    def test_builder_manifest_records_visual_close_scope(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn('"source_baseline": "v3296-h5-strict-triangle-kms-live-proof"', source)
        self.assertIn('"visual_hold_default_ms": 30000', source)
        self.assertIn('"operator-panel-visual-confirmation"', source)
        self.assertIn("gpu-h5-visual-triangle-hold-probe-candidate", source)

    def test_v3295_identity_still_available_for_regression(self) -> None:
        self.assertEqual(strict_runner.CYCLE, "V3295")
        self.assertEqual(strict_runner.INIT_VERSION, "0.11.73")
        self.assertIn(
            b"gpu.h5.kms.h3_linear_readback_nonzero_count=%u",
            b"\n".join(strict_runner.REQUIRED_STRINGS),
        )


if __name__ == "__main__":
    unittest.main()
