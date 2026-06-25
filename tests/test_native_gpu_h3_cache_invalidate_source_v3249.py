from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3249_gpu_h3_cache_invalidate_probe.py"
)


class NativeGpuH3CacheInvalidateSourceV3249Tests(unittest.TestCase):
    def test_v3249_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3249")
        self.assertEqual(runner.INIT_VERSION, "0.11.51")
        self.assertEqual(runner.INIT_BUILD, "v3249-gpu-h3-cache-invalidate-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3247_gpu_h3_rb_render_cntl_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.51", required)
        self.assertIn(b"v3249-gpu-h3-cache-invalidate-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-cache-invalidate-rb-render-cntl-r0-output-mov-f32-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.cache_invalidate_source=mesa-freedreno-a6xx-fd6-emit-restore-fd6-cache-inv",
            required,
        )
        self.assertIn(b"gpu.h3.draw.pre_draw_cache_invalidate=ccu-color,ccu-depth,cache", required)
        self.assertIn(
            b"gpu.h3.draw.pre_draw_cache_invalidate_events=0x%x,0x%x,0x%x",
            required,
        )
        self.assertIn(b"gpu.h3.draw.rb_render_cntl=0x%x", required)
        self.assertNotIn(
            b"gpu.h3.draw.scope=first-triangle-h3-rb-render-cntl-r0-output-mov-f32-shader",
            required,
        )

    def test_dispatch_emits_pre_draw_cache_invalidate_sequence(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_G4_EVENT_PC_CCU_INVALIDATE_COLOR 0x19U", source)
        self.assertIn("#define GPU_G4_EVENT_PC_CCU_INVALIDATE_DEPTH 0x18U", source)
        self.assertIn("#define GPU_G4_EVENT_CACHE_INVALIDATE 0x31U", source)
        self.assertIn(
            "static bool gpu_g4_pm4_emit_event(uint32_t *words,\n"
            "                                  unsigned int *dwords,\n"
            "                                  uint32_t event)",
            source,
        )
        self.assertIn(
            "gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_PC_CCU_INVALIDATE_COLOR)",
            source,
        )
        self.assertIn(
            "gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_PC_CCU_INVALIDATE_DEPTH)",
            source,
        )
        self.assertIn(
            "gpu_g4_pm4_emit_event(words, dwords, GPU_G4_EVENT_CACHE_INVALIDATE)",
            source,
        )
        self.assertLess(
            source.index("GPU_G4_EVENT_PC_CCU_INVALIDATE_COLOR"),
            source.index("gpu_h3_append_shader_state_pm4(words, dwords, vs_gpuaddr, fs_gpuaddr)"),
        )
        self.assertTrue(
            '"gpu.h3.draw.scope=first-triangle-h3-cache-invalidate-rb-render-cntl-r0-output-mov-f32-shader'
            in source
            or '"gpu.h3.draw.scope=first-triangle-h3-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
        )
        self.assertIn(
            '"gpu.h3.draw.cache_invalidate_source=mesa-freedreno-a6xx-fd6-emit-restore-fd6-cache-inv',
            source,
        )
        self.assertIn('"gpu.h3.draw.pre_draw_cache_invalidate=ccu-color,ccu-depth,cache', source)
        self.assertIn('"gpu.h3.draw.pre_draw_cache_invalidate_events=0x%x,0x%x,0x%x', source)
        self.assertIn("#define GPU_H3_RB_RENDER_CNTL 0x00000010U", source)

    def test_builder_manifest_records_cache_invalidate_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3247-rb-render-cntl-plus-v3248-live-validation"',
            source,
        )
        self.assertIn(
            '"scope": "first-triangle-h3-cache-invalidate-rb-render-cntl-r0-output-mov-f32-shader"',
            source,
        )
        self.assertIn(
            '"pre_draw_cache_invalidate_source": "Mesa A6xx fd6_emit_restore fd6_cache_inv"',
            source,
        )
        self.assertIn('"pre_draw_cache_invalidate_events": "0x19,0x18,0x31"', source)
        self.assertIn('"rb_render_cntl": "0x00000010"', source)
        self.assertIn('"state_reg_writes_expected": 92', source)
        self.assertIn('"pm4_dwords_expected": 240', source)
        self.assertIn(
            "gpu-h3-cache-invalidate-rb-render-cntl-r0-output-mov-f32-shader-timeout-guard",
            source,
        )
        self.assertIn("preserve-v3247-ramdisk-overlay-v3249-init-helper-engine", source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)
        self.assertIn("V3249 boot image too large for boot partition", source)


if __name__ == "__main__":
    unittest.main()
