from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3284_gpu_h3_a640_magic_block_probe.py"
)
audit = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_h3_shader_byte_audit_v3246.py"
)


class NativeGpuH3A640MagicBlockSourceV3284Tests(unittest.TestCase):
    def test_v3284_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3284")
        self.assertEqual(runner.INIT_VERSION, "0.11.68")
        self.assertEqual(runner.INIT_BUILD, "v3284-gpu-h3-a640-magic-block-probe")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3284_gpu_h3_a640_magic_block_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.68", required)
        self.assertIn(b"v3284-gpu-h3-a640-magic-block-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-a640-nonzero-init-magic-block",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.a640_magic_source=mesa-freedreno-devices-a640-a6xx-gen2-nonzero-magic-regs",
            required,
        )
        self.assertIn(b"gpu.h3.draw.a640_magic_mode=nonzero-block", required)
        self.assertIn(b"gpu.h3.draw.a640_magic_nonzero_block=rb_dbg_eco", required)
        self.assertIn(b"gpu.h3.draw.sp_chicken_bits=0x%x", required)
        self.assertIn(b"gpu.h3.draw.uche_unknown_0e12=0x%x", required)

    def test_dispatch_emits_full_nonzero_magic_block_before_shader_state(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        expected_defines = {
            "#define GPU_G4_CMD_MAX_DWORDS 384U",
            "#define GPU_A640_REG_RB_DBG_ECO_CNTL 0x8e04U",
            "#define GPU_A640_RB_DBG_ECO_CNTL 0x04100000U",
            "#define GPU_A640_REG_SP_CHICKEN_BITS 0xae03U",
            "#define GPU_A640_SP_CHICKEN_BITS 0x00000420U",
            "#define GPU_A640_REG_TPL1_DBG_ECO_CNTL 0xb600U",
            "#define GPU_A640_TPL1_DBG_ECO_CNTL 0x00008000U",
            "#define GPU_A640_REG_VPC_DBG_ECO_CNTL 0x9600U",
            "#define GPU_A640_VPC_DBG_ECO_CNTL 0x02000000U",
            "#define GPU_A640_REG_RB_RBP_CNTL 0x8e01U",
            "#define GPU_A640_RB_RBP_CNTL 0x00000001U",
            "#define GPU_A640_REG_PC_MODE_CNTL 0x9804U",
            "#define GPU_A640_PC_MODE_CNTL 0x0000001fU",
            "#define GPU_A640_REG_PC_POWER_CNTL 0x9805U",
            "#define GPU_A640_PC_POWER_CNTL 0x00000001U",
            "#define GPU_A640_REG_VFD_POWER_CNTL 0xa0f8U",
            "#define GPU_A640_VFD_POWER_CNTL 0x00000001U",
            "#define GPU_A640_REG_UCHE_UNKNOWN_0E12 0x0e12U",
            "#define GPU_A640_UCHE_UNKNOWN_0E12 0x00000001U",
            "#define GPU_H3_A640_INIT_MAGIC_REG_WRITES 9U",
        }
        for expected in expected_defines:
            self.assertIn(expected, source)

        self.assertIn("gpu.h3.draw.a640_magic_mode=nonzero-block", source)
        self.assertIn(
            "a640-nonzero-init-magic-block",
            source,
        )
        self.assertIn("gpu.h3.draw.a640_magic_nonzero_block=rb_dbg_eco", source)
        self.assertIn(
            "!gpu_h3_append_a640_init_magic_pm4(words, dwords) ||\n"
            "        !gpu_h3_append_shader_state_pm4",
            source,
        )
        append_pos = source.index("!gpu_h3_append_a640_init_magic_pm4(words, dwords)")
        shader_pos = source.index("!gpu_h3_append_shader_state_pm4", append_pos)
        self.assertLess(append_pos, shader_pos)

    def test_shader_audit_tracks_full_magic_block(self) -> None:
        result = audit.run_audit(ir3_disasm="/missing/ir3-disasm")
        checks = result["checks"]

        self.assertTrue(result["passed"])
        self.assertIn(result["cycle"], {"V3284", "V3287"})
        self.assertIn(result["scope"], {
            "gpu-h3-a640-nonzero-init-magic-shader-byte-audit",
            "gpu-h3-vfd-vs-contract-replay-shader-byte-audit",
        })
        self.assertTrue(checks["a640_nonzero_magic_all_match"])
        self.assertEqual(checks["a640_init_magic_reg_writes"], 9)
        self.assertTrue(checks["a640_init_magic_is_nonzero_block"])
        self.assertEqual(checks["sp_chicken_bits"], 0x00000420)
        self.assertEqual(checks["tpl1_dbg_eco_cntl"], 0x00008000)
        self.assertEqual(checks["vpc_dbg_eco_cntl"], 0x02000000)
        self.assertEqual(checks["rb_rbp_cntl"], 0x00000001)
        self.assertEqual(checks["pc_mode_magic"], 0x0000001F)
        self.assertEqual(checks["pc_power_cntl"], 0x00000001)
        self.assertEqual(checks["vfd_power_cntl"], 0x00000001)
        self.assertEqual(checks["uche_unknown_0e12"], 0x00000001)

    def test_builder_manifest_records_bounded_delta(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3282-v3283-rb-dbg-eco-only-live-no-pixel-plus-a640-device-db-nonzero-magic-block"',
            source,
        )
        self.assertIn('"a640_magic_mode": "nonzero-block"', source)
        self.assertIn('"cmd_max_dwords": CMD_MAX_DWORDS', source)
        self.assertIn('"init_magic_reg_writes_expected": INIT_MAGIC_REG_WRITES_EXPECTED', source)
        self.assertIn('"pm4_dwords_expected": PM4_DWORDS_EXPECTED', source)
        self.assertIn("PM4_DWORDS_EXPECTED = 329", source)
        self.assertIn("CMD_MAX_DWORDS = 384", source)
        self.assertIn("gpu-h3-a640-magic-block-probe-candidate", source)


if __name__ == "__main__":
    unittest.main()
