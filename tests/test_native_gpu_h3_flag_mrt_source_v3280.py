from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3280_gpu_h3_flag_mrt_probe.py"
)
audit = load_script(
    "workspace/public/src/scripts/revalidation/native_gpu_h3_shader_byte_audit_v3246.py"
)


class NativeGpuH3FlagMrtSourceV3280Tests(unittest.TestCase):
    def test_v3280_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3280")
        self.assertEqual(runner.INIT_VERSION, "0.11.66")
        self.assertEqual(runner.INIT_BUILD, "v3280-gpu-h3-flag-mrt-probe")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3280_gpu_h3_flag_mrt_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.66", required)
        self.assertIn(b"v3280-gpu-h3-flag-mrt-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-flag-mrt-cffdump-color-target",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.color_format_source=mesa-freedreno-a640-cffdump-rgba8-tile6-3-flag-mrt0",
            required,
        )
        self.assertIn(b"gpu.h3.draw.sp_ps_mrt_reg0=0x%x", required)
        self.assertIn(b"gpu.h3.draw.rb_mrt0_buf_info=0x%x", required)
        self.assertIn(b"gpu.h3.draw.rb_render_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.color_flag_buffer_pitch=0x%x", required)
        self.assertIn(b"gpu.h3.draw.color_flag_changed_count=%u", required)
        self.assertIn(b"gpu.h3.draw.offscreen=rgba8-tile6-3-flag-mrt0-128x128", required)
        self.assertIn(
            b"gpu.h3.draw.hlsq_round4_audit=local-a6xx-fd6-uses-sp-program-config-not-legacy-hlsq-control-regs",
            required,
        )

    def test_dispatch_uses_cffdump_flag_mrt0_color_target(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_G4_A6XX_FMT6_8_8_8_8_UNORM 0x30U", source)
        self.assertIn(
            "#define GPU_H3_COLOR_FORMAT GPU_G4_A6XX_FMT6_8_8_8_8_UNORM",
            source,
        )
        self.assertIn("#define GPU_H3_SP_PS_MRT_REG0 GPU_H3_COLOR_FORMAT", source)
        self.assertIn("#define GPU_H3_RB_MRT0_BUF_INFO \\", source)
        self.assertIn("gpu.h3.draw.color_format_source=mesa-freedreno-a640-cffdump-rgba8-tile6-3-flag-mrt0", source)
        self.assertIn("gpu.h3.draw.sp_ps_mrt_reg0=0x%x", source)
        self.assertIn("gpu.h3.draw.rb_mrt0_buf_info=0x%x", source)
        self.assertIn("#define GPU_H3_RB_RENDER_CNTL_FLAG_MRT0", source)
        self.assertIn("#define GPU_H3_COLOR_FLAG_BUFFER_PITCH 0x00004001U", source)
        self.assertIn("GPU_H3_REG_RB_COLOR_FLAG_BUFFER0_ADDR", source)
        self.assertIn("gpu.h3.draw.color_flag_changed_count=%u", source)
        self.assertIn("gpu.h3.draw.offscreen=rgba8-tile6-3-flag-mrt0-128x128", source)
        self.assertIn(
            "gpu.h3.draw.hlsq_round4_audit=local-a6xx-fd6-uses-sp-program-config-not-legacy-hlsq-control-regs",
            source,
        )
        self.assertNotIn("gpu.h3.draw.offscreen=f32-linear-128x128", source)

    def test_shader_audit_tracks_flag_mrt_contract(self) -> None:
        result = audit.run_audit(ir3_disasm="/missing/ir3-disasm")
        checks = result["checks"]

        self.assertTrue(result["passed"])
        self.assertIn(result["cycle"], {"V3280", "V3282", "V3284", "V3287", "V3289"})
        self.assertIn(
            result["scope"],
            {
                "gpu-h3-flag-mrt-shader-byte-audit",
                "gpu-h3-rb-dbg-eco-init-magic-shader-byte-audit",
                "gpu-h3-a640-nonzero-init-magic-shader-byte-audit",
                "gpu-h3-vfd-vs-contract-replay-shader-byte-audit",
                "gpu-h3-blend-output-state-shader-byte-audit",
            },
        )
        self.assertEqual(checks["sp_ps_mrt_reg0_color_format"], 0x30)
        self.assertEqual(checks["rb_mrt0_buf_info_color_format"], 0x30)
        self.assertEqual(checks["rb_mrt0_buf_info_tile_mode"], 0x3)
        self.assertEqual(checks["rb_render_cntl"], 0x00010010)
        self.assertEqual(checks["rb_render_cntl_flag_mrts"], 0x1)
        self.assertEqual(checks["color_flag_buffer_pitch"], 0x00004001)
        self.assertTrue(checks["sp_ps_mrt_reg0_matches_a640_cffdump_rgba8"])
        self.assertTrue(checks["rb_mrt0_buf_info_matches_h3_color_format"])
        self.assertTrue(checks["rb_mrt0_buf_info_matches_a640_cffdump_tile6_3"])
        self.assertTrue(checks["rb_render_cntl_matches_a640_cffdump_flag_mrt0"])
        self.assertTrue(checks["color_flag_buffer_pitch_matches_a640_cffdump"])

    def test_builder_manifest_records_bounded_delta(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3278-v3279-rgba8-mrt-live-no-pixel-plus-a640-cffdump-draw2-flag-mrt-color-target-diff"',
            source,
        )
        self.assertIn('"flag_mrt_source": FLAG_MRT_SOURCE', source)
        self.assertIn('"color_format_value": COLOR_FORMAT_VALUE', source)
        self.assertIn('"rb_mrt0_buf_info_value": RB_MRT0_BUF_INFO_VALUE', source)
        self.assertIn('"rb_render_cntl_value": RB_RENDER_CNTL_VALUE', source)
        self.assertIn('"color_flag_buffer_pitch_value": COLOR_FLAG_BUFFER_PITCH_VALUE', source)
        self.assertIn('"hlsq_round4_audit":', source)
        self.assertIn('"state_reg_writes_expected": 121', source)
        self.assertIn('"vfd_reg_writes_expected": 14', source)
        self.assertIn('"pm4_dwords_expected": 311', source)
        self.assertIn("gpu-h3-flag-mrt-probe-candidate", source)


if __name__ == "__main__":
    unittest.main()
