from __future__ import annotations

import unittest

from _loader import load_script


shader_bytes = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_2d_d1_textured_shader_bytes_v3305.py"
)


class NativeGpu2dD1TexturedShaderBytesV3305Tests(unittest.TestCase):
    def test_textured_fs_shader_byte_verification_passes(self) -> None:
        result = shader_bytes.run_verification(require_disasm=True)

        self.assertEqual(result["cycle"], "V3305")
        self.assertEqual(result["scope"], "gpu-2d-d1-textured-fs-shader-byte-materialization")
        self.assertTrue(result["passed"])
        self.assertTrue(result["ready_for_d1_source"])
        self.assertTrue(result["checks"]["shader_binary_sha256_matches"])
        self.assertTrue(result["checks"]["ir3_disasm_contains_expected_ops"])

    def test_materialized_textured_fs_metadata_matches_a640_assembler_output(self) -> None:
        result = shader_bytes.run_verification(require_disasm=True)
        shader = result["shader"]

        self.assertEqual(shader["gpu_name"], "FD640")
        self.assertEqual(shader["chip_id"], "06040000")
        self.assertEqual(shader["stage"], "fragment")
        self.assertEqual(shader["instrlen"], 1)
        self.assertEqual(shader["constlen"], 0)
        self.assertEqual(shader["sizedwords"], 32)
        self.assertEqual(shader["size_bytes"], 128)
        self.assertEqual(shader["max_reg"], 1)
        self.assertEqual(shader["max_half_reg"], -1)
        self.assertTrue(shader["mergedregs"])
        self.assertEqual(shader["num_samp"], 1)
        self.assertEqual(shader["num_tex"], 1)
        self.assertEqual(
            shader["binary_sha256"],
            "4e8ad0a934d236149af999619a1fe99690e7b732d2e4ca69a2b345100d8d04a3",
        )

    def test_dwords_decode_to_barycentric_uv_sample_to_color_output(self) -> None:
        result = shader_bytes.run_verification(require_disasm=True)
        shader = result["shader"]
        disasm = "\n".join(result["disasm"]["lines"])

        self.assertEqual(shader["instruction_pairs_hex"][:4], [
            "47300000_00002000",
            "47300001_00002001",
            "a0c01f02_00000001",
            "03000000_00000000",
        ])
        self.assertIn("bary.f r0.x, 0, r0.x", disasm)
        self.assertIn("bary.f r0.y, 1, r0.x", disasm)
        self.assertIn("sam (f32)(xyzw)r0.z, r0.x, s#0, t#0", disasm)
        self.assertIn("end", disasm)

    def test_sample_output_register_matches_existing_h3_color_output_contract(self) -> None:
        result = shader_bytes.run_verification(require_disasm=False)
        h3 = result["h3_output_contract"]

        self.assertTrue(h3["valid"])
        self.assertEqual(h3["ps_output_regid"], 2)
        self.assertEqual(h3["sample_writes_color_regid"], 2)
        self.assertTrue(h3["sample_output_matches_h3_color_regid"])
        self.assertTrue(h3["fullregfootprint_covers_sample_result"])
        self.assertTrue(h3["shader_slot_covers_aligned_payload"])
        self.assertTrue(h3["has_mergedregs_ps_control"])
        self.assertTrue(h3["has_rgba8_mrt0_contract"])

    def test_next_step_is_source_build_static_checkerboard_probe(self) -> None:
        result = shader_bytes.run_verification(require_disasm=True)

        self.assertIn("embed these verified FS shader words", result["next"][0])
        self.assertIn("NTEX=1/NSAMP=1", result["next"][1])
        self.assertIn("sampled checkerboard pattern", result["next"][2])


if __name__ == "__main__":
    unittest.main()
