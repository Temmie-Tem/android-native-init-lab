from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3282_gpu_h3_rb_dbg_eco_probe.py"
)
audit = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_h3_shader_byte_audit_v3246.py"
)


class NativeGpuH3RbDbgEcoSourceV3282Tests(unittest.TestCase):
    def test_v3282_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3282")
        self.assertEqual(runner.INIT_VERSION, "0.11.67")
        self.assertEqual(runner.INIT_BUILD, "v3282-gpu-h3-rb-dbg-eco-probe")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3282_gpu_h3_rb_dbg_eco_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.67", required)
        self.assertIn(b"v3282-gpu-h3-rb-dbg-eco-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-rb-dbg-eco-init-magic",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.a640_magic_source=mesa-freedreno-devices-a640-a6xx-gen2-rb-dbg-eco-cntl",
            required,
        )
        self.assertIn(b"gpu.h3.draw.a640_magic_mode=rb-dbg-eco-only", required)
        self.assertIn(b"gpu.h3.draw.rb_dbg_eco_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.rb_dbg_eco_cntl_reg=0x%x", required)
        self.assertIn(b"gpu.h3.draw.a640_init_magic_reg_writes=%u", required)

    def test_dispatch_keeps_rb_dbg_eco_magic_before_shader_state(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_A640_REG_RB_DBG_ECO_CNTL 0x8e04U", source)
        self.assertIn("#define GPU_A640_RB_DBG_ECO_CNTL 0x04100000U", source)
        self.assertIn("gpu_h3_append_a640_init_magic_pm4", source)
        self.assertIn("GPU_A640_REG_RB_DBG_ECO_CNTL", source)
        self.assertIn("GPU_A640_RB_DBG_ECO_CNTL", source)
        self.assertIn(
            "!gpu_h3_append_a640_init_magic_pm4(words, dwords) ||\n"
            "        !gpu_h3_append_shader_state_pm4",
            source,
        )

    def test_shader_audit_tracks_rb_dbg_eco_magic(self) -> None:
        result = audit.run_audit(ir3_disasm="/missing/ir3-disasm")
        checks = result["checks"]

        self.assertTrue(result["passed"])
        self.assertIn(result["cycle"], {"V3282", "V3284", "V3287"})
        self.assertIn(result["scope"], {
            "gpu-h3-rb-dbg-eco-init-magic-shader-byte-audit",
            "gpu-h3-a640-nonzero-init-magic-shader-byte-audit",
            "gpu-h3-vfd-vs-contract-replay-shader-byte-audit",
        })
        self.assertEqual(checks["rb_dbg_eco_reg"], 0x8E04)
        self.assertEqual(checks["rb_dbg_eco_cntl"], 0x04100000)
        self.assertTrue(checks["rb_dbg_eco_matches_a640_device_db"])
        self.assertIn(checks["a640_init_magic_reg_writes"], {1, 9})

    def test_builder_manifest_records_bounded_delta(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3280-v3281-flag-mrt-live-no-pixel-plus-a640-device-db-rb-dbg-eco-magic"',
            source,
        )
        self.assertIn('"rb_dbg_eco_source": RB_DBG_ECO_SOURCE', source)
        self.assertIn('"rb_dbg_eco_reg_value": RB_DBG_ECO_REG_VALUE', source)
        self.assertIn('"rb_dbg_eco_cntl_value": RB_DBG_ECO_CNTL_VALUE', source)
        self.assertIn('"a640_magic_mode": "rb-dbg-eco-only"', source)
        self.assertIn('"state_reg_writes_expected": 121', source)
        self.assertIn('"init_magic_reg_writes_expected": INIT_MAGIC_REG_WRITES_EXPECTED', source)
        self.assertIn('"vfd_reg_writes_expected": 14', source)
        self.assertIn('"pm4_dwords_expected": 313', source)
        self.assertIn("gpu-h3-rb-dbg-eco-probe-candidate", source)


if __name__ == "__main__":
    unittest.main()
