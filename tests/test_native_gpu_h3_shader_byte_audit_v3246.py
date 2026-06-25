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
                "204cc002_3f800000",
                "204cc003_3f800000",
                "03000000_00000000",
            ] + ["00000000_00000000"] * 13,
        )
        self.assertEqual(
            [entry["word"] for entry in result["decoded"]["fs_shader"]],
            [
                "20444000_3f800000",
                "03000000_00000000",
            ] + ["00000000_00000000"] * 14,
        )

    def test_half_precision_and_vpc_position_checks_are_closed(self) -> None:
        result = audit.run_audit(ir3_disasm="/missing/ir3-disasm")
        checks = result["checks"]

        self.assertTrue(checks["fs_writes_full_f32_r0x"])
        self.assertTrue(checks["vs_uses_mesa_reference_u32_z_w_instrlen1"])
        self.assertEqual(checks["vs_shader_instrlen"], 1)
        self.assertEqual(checks["fs_shader_instrlen"], 1)
        self.assertEqual(checks["ir3_instr_align"], 16)
        self.assertFalse(checks["sp_ps_output_reg0_half_precision"])
        self.assertTrue(checks["fs_full_precision_matches_ps_output"])
        self.assertEqual(checks["sp_ps_output_reg0_regid"], 0)
        self.assertEqual(checks["sp_ps_mrt_reg0_color_format"], 0x4A)
        self.assertFalse(checks["sp_ps_mrt_reg0_color_uint"])
        self.assertTrue(checks["sp_ps_mrt_reg0_has_no_half_precision_field"])

        self.assertEqual(checks["sp_vs_output_reg0_regid"], 0)
        self.assertEqual(checks["sp_vs_output_reg0_compmask"], 0xF)
        self.assertEqual(checks["sp_vs_vpc_dest_reg0_outloc0"], 0)
        self.assertEqual(checks["vpc_vs_cntl_stride_in_vpc"], 4)
        self.assertEqual(checks["vpc_vs_cntl_positionloc"], 0)
        self.assertEqual(checks["vpc_vs_cntl_psizeloc"], 0xFF)
        self.assertTrue(checks["position_is_vpc_vs_cntl_not_siv"])
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
