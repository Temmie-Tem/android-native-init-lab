from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from _loader import load_script


diff = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_h3_cffdump_diff_v3286.py"
)


SUMMARY_FIXTURE = """
cmdstream[0]: 265 dwords
    draw[1] register values
!+  00000000            RB_RENDER_CNTL: { 0 }
    draw[2] register values
!+  000000c0            GRAS_CL_CNTL: { ZERO_GB_SCALE_Z | VP_CLIP_CODE_IGNORE }
!+  00000001            GRAS_CL_INTERP_CNTL: { IJ_PERSP_PIXEL | COORD_MASK = 0 }
!+  0007fdff            GRAS_CL_GUARDBAND_CLIP_ADJ: { HORZ = 511 | VERT = 511 }
!+  00000814            GRAS_SU_CNTL: { FRONT_CW }
    00000002            GRAS_SC_CNTL: { RASTER_MODE = TYPE_TILED }
!+  00000004            GRAS_SC_DEST_MSAA_CNTL: { SAMPLES = MSAA_ONE | MSAA_DISABLE }
    00000000            GRAS_LRZ_CNTL: { DIR = 0 }
!+  00010010            RB_RENDER_CNTL: { FLAG_MRTS = 0x1 }
!+  00000004            RB_DEST_MSAA_CNTL: { SAMPLES = MSAA_ONE | MSAA_DISABLE }
 +   00000401            RB_INTERP_CNTL: { IJ_PERSP_PIXEL | INTERP_EN }
 +   00000000            RB_PS_OUTPUT_CNTL: { 0 }
!+  00000001            RB_PS_MRT_CNTL: { MRT = 1 }
!+  0000000f            RB_PS_OUTPUT_MASK: { RT0 = 0xf }
!+  00000780            RB_MRT[0].CONTROL: { COMPONENT_ENABLE = 0xf }
!+  08040804            RB_MRT[0].BLEND_CONTROL: { 0x8040804 }
!+  00000330            RB_MRT[0].BUF_INFO: { FMT6_8_8_8_8_UNORM }
!+  00000010            RB_MRT[0].PITCH: 1024
!+  00001000            RB_MRT[0].ARRAY_PITCH: 262144
 +   00000000            RB_MRT[0].BASE_GMEM: 0
!+  ffff0100            RB_BLEND_CNTL: { SAMPLE_MASK = 0xffff }
!+  00004001            RB_COLOR_FLAG_BUFFER[0].PITCH: { PITCH = 64 }
!+  00ffff00            VPC_VS_CLIP_CULL_CNTL: { 0 }
!+  0000ffff            VPC_VS_SIV_CNTL: { 0 }
!+  00000003            VPC_RAST_CNTL: { MODE = POLYMODE6_TRIANGLES }
!+  00ff0408            VPC_VS_CNTL: { STRIDE_IN_VPC = 8 }
!+  ff01ff04            VPC_PS_CNTL: { NUMNONPOSVAR = 4 }
    00000000            VPC_SO_OVERRIDE: { 0 }
!+  ffffffff            PC_RESTART_INDEX: 4294967295
    0000001f            PC_MODE_CNTL: { COUNT1 = 31 }
    00000000            VPC_RAST_STREAM_CNTL: { STREAM = 0 }
!+  00000003            PC_DGEN_RAST_CNTL: { MODE = POLYMODE6_TRIANGLES }
 +   00000000            PC_CNTL: { 0 }
!+  00000008            PC_VS_CNTL: { STRIDE_IN_VPC = 8 }
!+  00000303            VFD_CNTL_0: { FETCH_CNT = 3 | DECODE_CNT = 3 }
!+  fcfcfc09            VFD_CNTL_1: { REGID4VTX = r2.y }
!+  00000024            VFD_VERTEX_BUFFER[0].STRIDE: 36
!+  c8200000            VFD_FETCH_INSTR[0].INSTR: { FORMAT = FMT6_32_32_32_32_FLOAT }
!+  00000001            VFD_FETCH_INSTR[0].STEP_RATE: 1
!+  c8200200            VFD_FETCH_INSTR[0x1].INSTR: { OFFSET = 0x10 }
!+  44c00400            VFD_FETCH_INSTR[0x2].INSTR: { OFFSET = 0x20 }
!+  0000000f            VFD_DEST_CNTL[0].INSTR: { WRITEMASK = 0xf }
!+  0000004f            VFD_DEST_CNTL[0x1].INSTR: { WRITEMASK = 0xf }
!+  00000081            VFD_DEST_CNTL[0x2].INSTR: { WRITEMASK = 0x1 }
!+  80100180            SP_VS_CNTL_0: { FULLREGFOOTPRINT = 3 }
!+  00000002            SP_VS_OUTPUT_CNTL: { OUT = 2 }
!+  0f000f08            SP_VS_OUTPUT[0].REG: { A_REGID = r2.x }
!+  00000400            SP_VS_VPC_DEST[0].REG: { OUTLOC1 = 4 }
!+  00000100            SP_VS_CONFIG: { ENABLED }
!+  00000001            SP_VS_INSTR_SIZE: 1
!+  81500100            SP_PS_CNTL_0: { FULLREGFOOTPRINT = 2 }
!+  00000100            SP_BLEND_CNTL: { INDEPENDENT_BLEND_EN }
!+  0000000f            SP_PS_OUTPUT_MASK: { RT0 = 0xf }
!+  fcfcfc00            SP_PS_OUTPUT_CNTL: { DEPTH_REGID = r63.x }
!+  00000001            SP_PS_MRT_CNTL: { MRT = 1 }
!+  00000002            SP_PS_OUTPUT[0].REG: { REGID = r0.z }
!+  00000030            SP_PS_MRT[0].REG: { COLOR_FORMAT = FMT6_8_8_8_8_UNORM }
!+  00007fc0            SP_PS_INITIAL_TEX_LOAD_CNTL: { COUNT = 0 }
    00000005            SP_MODE_CNTL: { ISAMMODE = ISAMMODE_GL }
!+  00000100            SP_PS_CONFIG: { ENABLED }
!+  00000001            SP_PS_INSTR_SIZE: 1
!+  00000101            SP_VS_CONST_CONFIG: { CONSTLEN = 4 | ENABLED }
!+  00000003            SP_PS_WAVE_CNTL: { THREADSIZE = THREAD128 | VARYINGS }
!+  00000007            SP_LB_PARAM_LIMIT: { PRIMALLOCTHRESHOLD = 7 }
!+  fcfcfcfc            SP_REG_PROG_ID_0: { 0 }
!+  fcfcfc00            SP_REG_PROG_ID_1: { IJ_PERSP_PIXEL = r0.x }
!+  fcfcfcfc            SP_REG_PROG_ID_2: { 0 }
 +   000000fc            SP_REG_PROG_ID_3: { LINELENGTHREGID = r63.x }
!+? 0000009f            SP_UPDATE_CNTL: { VS_STATE | FS_STATE }
!+  00000100            SP_PS_CONST_CONFIG: { CONSTLEN = 0 | ENABLED }
    draw[3] register values
!+  00000000            RB_RENDER_CNTL: { 0 }
"""


