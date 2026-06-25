from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3261_gpu_h3_window_offset_probe.py"
)


class NativeGpuH3WindowOffsetSourceV3261Tests(unittest.TestCase):
    def test_v3261_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3261")
        self.assertEqual(runner.INIT_VERSION, "0.11.57")
        self.assertEqual(runner.INIT_BUILD, "v3261-gpu-h3-window-offset-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3259_gpu_h3_visibility_packets_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.57", required)
        self.assertIn(b"v3261-gpu-h3-window-offset-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.window_offset_source=mesa-freedreno-a6xx-fd6-sysmem-prep-set-window-offset-zero",
            required,
        )
        self.assertIn(b"gpu.h3.draw.rb_window_offset=0x%x", required)
        self.assertIn(b"gpu.h3.draw.rb_resolve_window_offset=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_window_offset=0x%x", required)
        self.assertIn(b"gpu.h3.draw.tpl1_window_offset=0x%x", required)
        self.assertNotIn(b"v3259-gpu-h3-visibility-packets-probe", required)

    def test_dispatch_emits_window_offsets_before_visibility_packets(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        state_emit = source[source.index("static bool gpu_h2_append_3d_state_pm4"):]

        self.assertIn("#define GPU_H3_REG_RB_WINDOW_OFFSET 0x8890U", source)
        self.assertIn("#define GPU_H3_REG_RB_RESOLVE_WINDOW_OFFSET 0x88d4U", source)
        self.assertIn("#define GPU_H3_REG_SP_WINDOW_OFFSET 0xb4d1U", source)
        self.assertIn("#define GPU_H3_REG_TPL1_WINDOW_OFFSET 0xb307U", source)
        self.assertIn("#define GPU_H3_WINDOW_OFFSET 0x00000000U", source)
        self.assertLess(
            state_emit.index("GPU_H3_A6XX_CP_SET_MARKER_RM6_DIRECT_RENDER"),
            state_emit.index("GPU_H3_REG_RB_WINDOW_OFFSET"),
        )
        self.assertLess(
            state_emit.index("GPU_H3_REG_RB_WINDOW_OFFSET"),
            state_emit.index("GPU_H3_PM4_CP_SKIP_IB2_ENABLE_GLOBAL"),
        )
        self.assertLess(
            state_emit.index("GPU_H3_PM4_CP_SET_VISIBILITY_OVERRIDE"),
            state_emit.index("GPU_H3_REG_RB_CCU_CNTL,\n                              GPU_H3_RB_CCU_CNTL"),
        )
        self.assertTrue(
            '"gpu.h3.draw.scope=first-triangle-h3-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
            or '"gpu.h3.draw.scope=first-triangle-h3-cp-set-mode-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            or '"gpu.h3.draw.scope=first-triangle-h3-raster-mode-cp-set-mode-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
        )
        self.assertIn(
            '"gpu.h3.draw.window_offset_source=mesa-freedreno-a6xx-fd6-sysmem-prep-set-window-offset-zero',
            source,
        )
        self.assertIn('"gpu.h3.draw.rb_window_offset=0x%x', source)
        self.assertIn('"gpu.h3.draw.rb_resolve_window_offset=0x%x', source)
        self.assertIn('"gpu.h3.draw.sp_window_offset=0x%x', source)
        self.assertIn('"gpu.h3.draw.tpl1_window_offset=0x%x', source)

    def test_builder_manifest_records_window_offset_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3259-visibility-packets-plus-v3260-live-validation"',
            source,
        )
        self.assertIn('"window_offset_registers": WINDOW_OFFSET_REGISTERS', source)
        self.assertIn('"window_offset_value": WINDOW_OFFSET_VALUE', source)
        self.assertIn('"state_reg_writes_expected": 98', source)
        self.assertIn('"pm4_dwords_expected": 260', source)
        self.assertIn("RB_WINDOW_OFFSET=0", source)
        self.assertIn("TPL1_WINDOW_OFFSET=0", source)
        self.assertIn("preserve-v3259-ramdisk-overlay-v3261-init-helper-engine", source)
        self.assertIn("STALE_V3259_ENGINE_RAMDISK_PATH", source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)


if __name__ == "__main__":
    unittest.main()
