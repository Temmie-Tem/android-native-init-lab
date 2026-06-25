from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


audit = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_h3_shader_byte_audit_v3246.py"
)


class NativeGpuH3ShaderByteAuditV3246Tests(unittest.TestCase):
    def test_internal_decoder_verifies_current_h3_shader_contract(self) -> None:
        result = audit.run_audit(ir3_disasm="/missing/ir3-disasm")

        self.assertTrue(result["passed"])
        self.assertFalse(result["checks"]["external_ir3_disasm_used"])
        self.assertEqual(result["mismatches"], [])
        self.assertEqual(
            [entry["disasm"] for entry in result["decoded"]["vs_shader"]],
            audit.EXPECTED_VS,
        )
        self.assertEqual(
            [entry["disasm"] for entry in result["decoded"]["fs_shader"]],
            audit.EXPECTED_FS,
        )
        self.assertEqual(
            [entry["word"] for entry in result["decoded"]["vs_shader"]],
            [
                "20044008_00000004",
                "20044009_00000005",
                "2004400a_00000006",
                "2004400b_00000007",
                "03000000_00000000",
            ] + ["00000000_00000000"] * 11,
        )
        self.assertEqual(
            [entry["word"] for entry in result["decoded"]["fs_shader"]],
            [
                "47300002_00002000",
                "47300003_00002001",
                "47300004_00002002",
                "47308005_00002003",
                "03000000_00000000",
            ] + ["00000000_00000000"] * 11,
        )

    def test_half_precision_and_vpc_position_checks_are_closed(self) -> None:
        result = audit.run_audit(ir3_disasm="/missing/ir3-disasm")
        checks = result["checks"]

        self.assertTrue(checks["fs_uses_cffdump_bary_outputs"])
        self.assertTrue(checks["vs_routes_position_to_r2_and_varying_r0"])
        self.assertEqual(checks["vs_position_source_regid"], 4)
        self.assertEqual(checks["vs_shader_instrlen"], 1)
        self.assertEqual(checks["fs_shader_instrlen"], 1)
        self.assertEqual(checks["ir3_instr_align"], 16)
        self.assertFalse(checks["sp_ps_output_reg0_half_precision"])
        self.assertTrue(checks["fs_full_precision_matches_ps_output"])
        self.assertEqual(checks["sp_ps_output_reg0_regid"], 2)
        self.assertEqual(checks["sp_ps_mrt_reg0_color_format"], 0x30)
        self.assertFalse(checks["sp_ps_mrt_reg0_color_uint"])
        self.assertTrue(checks["sp_ps_mrt_reg0_has_no_half_precision_field"])
        self.assertTrue(checks["sp_ps_mrt_reg0_matches_a640_cffdump_rgba8"])
        self.assertEqual(checks["rb_mrt0_buf_info_color_format"], 0x30)
        self.assertTrue(checks["rb_mrt0_buf_info_matches_h3_color_format"])
        self.assertEqual(checks["rb_mrt0_buf_info_tile_mode"], 0x3)
        self.assertTrue(checks["rb_mrt0_buf_info_matches_a640_cffdump_tile6_3"])
        self.assertEqual(checks["rb_render_cntl"], 0x00010010)
        self.assertEqual(checks["rb_render_cntl_flag_mrts"], 0x1)
        self.assertTrue(checks["rb_render_cntl_matches_a640_cffdump_flag_mrt0"])
        self.assertEqual(checks["color_flag_buffer_pitch"], 0x00004001)
        self.assertTrue(checks["color_flag_buffer_pitch_matches_a640_cffdump"])
        self.assertEqual(checks["rb_dbg_eco_reg"], 0x8E04)
        self.assertEqual(checks["rb_dbg_eco_cntl"], 0x04100000)
        self.assertTrue(checks["rb_dbg_eco_matches_a640_device_db"])
        self.assertEqual(checks["a640_init_magic_reg_writes"], 9)
        self.assertTrue(checks["a640_init_magic_is_nonzero_block"])
        self.assertTrue(checks["a640_nonzero_magic_all_match"])
        self.assertEqual(checks["sp_chicken_bits"], 0x00000420)
        self.assertEqual(checks["tpl1_dbg_eco_cntl"], 0x00008000)
        self.assertEqual(checks["vpc_dbg_eco_cntl"], 0x02000000)
        self.assertEqual(checks["rb_rbp_cntl"], 0x00000001)
        self.assertEqual(checks["pc_mode_magic"], 0x0000001F)
        self.assertEqual(checks["pc_power_cntl"], 0x00000001)
        self.assertEqual(checks["vfd_power_cntl"], 0x00000001)
        self.assertEqual(checks["uche_unknown_0e12"], 0x00000001)
        self.assertEqual(checks["vertex_stride"], 36)
        self.assertEqual(checks["vertex_dwords"], 27)
        self.assertEqual(checks["vertex_bytes"], 108)
        self.assertEqual(checks["vfd_cntl_0"], 0x00000303)
        self.assertEqual(checks["vfd_cntl_1"], 0xFCFCFC09)
        self.assertEqual(checks["vfd_fetch_instr0"], 0xC8200000)
        self.assertEqual(checks["vfd_fetch_instr1"], 0xC8200200)
        self.assertEqual(checks["vfd_fetch_instr2"], 0x44C00400)
        self.assertEqual(checks["vfd_dest_cntl0"], 0xF)
        self.assertEqual(checks["vfd_dest_cntl1"], 0x4F)
        self.assertEqual(checks["vfd_dest_cntl2"], 0x81)
        self.assertTrue(checks["vfd_contract_matches_a640_cffdump_draw2"])

        self.assertEqual(checks["sp_vs_output_reg0_a_regid"], 8)
        self.assertEqual(checks["sp_vs_output_reg0_a_compmask"], 0xF)
        self.assertEqual(checks["sp_vs_output_reg0_b_regid"], 0)
        self.assertEqual(checks["sp_vs_output_reg0_b_compmask"], 0xF)
        self.assertEqual(checks["sp_vs_vpc_dest_reg0_outloc0"], 0)
        self.assertEqual(checks["sp_vs_vpc_dest_reg0_outloc1"], 4)
        self.assertEqual(checks["vpc_vs_cntl_stride_in_vpc"], 8)
        self.assertEqual(checks["vpc_vs_cntl_positionloc"], 4)
        self.assertEqual(checks["vpc_vs_cntl_psizeloc"], 0xFF)
        self.assertEqual(checks["vpc_ps_cntl_numnonposvar"], 4)
        self.assertEqual(checks["vpc_ps_cntl_primidloc"], 0xFF)
        self.assertTrue(checks["vpc_ps_cntl_varying"])
        self.assertEqual(checks["vpc_ps_cntl_viewidloc"], 0xFF)
        self.assertTrue(checks["position_is_vpc_loc4_not_siv"])
        self.assertEqual(checks["vpc_vs_siv_cntl_layerloc"], 0xFF)
        self.assertEqual(checks["vpc_vs_siv_cntl_viewloc"], 0xFF)

    def test_real_mesa_ir3_disasm_when_available(self) -> None:
        ir3_disasm = Path("/tmp/a90-mesa-h3-build-ir3/src/freedreno/isa/ir3-disasm")
        if not ir3_disasm.exists():
            self.skipTest("Mesa ir3-disasm not built in /tmp")

        result = audit.run_audit(ir3_disasm=str(ir3_disasm), require_ir3_disasm=True)

        self.assertTrue(result["passed"])
        self.assertTrue(result["checks"]["external_ir3_disasm_used"])
        self.assertEqual(
            [entry["mesa_ir3_disasm"] for entry in result["decoded"]["vs_shader"]],
            audit.EXPECTED_VS,
        )
        self.assertEqual(
            [entry["mesa_ir3_disasm"] for entry in result["decoded"]["fs_shader"]],
            audit.EXPECTED_FS,
        )


if __name__ == "__main__":
    unittest.main()
