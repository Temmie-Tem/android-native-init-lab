from __future__ import annotations

import unittest

from _loader import load_script


shader_bytes = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_compute_c1_shader_bytes_v3300.py"
)


class NativeGpuComputeC1ShaderBytesV3300Tests(unittest.TestCase):
    def test_shader_byte_verification_passes_and_is_c1_ready(self) -> None:
        result = shader_bytes.run_verification(require_disasm=True)

        self.assertEqual(result["cycle"], "V3300")
        self.assertEqual(result["scope"], "gpu-compute-c1-shader-byte-materialization")
        self.assertTrue(result["passed"])
        self.assertTrue(result["ready_for_c1_live"])
        self.assertTrue(result["checks"]["shader_binary_sha256_matches"])
        self.assertTrue(result["checks"]["ir3_disasm_contains_expected_ops"])

    def test_materialized_shader_metadata_matches_mesa_assembler_output(self) -> None:
        result = shader_bytes.run_verification(require_disasm=True)
        shader = result["shader"]

        self.assertEqual(shader["gpu_name"], "FD640")
        self.assertEqual(shader["local_size"], [32, 1, 1])
        self.assertEqual(shader["num_bufs"], 1)
        self.assertEqual(shader["buf_sizes"], [32])
        self.assertEqual(shader["buf_addr_regs"], [252])
        self.assertEqual(shader["instrlen"], 1)
        self.assertEqual(shader["sizedwords"], 32)
        self.assertEqual(shader["size_bytes"], 128)
        self.assertEqual(shader["max_reg"], 0)
        self.assertEqual(shader["max_half_reg"], -1)
        self.assertEqual(shader["constlen"], 4)
        self.assertTrue(shader["mergedregs"])
        self.assertEqual(
            shader["binary_sha256"],
            "7142780e5a7332c4bffdf4e0defb78450003295a9932b356140636845087285a",
        )

    def test_dwords_decode_to_invocation_id_store_kernel(self) -> None:
        result = shader_bytes.run_verification(require_disasm=True)
        dwords = result["shader"]["dwords_hex"]
        disasm = "\n".join(result["disasm"]["lines"])

        self.assertEqual(dwords[:8], [
            "0x00000000",
            "0x200cc001",
            "0x00000000",
            "0x00000500",
            "0x01674000",
            "0xc0260000",
            "0x00000000",
            "0x03000000",
        ])
        self.assertIn("mov.u32u32 r0.y, r0.x", disasm)
        self.assertIn("(rpt5)nop", disasm)
        self.assertIn("stib.b.untyped.1d.u32.1.imm r0.x, r0.y, 0", disasm)
        self.assertIn("end", disasm)

    def test_staged_kernel_contract_still_matches_expected_source(self) -> None:
        result = shader_bytes.run_verification(require_disasm=False)
        kernel = result["kernel_contract"]

        self.assertEqual(
            kernel["sha256"],
            "1e0187f2917ab504602a22f30f475716ea8ec7f7123481d371cc87b908c1a97a",
        )
        self.assertTrue(kernel["has_localsize_32_1_1"])
        self.assertTrue(kernel["has_one_32_word_uav"])
        self.assertTrue(kernel["has_invocationid_r0x"])
        self.assertTrue(kernel["has_wgid_r48x"])
        self.assertTrue(kernel["has_numwg_c2x"])
        self.assertTrue(kernel["moves_invocation_id_to_store_value"])
        self.assertTrue(kernel["stores_invocation_id_to_uav"])
        self.assertEqual(kernel["expected_readback"], list(range(32)))


if __name__ == "__main__":
    unittest.main()
