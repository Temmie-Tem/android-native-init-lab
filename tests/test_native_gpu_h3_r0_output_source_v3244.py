from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3244_gpu_h3_r0_output_probe.py"
)


class NativeGpuH3R0OutputSourceV3244Tests(unittest.TestCase):
    def test_v3244_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3244")
        self.assertEqual(runner.INIT_VERSION, "0.11.49")
        self.assertEqual(runner.INIT_BUILD, "v3244-gpu-h3-r0-output-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3242_gpu_h3_direct_render_marker_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.49", required)
        self.assertIn(b"v3244-gpu-h3-r0-output-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-r0-output-full-state-mov-f32-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.shader_payload=hand-assembled-ir3-r0-output-mov-f32-vs-position-fs-color-no-full-compiler",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.shader_output_source=mesa-freedreno-a6xx-fd6-emit-vpc-emit-fs-outputs-regid-map",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.render_marker_source=mesa-freedreno-a6xx-fd6-set-render-mode-rm6-direct-render",
            required,
        )
        self.assertIn(b"gpu.h3.draw.cp_set_marker=0x%x", required)
        self.assertIn(
            b"gpu.h3.draw.rb_ccu_source=mesa-freedreno-a6xx-fd6-emit-gmem-cache-cntl-sysmem-adreno640v2",
            required,
        )
        self.assertIn(b"gpu.h3.draw.vs_output_regid=0x%x", required)
        self.assertIn(b"gpu.h3.draw.ps_output_regid=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_vs_output_reg0=0x%x", required)
        self.assertNotIn(
            b"gpu.h3.draw.scope=first-triangle-h3-direct-render-marker-r1-footprint2-mov-f32-shader",
            required,
        )
        self.assertNotIn(
            b"gpu.h3.draw.shader_payload=hand-assembled-ir3-r1-output-mov-f32-vs-position-fs-color-no-full-compiler",
            required,
        )

    def test_dispatch_programs_r0_output_shader_contract(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_H3_VS_SHADER_DWORDS 12U", source)
        self.assertIn("#define GPU_H3_FS_SHADER_DWORDS 8U", source)
        self.assertIn("#define GPU_H3_VS_OUTPUT_REGID 0U", source)
        self.assertIn("#define GPU_H3_PS_OUTPUT_REGID 0U", source)
        self.assertIn("#define GPU_H3_SP_FULLREGFOOTPRINT 2U", source)
        self.assertIn("#define GPU_H3_IR3_MOV_F32F32_R0X_R0X_LO 0x00000000U", source)
        self.assertIn("#define GPU_H3_IR3_MOV_F32F32_R0Y_R0Y_LO 0x00000001U", source)
        self.assertIn("#define GPU_H3_IR3_MOV_F32F32_R0X_R0X_HI 0x20044000U", source)
        self.assertIn("#define GPU_H3_IR3_MOV_F32F32_R0Y_R0Y_HI 0x20044001U", source)
        self.assertIn("#define GPU_H3_IR3_MOV_F32F32_R0Z_HI 0x20444002U", source)
        self.assertIn("#define GPU_H3_IR3_MOV_F32F32_R0W_HI 0x20444003U", source)
        self.assertIn("#define GPU_G4_PM4_CP_SET_MARKER 0x65U", source)
        self.assertIn("#define GPU_H3_A6XX_CP_SET_MARKER_RM6_DIRECT_RENDER 1U", source)
        self.assertIn("#define GPU_H3_RB_CCU_CNTL 0x10000000U", source)

        self.assertIn("static const uint32_t vs_shader[GPU_H3_VS_SHADER_DWORDS]", source)
        self.assertIn(
            "GPU_H3_IR3_MOV_F32F32_R0X_R0X_LO, GPU_H3_IR3_MOV_F32F32_R0X_R0X_HI",
            source,
        )
        self.assertIn(
            "GPU_H3_IR3_MOV_F32F32_R0Y_R0Y_LO, GPU_H3_IR3_MOV_F32F32_R0Y_R0Y_HI",
            source,
        )
        self.assertIn("GPU_H3_IR3_F32_0_LO, GPU_H3_IR3_MOV_F32F32_R0Z_HI", source)
        self.assertIn("GPU_H3_IR3_F32_1_LO, GPU_H3_IR3_MOV_F32F32_R0W_HI", source)
        self.assertIn("static const uint32_t fs_shader[GPU_H3_FS_SHADER_DWORDS]", source)
        self.assertIn("GPU_H3_IR3_F32_1_LO, GPU_H3_IR3_MOV_F32F32_R0X_HI", source)
        self.assertNotIn("GPU_H3_IR3_F32_1_LO, GPU_H3_IR3_MOV_F32F32_R1X_HI", source)
        self.assertIn(
            "GPU_G4_PM4_CP_SET_MARKER, 1) ||\n        !gpu_g4_pm4_push(words, dwords,\n                         GPU_H3_A6XX_CP_SET_MARKER_RM6_DIRECT_RENDER)",
            source,
        )
        self.assertLess(
            source.index("GPU_H3_A6XX_CP_SET_MARKER_RM6_DIRECT_RENDER"),
            source.index("GPU_H3_REG_RB_CCU_CNTL,\n                              GPU_H3_RB_CCU_CNTL"),
        )
        self.assertTrue(
            '"gpu.h3.draw.scope=first-triangle-h3-r0-output-full-state-mov-f32-shader' in source
            or '"gpu.h3.draw.scope=first-triangle-h3-rb-render-cntl-r0-output-mov-f32-shader'
            in source
        )
        self.assertIn(
            '"gpu.h3.draw.shader_payload=hand-assembled-ir3-r0-output-mov-f32-vs-position-fs-color-no-full-compiler',
            source,
        )
        self.assertIn('"gpu.h3.draw.vs_output_regid=0x%x', source)
        self.assertIn('"gpu.h3.draw.ps_output_regid=0x%x', source)
        self.assertIn('"gpu.h3.draw.sp_vs_output_reg0=0x%x', source)

    def test_builder_manifest_records_r0_output_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3242-direct-render-marker-plus-rb-ccu-on-v3232-ramdisk-base"',
            source,
        )
        self.assertIn('"scope": "first-triangle-h3-r0-output-full-state-mov-f32-shader"', source)
        self.assertIn('"shader_payload": "hand-assembled-ir3-r0-output-mov-f32-vs-position-fs-color-no-full-compiler"', source)
        self.assertIn('"ir3_mov_f32f32_r0x_r0x_opcode": "0x2004400000000000"', source)
        self.assertIn('"ir3_mov_f32f32_r0y_r0y_opcode": "0x2004400100000001"', source)
        self.assertIn('"vs_shader_dwords": 12', source)
        self.assertIn('"fs_shader_dwords": 8', source)
        self.assertIn('"vs_output_regid": "0x00"', source)
        self.assertIn('"ps_output_regid": "0x00"', source)
        self.assertIn('"sp_vs_output_reg0": "0x00000f00"', source)
        self.assertIn('"state_reg_writes_expected": 92', source)
        self.assertIn('"pm4_dwords_expected": 233', source)
        self.assertIn('"cp_set_marker_payload": "0x00000001"', source)
        self.assertIn('"rb_ccu_cntl": "0x10000000"', source)
        self.assertIn("gpu-h3-r0-output-full-state-mov-f32-shader-timeout-guard", source)
        self.assertIn("preserve-v3242-ramdisk-overlay-v3244-init-helper-engine", source)
        self.assertIn('"bin/a90_doomgeneric_private_engine_v3244"', source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)
        self.assertIn("V3244 boot image too large for boot partition", source)


if __name__ == "__main__":
    unittest.main()
