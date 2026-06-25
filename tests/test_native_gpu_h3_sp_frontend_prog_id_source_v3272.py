from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3272_gpu_h3_sp_frontend_prog_id_probe.py"
)


class NativeGpuH3SpFrontendProgIdSourceV3272Tests(unittest.TestCase):
    def test_v3272_identity_and_base(self) -> None:
        self.assertEqual(runner.CYCLE, "V3272")
        self.assertEqual(runner.INIT_VERSION, "0.11.62")
        self.assertEqual(runner.INIT_BUILD, "v3272-gpu-h3-sp-frontend-prog-id-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3268_gpu_h3_raster_mode_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.62", required)
        self.assertIn(b"v3272-gpu-h3-sp-frontend-prog-id-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-sp-frontend-prog-id-state-sp-const-fs-output-cntl-raster-mode-cp-set-mode-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader",
            required,
        )
        self.assertIn(b"gpu.h3.draw.sp_const_config_source=mesa-freedreno-a6xx-fd6-program-config-stateobj", required)
        self.assertIn(b"gpu.h3.draw.sp_vs_const_config=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_ps_const_config=0x%x", required)
        self.assertIn(b"gpu.h3.draw.fs_output_cntl_source=mesa-freedreno-a6xx-fd6-program-invalid-depth-sampmask-stencil-regids", required)
        self.assertIn(b"gpu.h3.draw.sp_ps_output_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_frontend_prog_id_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-current-constant-fs-no-varyings", required)
        self.assertIn(b"gpu.h3.draw.sp_ps_initial_tex_load_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_ps_wave_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_lb_param_limit=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_reg_prog_id_0=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_reg_prog_id_1=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_reg_prog_id_2=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_reg_prog_id_3=0x%x", required)

    def test_dispatch_emits_sp_frontend_prog_id_state(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        state_emit = source[source.index("static bool gpu_h2_append_3d_state_pm4"):]
        shader_emit = source[source.index("static bool gpu_h3_append_shader_state_pm4"):]

        self.assertIn("#define GPU_H3_SP_INVALID_REG 0xfcU", source)
        self.assertIn("#define GPU_H3_SP_PS_INITIAL_TEX_LOAD_CNTL 0x00000008U", source)
        self.assertIn("#define GPU_H3_SP_PS_WAVE_CNTL 0x00000000U", source)
        self.assertIn("#define GPU_H3_SP_LB_PARAM_LIMIT 0x00000007U", source)
        self.assertIn("#define GPU_H3_SP_PS_OUTPUT_CNTL \\", source)
        self.assertIn("(GPU_H3_SP_INVALID_REG << 8)", source)
        self.assertIn("(GPU_H3_SP_INVALID_REG << 16)", source)
        self.assertIn("(GPU_H3_SP_INVALID_REG << 24)", source)
        self.assertIn("#define GPU_H3_SP_REG_PROG_ID_0 \\", source)
        self.assertIn("#define GPU_H3_SP_REG_PROG_ID_1 GPU_H3_SP_REG_PROG_ID_0", source)
        self.assertIn("#define GPU_H3_SP_REG_PROG_ID_2 GPU_H3_SP_REG_PROG_ID_0", source)
        self.assertIn("#define GPU_H3_REG_SP_VS_CONST_CONFIG 0xb800U", source)
        self.assertIn("#define GPU_H3_REG_SP_PS_CONST_CONFIG 0xbb10U", source)
        self.assertIn("#define GPU_H3_REG_SP_PS_INITIAL_TEX_LOAD_CNTL 0xa99eU", source)
        self.assertIn("#define GPU_H3_REG_SP_PS_WAVE_CNTL 0xb980U", source)
        self.assertIn("#define GPU_H3_REG_SP_LB_PARAM_LIMIT 0xb982U", source)
        self.assertIn("#define GPU_H3_REG_SP_REG_PROG_ID_0 0xb983U", source)
        self.assertIn("#define GPU_H3_REG_SP_REG_PROG_ID_1 0xb984U", source)
        self.assertIn("#define GPU_H3_REG_SP_REG_PROG_ID_2 0xb985U", source)
        self.assertIn("#define GPU_H3_SP_CONST_CONFIG_ENABLED 0x00000100U", source)
        self.assertIn(
            '"gpu.h3.draw.scope=first-triangle-h3-sp-frontend-prog-id-state-sp-const-fs-output-cntl-raster-mode-cp-set-mode-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader',
            source,
        )
        self.assertLess(
            shader_emit.index("GPU_H1_REG_SP_VS_INSTR_SIZE"),
            shader_emit.index("GPU_H3_REG_SP_VS_CONST_CONFIG"),
        )
        self.assertLess(
            shader_emit.index("GPU_H1_REG_SP_PS_INSTR_SIZE"),
            shader_emit.index("GPU_H3_REG_SP_PS_CONST_CONFIG"),
        )
        self.assertIn(
            "GPU_H3_REG_SP_VS_CONST_CONFIG,\n                              GPU_H3_SP_CONST_CONFIG_ENABLED",
            source,
        )
        self.assertIn(
            "GPU_H3_REG_SP_PS_CONST_CONFIG,\n                              GPU_H3_SP_CONST_CONFIG_ENABLED",
            source,
        )
        self.assertIn(
            "GPU_H2_REG_SP_PS_OUTPUT_CNTL,\n                              GPU_H3_SP_PS_OUTPUT_CNTL",
            state_emit,
        )
        self.assertLess(
            state_emit.index("GPU_H2_REG_SP_PS_MRT_REG0"),
            state_emit.index("GPU_H3_REG_SP_PS_INITIAL_TEX_LOAD_CNTL"),
        )
        self.assertLess(
            state_emit.index("GPU_H3_REG_SP_PS_INITIAL_TEX_LOAD_CNTL"),
            state_emit.index("GPU_H3_REG_SP_PS_WAVE_CNTL"),
        )
        self.assertLess(
            state_emit.index("GPU_H3_REG_SP_LB_PARAM_LIMIT"),
            state_emit.index("GPU_H3_REG_SP_REG_PROG_ID_0"),
        )
        self.assertLess(
            state_emit.index("GPU_H3_REG_SP_REG_PROG_ID_2"),
            state_emit.index("GPU_H3_REG_SP_REG_PROG_ID_3"),
        )
        self.assertIn('"gpu.h3.draw.sp_const_config_source=mesa-freedreno-a6xx-fd6-program-config-stateobj', source)
        self.assertIn('"gpu.h3.draw.sp_vs_const_config=0x%x', source)
        self.assertIn('"gpu.h3.draw.sp_ps_const_config=0x%x', source)
        self.assertIn('"gpu.h3.draw.fs_output_cntl_source=mesa-freedreno-a6xx-fd6-program-invalid-depth-sampmask-stencil-regids', source)
        self.assertIn('"gpu.h3.draw.sp_ps_output_cntl=0x%x', source)
        self.assertIn('"gpu.h3.draw.sp_frontend_prog_id_source=mesa-freedreno-a6xx-fd6-program-emit-fs-inputs-current-constant-fs-no-varyings', source)
        self.assertIn('"gpu.h3.draw.sp_ps_initial_tex_load_cntl=0x%x', source)
        self.assertIn('"gpu.h3.draw.sp_ps_wave_cntl=0x%x', source)
        self.assertIn('"gpu.h3.draw.sp_lb_param_limit=0x%x', source)
        self.assertIn('"gpu.h3.draw.sp_reg_prog_id_0=0x%x', source)
        self.assertIn('"gpu.h3.draw.sp_reg_prog_id_1=0x%x', source)
        self.assertIn('"gpu.h3.draw.sp_reg_prog_id_2=0x%x', source)

    def test_builder_manifest_records_sp_frontend_prog_id_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3270-sp-const-output-plus-v3271-live-no-pixel-and-a6xx-sp-frontend-diff"',
            source,
        )
        self.assertIn('"sp_const_config_source": SP_CONST_CONFIG_SOURCE', source)
        self.assertIn('"sp_const_config_value": SP_CONST_CONFIG_VALUE', source)
        self.assertIn('"sp_ps_output_cntl_source": SP_PS_OUTPUT_CNTL_SOURCE', source)
        self.assertIn('"sp_ps_output_cntl_value": SP_PS_OUTPUT_CNTL_VALUE', source)
        self.assertIn('"sp_frontend_prog_id_source": SP_FRONTEND_PROG_ID_SOURCE', source)
        self.assertIn('"sp_ps_initial_tex_load_cntl_value": SP_PS_INITIAL_TEX_LOAD_CNTL_VALUE', source)
        self.assertIn('"sp_ps_wave_cntl_value": SP_PS_WAVE_CNTL_VALUE', source)
        self.assertIn('"sp_lb_param_limit_value": SP_LB_PARAM_LIMIT_VALUE', source)
        self.assertIn('"sp_reg_prog_id_values": {', source)
        self.assertIn('"state_reg_writes_expected": 106', source)
        self.assertIn('"pm4_dwords_expected": 282', source)
        self.assertIn("preserve-v3268-ramdisk-overlay-v3272-init-helper-engine", source)
        self.assertIn("STALE_V3268_ENGINE_RAMDISK_PATH", source)


if __name__ == "__main__":
    unittest.main()