class NativeGpuH3CffdumpDiffV3286Tests(unittest.TestCase):
    def test_parser_normalizes_hex_array_indices(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = Path(tmp) / "summary.txt"
            summary.write_text(SUMMARY_FIXTURE, encoding="utf-8")

            regs = diff.parse_cffdump_draw_registers(summary, draw_index=2)

        self.assertEqual(regs["VFD_FETCH_INSTR[1].INSTR"], 0xC8200200)
        self.assertEqual(regs["VFD_FETCH_INSTR[2].INSTR"], 0x44C00400)
        self.assertEqual(regs["VFD_DEST_CNTL[1].INSTR"], 0x4F)
        self.assertEqual(regs["VFD_DEST_CNTL[2].INSTR"], 0x81)

    def test_run_diff_classifies_remaining_h3_deltas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = Path(tmp) / "summary.txt"
            summary.write_text(SUMMARY_FIXTURE, encoding="utf-8")
            rd = Path(tmp) / "triangle.rd"
            rd.write_bytes(b"rd-fixture")

            result = diff.run_diff(summary_path=summary, rd_path=rd)

        self.assertEqual(result["cycle"], "V3286")
        self.assertEqual(result["scope"], "gpu-h3-cffdump-current-state-diff")
        self.assertTrue(result["passed"])
        self.assertTrue(result["checks"]["cffdump_summary_exists"])
        self.assertTrue(result["checks"]["rd_exists"])
        self.assertTrue(result["checks"]["no_device_flash_required"])
        self.assertGreater(result["checks"]["matched_core_count"], 30)
        self.assertEqual(result["checks"]["mismatched_core_count"], 0)
        self.assertGreater(result["checks"]["candidate_delta_count"], 0)
        self.assertEqual(
            [candidate["name"] for candidate in result["top_candidates"]],
            [
                "vfd_fetch_decode_shader_contract",
                "sp_rb_blend_output_state_group",
                "sp_vs_const_config_shader_contract",
                "sp_reg_prog_id_3_foveation_quality",
            ],
        )

        vfd = result["top_candidates"][0]
        self.assertEqual(vfd["classification"], "structural_shader_vfd_coupled")
        self.assertEqual(vfd["reference"]["VFD_CNTL_0"], 0x303)
        self.assertEqual(vfd["current_h3"]["VFD_CNTL_0"], 0x303)
        self.assertEqual(vfd["reference"]["VFD_VERTEX_BUFFER[0].STRIDE"], 36)
        self.assertEqual(vfd["current_h3"]["VFD_VERTEX_BUFFER[0].STRIDE"], 36)
        self.assertEqual(vfd["reference"]["VFD_DEST_CNTL[0].INSTR"], 0xF)
        self.assertEqual(vfd["current_h3"]["VFD_DEST_CNTL[0].INSTR"], 0xF)

        blend = result["top_candidates"][1]
        self.assertEqual(blend["classification"], "direct_sysmem_compatible_output_state")
        self.assertEqual(blend["reference"]["SP_BLEND_CNTL"], 0x100)
        self.assertEqual(blend["current_h3"]["SP_BLEND_CNTL"], 0x100)
        self.assertEqual(blend["reference"]["RB_BLEND_CNTL"], 0xFFFF0100)
        self.assertEqual(blend["current_h3"]["RB_BLEND_CNTL"], 0xFFFF0100)
        self.assertEqual(blend["reference"]["RB_MRT[0].BLEND_CONTROL"], 0x08040804)
        self.assertEqual(blend["current_h3"]["RB_MRT[0].BLEND_CONTROL"], 0x08040804)

    def test_reference_matched_core_keeps_already_closed_hypotheses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            summary = Path(tmp) / "summary.txt"
            summary.write_text(SUMMARY_FIXTURE, encoding="utf-8")

            result = diff.run_diff(summary_path=summary, rd_path=Path(tmp) / "missing.rd")

        matched = {row["register"]: row for row in result["matched_core"]}
        self.assertEqual(matched["RB_RENDER_CNTL"]["current_h3"], 0x00010010)
        self.assertEqual(matched["RB_MRT[0].CONTROL"]["current_h3"], 0x780)
        self.assertEqual(matched["RB_MRT[0].BUF_INFO"]["current_h3"], 0x330)
        self.assertEqual(matched["SP_PS_OUTPUT_CNTL"]["current_h3"], 0xFCFCFC00)
        self.assertEqual(matched["SP_PS_MRT[0].REG"]["current_h3"], 0x30)
        self.assertEqual(matched["VPC_VS_CNTL"]["current_h3"], 0x00FF0408)
        self.assertEqual(matched["VPC_PS_CNTL"]["current_h3"], 0xFF01FF04)

        excluded = {entry["name"]: entry for entry in result["excluded_or_contextual_differences"]}
        self.assertIn("target_size_dependent_surface_values", excluded)
        self.assertIn("gmem_vs_direct_sysmem_path_values", excluded)


if __name__ == "__main__":
    unittest.main()
