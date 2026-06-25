from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3278_gpu_h3_rgba8_mrt_probe.py"
)
audit = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_h3_shader_byte_audit_v3246.py"
)


class NativeGpuH3Rgba8MrtSourceV3278Tests(unittest.TestCase):
    def test_v3278_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3278")
        self.assertEqual(runner.INIT_VERSION, "0.11.65")
        self.assertEqual(runner.INIT_BUILD, "v3278-gpu-h3-rgba8-mrt-probe")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3278_gpu_h3_rgba8_mrt_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.65", required)
        self.assertIn(b"v3278-gpu-h3-rgba8-mrt-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-rgba8-mrt-cffdump-diff",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.color_format_source=mesa-freedreno-a640-cffdump-rgba8-mrt0",
            required,
        )
        self.assertIn(b"gpu.h3.draw.sp_ps_mrt_reg0=0x%x", required)
        self.assertIn(b"gpu.h3.draw.rb_mrt0_buf_info=0x%x", required)
        self.assertIn(b"gpu.h3.draw.offscreen=rgba8-linear-128x128", required)
        self.assertIn(
            b"gpu.h3.draw.hlsq_round4_audit=local-a6xx-fd6-uses-sp-program-config-not-legacy-hlsq-control-regs",
            required,
        )

    def test_dispatch_uses_cffdump_rgba8_mrt0_color_target(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_G4_A6XX_FMT6_8_8_8_8_UNORM 0x30U", source)
        self.assertIn(
            "#define GPU_H3_COLOR_FORMAT GPU_G4_A6XX_FMT6_8_8_8_8_UNORM",
            source,
        )
        self.assertIn("#define GPU_H3_SP_PS_MRT_REG0 GPU_H3_COLOR_FORMAT", source)
        self.assertIn("#define GPU_H3_RB_MRT0_BUF_INFO \\", source)
        self.assertTrue(
            "gpu.h3.draw.color_format_source=mesa-freedreno-a640-cffdump-rgba8-mrt0" in source
            or "gpu.h3.draw.color_format_source=mesa-freedreno-a640-cffdump-rgba8-tile6-3-flag-mrt0" in source
        )
        self.assertIn("gpu.h3.draw.sp_ps_mrt_reg0=0x%x", source)
        self.assertIn("gpu.h3.draw.rb_mrt0_buf_info=0x%x", source)
        self.assertTrue(
            "gpu.h3.draw.offscreen=rgba8-linear-128x128" in source
            or "gpu.h3.draw.offscreen=rgba8-tile6-3-flag-mrt0-128x128" in source
        )
        self.assertIn(
            "gpu.h3.draw.hlsq_round4_audit=local-a6xx-fd6-uses-sp-program-config-not-legacy-hlsq-control-regs",
            source,
        )
        self.assertNotIn("gpu.h3.draw.offscreen=f32-linear-128x128", source)

    def test_shader_audit_tracks_rgba8_mrt_contract(self) -> None:
        result = audit.run_audit(ir3_disasm="/missing/ir3-disasm")
        checks = result["checks"]

        self.assertTrue(result["passed"])
        self.assertIn(result["cycle"], {"V3278", "V3280", "V3282", "V3284"})
        self.assertIn(
            result["scope"],
            {
                "gpu-h3-rgba8-mrt-shader-byte-audit",
                "gpu-h3-flag-mrt-shader-byte-audit",
                "gpu-h3-rb-dbg-eco-init-magic-shader-byte-audit",
                "gpu-h3-a640-nonzero-init-magic-shader-byte-audit",
            },
        )
        self.assertEqual(checks["sp_ps_mrt_reg0_color_format"], 0x30)
        self.assertEqual(checks["rb_mrt0_buf_info_color_format"], 0x30)
        self.assertTrue(checks["sp_ps_mrt_reg0_matches_a640_cffdump_rgba8"])
        self.assertTrue(checks["rb_mrt0_buf_info_matches_h3_color_format"])

    def test_builder_manifest_records_bounded_delta(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3276-varying-ij-live-no-pixel-plus-a640-cffdump-rgba8-mrt-color-target-diff"',
            source,
        )
        self.assertIn('"rgba8_mrt_source": RGBA8_MRT_SOURCE', source)
        self.assertIn('"color_format_value": COLOR_FORMAT_VALUE', source)
        self.assertIn('"rb_mrt0_buf_info_value": RB_MRT0_BUF_INFO_VALUE', source)
        self.assertIn('"hlsq_round4_audit":', source)
        self.assertIn('"state_reg_writes_expected": 118', source)
        self.assertIn('"vfd_reg_writes_expected": 14', source)
        self.assertIn('"pm4_dwords_expected": 306', source)
        self.assertIn("gpu-h3-rgba8-mrt-probe-candidate", source)


if __name__ == "__main__":
    unittest.main()
