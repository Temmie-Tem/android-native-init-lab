from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3238_gpu_g0_fwclass_materialize_prep_probe.py"
)


class NativeGpuG0FwclassMaterializeSourceV3238Tests(unittest.TestCase):
    def test_v3238_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3238")
        self.assertEqual(runner.INIT_VERSION, "0.11.46")
        self.assertEqual(runner.INIT_BUILD, "v3238-gpu-g0-fwclass-materialize-prep-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3232_gpu_h3_static_context_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.46", required)
        self.assertIn(b"v3238-gpu-g0-fwclass-materialize-prep-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-fwclass-materialize-r1-footprint2-mov-f32-shader",
            required,
        )
        self.assertIn(b"gpu.g0.materialize.fwclass_prepare_attempted=1", required)
        self.assertIn(b"gpu.g0.materialize.fwclass_prepare_rc=%d", required)
        self.assertIn(b"gpu.g0.fwclass_prepare.result=ok", required)
        self.assertIn(
            b"gpu.h3.draw.shader_payload=hand-assembled-ir3-r1-output-mov-f32-vs-position-fs-color-no-full-compiler",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.shader_output_source=mesa-freedreno-a6xx-fd6-emit-vpc-emit-fs-outputs-regid-map",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.shader_mode_source=mesa-freedreno-a6xx-fd6-emit-shader-regs-sp-tpl1-mode",
            required,
        )
        self.assertIn(b"gpu.h3.draw.sp_mode_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.tpl1_mode_cntl=0x%x", required)
        self.assertIn(
            b"gpu.h3.draw.fragment_input_state_source=mesa-freedreno-a6xx-emit-fs-inputs-default-zero",
            required,
        )
        self.assertIn(b"gpu.h3.draw.gras_cl_interp_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.rb_interp_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.rb_ps_input_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.rb_ps_samplefreq_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_lrz_ps_input_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_lrz_ps_samplefreq_cntl=0x%x", required)
        self.assertIn(
            b"gpu.h3.draw.mrt_component_mask_source=mesa-freedreno-a6xx-mrt-components-full-rt0",
            required,
        )
        self.assertIn(b"gpu.h3.draw.color_output_mask=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_vs_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_vs_clip_cull_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_vs_clip_cull_cntl_v2=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_cl_vs_clip_cull_distance=0x%x", required)
        self.assertIn(
            b"gpu.h3.draw.vpc_lm_siv_source=mesa-freedreno-a6xx-emit-vpc-position-only-siv",
            required,
        )
        self.assertIn(b"gpu.h3.draw.vpc_varying_lm_transfer_cntl0=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_varying_lm_transfer_cntl1=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_varying_lm_transfer_cntl2=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_varying_lm_transfer_cntl3=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_vs_siv_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_vs_siv_cntl_v2=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_su_vs_siv_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vs_shader_dwords=%u", required)
        self.assertIn(b"gpu.h3.draw.fs_shader_dwords=%u", required)
        self.assertIn(b"gpu.h3.draw.vs_output_regid=0x%x", required)
        self.assertIn(b"gpu.h3.draw.ps_output_regid=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_vs_output_reg0=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_fullregfootprint=%u", required)
        self.assertIn(b"gpu.h3.draw.gras_su_conservative_ras_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_unknown_9210=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_so_override=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_rast_stream_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.pc_stereo_rendering_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.tpl1_ps_swizzle_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_reg_prog_id_3=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_sc_ras_msaa_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_sc_dest_msaa_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_sc_screen_scissor_cntl=0x%x", required)
        self.assertNotIn(b"first-triangle-h3-sp-cntl0-linkage-mov-f32-shader", required)
        self.assertNotIn(b"first-triangle-h3-shader-mode-mov-f32-shader", required)
        self.assertNotIn(b"first-triangle-h3-fragment-input-state-mov-f32-shader", required)

    def test_dispatch_programs_mesa_fwclass_materialize_registers(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn('gpu.g0.materialize.fwclass_prepare_attempted=1', source)
        self.assertIn("prep_rc = gpu_g0_fwclass_prepare();", source)
        self.assertIn('gpu.g0.materialize.fwclass_prepare_rc=%d', source)
        self.assertLess(
            source.index("prep_rc = gpu_g0_fwclass_prepare();"),
            source.index("rc = gpu_g0_read_sysfs_dev(&major_num, &minor_num);"),
        )
        self.assertIn("#define GPU_H3_REG_SP_MODE_CNTL 0xab00U", source)
        self.assertIn("#define GPU_H3_SP_FULLREGFOOTPRINT 2U", source)
        self.assertIn("#define GPU_H3_VS_SHADER_DWORDS 12U", source)
        self.assertIn("#define GPU_H3_FS_SHADER_DWORDS 8U", source)
        self.assertIn("#define GPU_H3_VS_OUTPUT_REGID 0U", source)
        self.assertIn("#define GPU_H3_PS_OUTPUT_REGID 0U", source)
        self.assertIn("#define GPU_H3_SP_VS_OUTPUT_REG0", source)
        self.assertIn("#define GPU_H3_IR3_MOV_F32F32_R1X_R0X_LO 0x00000000U", source)
        self.assertIn("#define GPU_H3_IR3_MOV_F32F32_R1Y_R0Y_LO 0x00000001U", source)
        self.assertIn("#define GPU_H3_IR3_MOV_F32F32_R1X_R0X_HI 0x20044004U", source)
        self.assertIn("#define GPU_H3_IR3_MOV_F32F32_R1Y_R0Y_HI 0x20044005U", source)
        self.assertIn("#define GPU_H3_IR3_MOV_F32F32_R1X_HI 0x20444004U", source)
        self.assertIn("#define GPU_H3_IR3_MOV_F32F32_R1Z_HI 0x20444006U", source)
        self.assertIn("#define GPU_H3_IR3_MOV_F32F32_R1W_HI 0x20444007U", source)
        self.assertIn("#define GPU_H3_REG_TPL1_MODE_CNTL 0xb309U", source)
        self.assertIn("#define GPU_H3_SP_MODE_CNTL 0x00000005U", source)
        self.assertIn("#define GPU_H3_TPL1_MODE_CNTL 0x000000a2U", source)
        self.assertIn("#define GPU_H2_REG_GRAS_CL_INTERP_CNTL 0x8005U", source)
        self.assertIn("#define GPU_H2_REG_GRAS_LRZ_PS_INPUT_CNTL 0x8101U", source)
        self.assertIn("#define GPU_H2_REG_GRAS_LRZ_PS_SAMPLEFREQ_CNTL 0x8109U", source)
        self.assertIn("#define GPU_H2_REG_RB_INTERP_CNTL 0x8809U", source)
        self.assertIn("#define GPU_H2_REG_RB_PS_INPUT_CNTL 0x880aU", source)
        self.assertIn("#define GPU_H2_REG_RB_PS_SAMPLEFREQ_CNTL 0x8810U", source)
        self.assertIn("#define GPU_H2_REG_GRAS_SU_VS_SIV_CNTL 0x809bU", source)
        self.assertIn("#define GPU_H2_REG_VPC_VS_SIV_CNTL 0x9104U", source)
        self.assertIn("#define GPU_H2_REG_VPC_VARYING_LM_TRANSFER_CNTL0 0x9212U", source)
        self.assertIn("#define GPU_H2_REG_VPC_VS_SIV_CNTL_V2 0x9314U", source)
        self.assertIn("#define GPU_H3_REG_GRAS_SU_CONSERVATIVE_RAS_CNTL 0x8099U", source)
        self.assertIn("#define GPU_H3_REG_VPC_UNKNOWN_9210 0x9210U", source)
        self.assertIn("#define GPU_H3_REG_VPC_SO_OVERRIDE 0x9306U", source)
        self.assertIn("#define GPU_H3_REG_VPC_RAST_STREAM_CNTL 0x9980U", source)
        self.assertIn("#define GPU_H3_REG_PC_STEREO_RENDERING_CNTL 0x9b07U", source)
        self.assertIn("#define GPU_H3_REG_TPL1_PS_SWIZZLE_CNTL 0xb183U", source)
        self.assertIn("#define GPU_H3_REG_SP_REG_PROG_ID_3 0xb986U", source)
        self.assertIn("#define GPU_H3_GRAS_CL_INTERP_CNTL 0x00000000U", source)
        self.assertIn("#define GPU_H3_RB_PS_INPUT_CNTL 0x00000000U", source)
        self.assertIn("#define GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL0 0xfffffff0U", source)
        self.assertIn("#define GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL1 0xffffffffU", source)
        self.assertIn("#define GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL2 0xffffffffU", source)
        self.assertIn("#define GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL3 0xffffffffU", source)
        self.assertIn("#define GPU_H3_VPC_VS_SIV_CNTL 0x0000ffffU", source)
        self.assertIn("#define GPU_H3_VPC_VS_SIV_CNTL_V2 0x0000ffffU", source)
        self.assertIn("#define GPU_H3_GRAS_SU_VS_SIV_CNTL 0x00000000U", source)
        self.assertIn("#define GPU_H3_GRAS_SU_CONSERVATIVE_RAS_CNTL 0x00000000U", source)
        self.assertIn("#define GPU_H3_VPC_SO_OVERRIDE 0x00000001U", source)
        self.assertIn("#define GPU_H3_SP_INVALID_REG 0xfcU", source)
        self.assertIn("#define GPU_H3_SP_REG_PROG_ID_3", source)
        self.assertIn("GPU_H3_REG_SP_MODE_CNTL,\n                              GPU_H3_SP_MODE_CNTL", source)
        self.assertIn("GPU_H3_REG_TPL1_MODE_CNTL,\n                              GPU_H3_TPL1_MODE_CNTL", source)
        self.assertIn(
            "GPU_H2_REG_GRAS_CL_INTERP_CNTL,\n                              GPU_H3_GRAS_CL_INTERP_CNTL",
            source,
        )
        self.assertIn(
            "GPU_H2_REG_GRAS_LRZ_PS_INPUT_CNTL,\n                              GPU_H3_GRAS_LRZ_PS_INPUT_CNTL",
            source,
        )
        self.assertIn(
            "GPU_H2_REG_RB_INTERP_CNTL,\n                              GPU_H3_RB_INTERP_CNTL",
            source,
        )
        self.assertIn(
            "GPU_H2_REG_RB_PS_SAMPLEFREQ_CNTL,\n                              GPU_H3_RB_PS_SAMPLEFREQ_CNTL",
            source,
        )
        self.assertIn(
            "GPU_H2_REG_GRAS_SU_VS_SIV_CNTL,\n                              GPU_H3_GRAS_SU_VS_SIV_CNTL",
            source,
        )
        self.assertIn(
            "GPU_H3_REG_GRAS_SU_CONSERVATIVE_RAS_CNTL,\n                              GPU_H3_GRAS_SU_CONSERVATIVE_RAS_CNTL",
            source,
        )
        self.assertIn(
            "GPU_H2_REG_VPC_VARYING_LM_TRANSFER_CNTL0,\n                              GPU_H3_VPC_VARYING_LM_TRANSFER_CNTL0",
            source,
        )
        self.assertIn(
            "GPU_H2_REG_VPC_VS_SIV_CNTL,\n                              GPU_H3_VPC_VS_SIV_CNTL",
            source,
        )
        self.assertIn(
            "GPU_H2_REG_VPC_VS_SIV_CNTL_V2,\n                              GPU_H3_VPC_VS_SIV_CNTL_V2",
            source,
        )
        self.assertIn(
            "GPU_H3_REG_VPC_SO_OVERRIDE,\n                              GPU_H3_VPC_SO_OVERRIDE",
            source,
        )
        self.assertIn(
            "GPU_H3_REG_VPC_RAST_STREAM_CNTL,\n                              GPU_H3_VPC_RAST_STREAM_CNTL",
            source,
        )
        self.assertIn(
            "GPU_H3_REG_PC_STEREO_RENDERING_CNTL,\n                              GPU_H3_PC_STEREO_RENDERING_CNTL",
            source,
        )
        self.assertIn(
            "GPU_H3_REG_TPL1_PS_SWIZZLE_CNTL,\n                              GPU_H3_TPL1_PS_SWIZZLE_CNTL",
            source,
        )
        self.assertIn(
            "GPU_H3_REG_SP_REG_PROG_ID_3,\n                              GPU_H3_SP_REG_PROG_ID_3",
            source,
        )
        self.assertIn("static const uint32_t vs_shader[GPU_H3_VS_SHADER_DWORDS]", source)
        self.assertIn("GPU_H3_IR3_MOV_F32F32_R0X_R0X_LO, GPU_H3_IR3_MOV_F32F32_R0X_R0X_HI", source)
        self.assertIn("GPU_H3_IR3_MOV_F32F32_R0Y_R0Y_LO, GPU_H3_IR3_MOV_F32F32_R0Y_R0Y_HI", source)
        self.assertIn("GPU_H3_IR3_F32_0_LO, GPU_H3_IR3_MOV_F32F32_R0Z_HI", source)
        self.assertIn("GPU_H3_IR3_F32_1_LO, GPU_H3_IR3_MOV_F32F32_R0W_HI", source)
        self.assertIn("static const uint32_t fs_shader[GPU_H3_FS_SHADER_DWORDS]", source)
        self.assertIn("GPU_H3_IR3_F32_1_LO, GPU_H3_IR3_MOV_F32F32_R0X_HI", source)
        self.assertIn("GPU_H3_SP_VS_OUTPUT_REG0", source)
        self.assertIn("GPU_H3_PS_OUTPUT_REGID", source)
        self.assertIn(
            '"gpu.h3.draw.shader_mode_source=mesa-freedreno-a6xx-fd6-emit-shader-regs-sp-tpl1-mode',
            source,
        )
        self.assertIn(
            '"gpu.h3.draw.fragment_input_state_source=mesa-freedreno-a6xx-emit-fs-inputs-default-zero',
            source,
        )
        self.assertIn(
            '"gpu.h3.draw.vpc_lm_siv_source=mesa-freedreno-a6xx-emit-vpc-position-only-siv',
            source,
        )
        self.assertIn(
            '"gpu.h3.draw.shader_output_source=mesa-freedreno-a6xx-fd6-emit-vpc-emit-fs-outputs-regid-map',
            source,
        )
        self.assertIn('"gpu.h3.draw.sp_fullregfootprint=%u', source)
        self.assertIn('"gpu.h3.draw.vs_shader_dwords=%u', source)
        self.assertIn('"gpu.h3.draw.fs_shader_dwords=%u', source)
        self.assertIn('"gpu.h3.draw.vs_output_regid=0x%x', source)
        self.assertIn('"gpu.h3.draw.ps_output_regid=0x%x', source)
        self.assertIn('"gpu.h3.draw.sp_vs_output_reg0=0x%x', source)
        self.assertIn('"gpu.h3.draw.sp_mode_cntl=0x%x', source)
        self.assertIn('"gpu.h3.draw.tpl1_mode_cntl=0x%x', source)
        self.assertIn('"gpu.h3.draw.rb_ps_input_cntl=0x%x', source)
        self.assertIn('"gpu.h3.draw.vpc_vs_siv_cntl=0x%x', source)
        self.assertIn('"gpu.h3.draw.gras_su_vs_siv_cntl=0x%x', source)
        self.assertIn('"gpu.h3.draw.vpc_so_override=0x%x', source)
        self.assertIn('"gpu.h3.draw.sp_reg_prog_id_3=0x%x', source)
        self.assertIn("#define GPU_H3_COLOR_OUTPUT_MASK 0xfU", source)
        self.assertIn("uint32_t rb_mrt_control = (color_output_mask & 0xfU) << 7;", source)
        self.assertIn("GPU_H2_REG_RB_PS_OUTPUT_MASK,\n                              color_output_mask", source)
        self.assertIn("GPU_H2_REG_SP_PS_OUTPUT_MASK,\n                              color_output_mask", source)
        self.assertIn('"gpu.h3.draw.color_output_mask=0x%x', source)

    def test_builder_manifest_records_fwclass_materialize_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"source_baseline": "v3234-r1-shader-output-source-on-v3232-ramdisk-base"', source)
        self.assertIn('"scope": "first-triangle-h3-fwclass-materialize-r1-footprint2-mov-f32-shader"', source)
        self.assertIn("verify-fresh-boot-fwclass-path-before-h3", source)
        self.assertIn("gpu-h3-auto-fwclass-materialize-r1-footprint2-mov-f32-shader-timeout-guard", source)
        self.assertIn('"shader_payload": "hand-assembled-ir3-r1-output-mov-f32-vs-position-fs-color-no-full-compiler"', source)
        self.assertIn('"shader_output_source": "Mesa A6xx fd6 emit_vpc and emit_fs_outputs output regid maps"', source)
        self.assertIn('"ir3_mov_f32f32_r1x_r0x_opcode": "0x2004400400000000"', source)
        self.assertIn('"ir3_mov_f32f32_r1y_r0y_opcode": "0x2004400500000001"', source)
        self.assertIn('"vs_shader_dwords": 12', source)
        self.assertIn('"fs_shader_dwords": 8', source)
        self.assertIn('"vs_output_regid": "0x04"', source)
        self.assertIn('"ps_output_regid": "0x04"', source)
        self.assertIn('"sp_vs_output_reg0": "0x00000f04"', source)
        self.assertIn('"sp_fullregfootprint": 2', source)
        self.assertIn('"shader_mode_source": "Mesa A6xx fd6 emit_shader_regs SP_MODE_CNTL and TPL1_MODE_CNTL"', source)
        self.assertIn('"sp_mode_cntl": "0x00000005"', source)
        self.assertIn('"tpl1_mode_cntl": "0x000000a2"', source)
        self.assertIn('"sp_vs_cntl0": "0x00100100"', source)
        self.assertIn('"sp_ps_cntl0": "0x81000100"', source)
        self.assertIn('"fragment_input_state_source": "Mesa A6xx fd6 emit_fs_inputs defaults', source)
        self.assertIn('"gras_cl_interp_cntl": "0x00000000"', source)
        self.assertIn('"rb_interp_cntl": "0x00000000"', source)
        self.assertIn('"rb_ps_input_cntl": "0x00000000"', source)
        self.assertIn('"rb_ps_samplefreq_cntl": "0x00000000"', source)
        self.assertIn('"gras_lrz_ps_input_cntl": "0x00000000"', source)
        self.assertIn('"gras_lrz_ps_samplefreq_cntl": "0x00000000"', source)
        self.assertIn('"vpc_lm_siv_source": "Mesa A6xx fd6 emit_vpc position-only linkage and SIV sentinels"', source)
        self.assertIn('"vpc_varying_lm_transfer_cntl0": "0xfffffff0"', source)
        self.assertIn('"vpc_varying_lm_transfer_cntl1": "0xffffffff"', source)
        self.assertIn('"vpc_varying_lm_transfer_cntl2": "0xffffffff"', source)
        self.assertIn('"vpc_varying_lm_transfer_cntl3": "0xffffffff"', source)
        self.assertIn('"vpc_vs_siv_cntl": "0x0000ffff"', source)
        self.assertIn('"vpc_vs_siv_cntl_v2": "0x0000ffff"', source)
        self.assertIn('"gras_su_vs_siv_cntl": "0x00000000"', source)
        self.assertIn('"static_context_source": "Mesa A6xx fd6_emit_static_context_regs no-op/disable defaults"', source)
        self.assertIn('"gras_su_conservative_ras_cntl": "0x00000000"', source)
        self.assertIn('"vpc_unknown_9210": "0x00000000"', source)
        self.assertIn('"vpc_so_override": "0x00000001"', source)
        self.assertIn('"vpc_rast_stream_cntl": "0x00000000"', source)
        self.assertIn('"pc_stereo_rendering_cntl": "0x00000000"', source)
        self.assertIn('"tpl1_ps_swizzle_cntl": "0x00000000"', source)
        self.assertIn('"sp_reg_prog_id_3": "0x0000fcfc"', source)
        self.assertIn('"state_reg_writes_expected": 88', source)
        self.assertIn('"pm4_dwords_expected": 223', source)
        self.assertIn('"color_output_mask": "0xf"', source)
        self.assertIn('"rb_ps_output_mask": "0x0000000f"', source)
        self.assertIn('"sp_ps_output_mask": "0x0000000f"', source)
        self.assertIn('"rb_mrt0_component_enable": "0x00000780"', source)
        self.assertIn("emit_shader_regs", source)
        self.assertIn("emit_fs_inputs", source)
        self.assertIn("emit_vpc", source)
        self.assertIn("preserve-v3232-ramdisk-overlay-v3238-init-helper-engine", source)
        self.assertIn('"bin/a90_doomgeneric_private_engine_v3238"', source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)
        self.assertIn("V3238 boot image too large for boot partition", source)


if __name__ == "__main__":
    unittest.main()
