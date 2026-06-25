from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3216_gpu_h3_minimal_ir3_mov_shader_probe.py"
)


class NativeGpuH3MinimalIr3MovShaderSourceV3216Tests(unittest.TestCase):
    def test_v3216_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3216")
        self.assertEqual(runner.INIT_VERSION, "0.11.35")
        self.assertEqual(runner.INIT_BUILD, "v3216-gpu-h3-minimal-ir3-mov-shader-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3214_gpu_h3_ir3_end_terminator_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.35", required)
        self.assertIn(b"v3216-gpu-h3-minimal-ir3-mov-shader-probe", required)
        self.assertIn(b"h3-draw-envelope-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-minimal-ir3-mov-f32-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.shader_payload=hand-assembled-ir3-mov-f32-vs-position-fs-color-no-full-compiler",
            required,
        )
        self.assertIn(b"gpu.h3.draw.ir3_end_opcode_hi=0x%x", required)
        self.assertIn(b"gpu.h3.draw.ir3_mov_f32f32_r0x_hi=0x%x", required)
        self.assertIn(b"gpu.h3.draw.fs_color_f32_bits=0x%x", required)
        self.assertIn(b"gpu.h3.draw.offscreen=f32-linear-128x128", required)
        self.assertIn(b"gpu.h3.draw.readback_change_expected=1", required)
        self.assertNotIn(b"zero-placeholder-no-full-compiler", required)

    def test_dispatch_uses_minimal_ir3_mov_shader_stream(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn("GPU_G4_A6XX_FMT6_32_FLOAT 0x4aU", source)
        self.assertIn("GPU_H3_COLOR_FORMAT GPU_G4_A6XX_FMT6_32_FLOAT", source)
        self.assertIn("GPU_H3_COLOR_OUTPUT_MASK 0x1U", source)
        self.assertIn("GPU_H1_IR3_END_LO 0x00000000U", source)
        self.assertIn("GPU_H1_IR3_END_HI 0x03000000U", source)
        self.assertIn("GPU_H3_IR3_F32_0_LO 0x00000000U", source)
        self.assertIn("GPU_H3_IR3_F32_1_LO 0x3f800000U", source)
        self.assertIn("GPU_H3_IR3_MOV_F32F32_R0X_HI 0x20444000U", source)
        self.assertIn("GPU_H3_IR3_MOV_F32F32_R0Z_HI 0x20444002U", source)
        self.assertIn("GPU_H3_IR3_MOV_F32F32_R0W_HI 0x20444003U", source)
        self.assertIn("GPU_H3_IR3_F32_0_LO, GPU_H3_IR3_MOV_F32F32_R0Z_HI", source)
        self.assertIn("GPU_H3_IR3_F32_1_LO, GPU_H3_IR3_MOV_F32F32_R0W_HI", source)
        self.assertIn("GPU_H3_IR3_F32_1_LO, GPU_H3_IR3_MOV_F32F32_R0X_HI", source)
        self.assertIn("GPU_H1_IR3_END_LO, GPU_H1_IR3_END_HI", source)
        self.assertIn("color_format |", source)
        self.assertIn("color_uint ? (1U << 9) : 0U", source)
        self.assertIn("GPU_H3_COLOR_FORMAT, GPU_H3_COLOR_OUTPUT_MASK", source)
        self.assertIn(
            '"gpu.h3.draw.scope=first-triangle-h3-minimal-ir3-mov-f32-shader',
            source,
        )
        self.assertIn(
            '"gpu.h3.draw.shader_payload=hand-assembled-ir3-mov-f32-vs-position-fs-color-no-full-compiler',
            source,
        )
        self.assertIn('"gpu.h3.draw.ir3_end_opcode_hi=0x%x', source)
        self.assertIn('"gpu.h3.draw.readback_change_expected=1', source)

    def test_builder_manifest_records_minimal_mov_shader_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"source_baseline": "v3214-gpu-h3-ir3-end-terminator-probe"', source)
        self.assertIn('"ir3_end_opcode": "0x0300000000000000"', source)
        self.assertIn('"ir3_mov_f32f32_r0x_opcode_hi": "0x20444000"', source)
        self.assertIn('"fs_color_f32_bits": "0x3f800000"', source)
        self.assertIn('"color_format": "FMT6_32_FLOAT"', source)
        self.assertIn('"shader_payload": "hand-assembled-ir3-mov-f32-vs-position-fs-color-no-full-compiler"', source)
        self.assertIn("pending-gpu-h3-minimal-ir3-mov-shader-live-validation", source)
        self.assertIn("ir3-cat0.xml", source)
        self.assertIn("ir3-cat1.xml", source)
        self.assertIn("ir3.xml", source)
        self.assertIn("preserve-v3214-ramdisk-overlay-v3216-init-helper-engine", source)
        self.assertIn('"bin/a90_doomgeneric_private_engine_v3214"', source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)
        self.assertIn("V3216 boot image too large for boot partition", source)
        self.assertIn('"removed_stale_entries": removed_stale_entries', source)


if __name__ == "__main__":
    unittest.main()
