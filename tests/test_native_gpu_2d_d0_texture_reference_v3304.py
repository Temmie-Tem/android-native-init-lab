from __future__ import annotations

import unittest

from _loader import load_script


recon = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_2d_d0_texture_reference_v3304.py"
)


class NativeGpu2dD0TextureReferenceV3304Tests(unittest.TestCase):
    def test_d0_texture_reference_recon_passes_against_staged_mesa_sources(self) -> None:
        result = recon.run_recon()

        self.assertEqual(result["cycle"], "V3304")
        self.assertEqual(result["scope"], "gpu-2d-d0-texture-reference-recon")
        self.assertTrue(result["passed"])
        self.assertTrue(result["checks"]["d0_texture_reference_recon_passed"])
        self.assertEqual(result["offset_mismatches"], {})
        self.assertEqual(result["pm4_mismatches"], {})

    def test_fs_texture_register_offsets_match_a640_reference(self) -> None:
        result = recon.run_recon()
        offsets = result["actual_reg_offsets"]

        self.assertEqual(offsets["SP_PS_CONFIG"], 0xAB04)
        self.assertEqual(offsets["SP_PS_INSTR_SIZE"], 0xAB05)
        self.assertEqual(offsets["SP_PS_INITIAL_TEX_LOAD_CNTL"], 0xA99E)
        self.assertEqual(offsets["SP_PS_INITIAL_TEX_LOAD"], 0xA99F)
        self.assertEqual(offsets["SP_PS_INITIAL_TEX_INDEX"], 0xA9A3)
        self.assertEqual(offsets["SP_PS_TSIZE"], 0xA9A7)
        self.assertEqual(offsets["SP_PS_SAMPLER_BASE"], 0xA9E0)
        self.assertEqual(offsets["SP_PS_TEXMEMOBJ_BASE"], 0xA9E4)
        self.assertEqual(offsets["SP_UPDATE_CNTL"], 0xBB08)
        self.assertEqual(offsets["TPL1_GFX_BORDER_COLOR_BASE"], 0xB302)
        self.assertEqual(offsets["TPL1_WINDOW_OFFSET"], 0xB307)
        self.assertEqual(offsets["TPL1_MODE_CNTL"], 0xB309)

    def test_pm4_opcodes_and_state_enums_are_source_verified(self) -> None:
        result = recon.run_recon()
        values = result["actual_pm4_values"]

        self.assertEqual(values["CP_LOAD_STATE6_FRAG"], 0x34)
        self.assertEqual(values["CP_SET_DRAW_STATE"], 0x43)
        self.assertEqual(values["CP_DRAW_INDX_OFFSET"], 0x38)
        self.assertEqual(values["CP_WAIT_FOR_IDLE"], 0x26)
        self.assertEqual(values["SB6_FS_TEX"], 0x04)
        self.assertEqual(values["SB6_FS_SHADER"], 0x0C)
        self.assertEqual(values["ST6_SHADER"], 0)
        self.assertEqual(values["ST6_CONSTANTS"], 1)
        self.assertEqual(values["SS6_INDIRECT"], 2)

    def test_descriptor_contract_matches_fd6_texture_emit(self) -> None:
        result = recon.run_recon()
        stages = {stage["stage"]: stage for stage in result["ordered_envelope"]}

        sampler = stages["fs_sampler_descriptor"]
        self.assertEqual(sampler["descriptor_dwords"], 4)
        self.assertEqual(sampler["registers"], ["SP_PS_SAMPLER_BASE"])
        self.assertEqual(sampler["packet"], "CP_LOAD_STATE6_FRAG")
        self.assertEqual(sampler["state_type"], "ST6_SHADER")
        self.assertEqual(sampler["state_block"], "SB6_FS_TEX")

        texture = stages["fs_texture_descriptor"]
        self.assertEqual(texture["descriptor_dwords"], 16)
        self.assertEqual(texture["registers"], ["SP_PS_TEXMEMOBJ_BASE", "SP_PS_TSIZE"])
        self.assertEqual(texture["packet"], "CP_LOAD_STATE6_FRAG")
        self.assertEqual(texture["state_type"], "ST6_CONSTANTS")
        self.assertEqual(texture["state_block"], "SB6_FS_TEX")

    def test_fs_program_config_declares_texture_and_sampler_use(self) -> None:
        result = recon.run_recon()

        self.assertTrue(result["checks"]["fs_program_config_confirmed"])
        self.assertTrue(result["program_markers"]["A6XX_SP_PS_CONFIG(.dword = sp_xs_config(state->fs))"])
        self.assertTrue(result["program_markers"]["A6XX_SP_VS_CONFIG_NTEX(v->num_samp)"])
        self.assertTrue(result["program_markers"]["A6XX_SP_VS_CONFIG_NSAMP(v->num_samp)"])
        self.assertTrue(result["program_markers"][".fs_state = true"])

    def test_ir3_cat5_sam_contract_is_fixed_for_d1_shader(self) -> None:
        result = recon.run_recon()
        cat5 = result["cat5_sam_contract"]

        self.assertTrue(cat5["valid"])
        self.assertTrue(cat5["has_sam_bitset"])
        self.assertTrue(cat5["sam_has_sampler"])
        self.assertTrue(cat5["sam_has_texture"])
        self.assertEqual(cat5["sam_pattern"], "00011")
        self.assertTrue(cat5["instruction_has_samp_field"])
        self.assertTrue(cat5["instruction_has_tex_field"])
        self.assertTrue(cat5["non_bindless_uniform_mode"])

    def test_d1_gate_remains_shader_byte_materialization(self) -> None:
        result = recon.run_recon()
        gate = result["d1_gate"]

        self.assertFalse(gate["shader_bytes_verified"])
        self.assertFalse(gate["ready_for_d1_live"])
        self.assertIn("materialize a minimal textured FS", gate["next_required"][0])
        self.assertIn("ir3-disasm", gate["next_required"][1])


if __name__ == "__main__":
    unittest.main()
