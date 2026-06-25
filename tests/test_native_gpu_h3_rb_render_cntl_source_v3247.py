from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3247_gpu_h3_rb_render_cntl_probe.py"
)


class NativeGpuH3RbRenderCntlSourceV3247Tests(unittest.TestCase):
    def test_v3247_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3247")
        self.assertEqual(runner.INIT_VERSION, "0.11.50")
        self.assertEqual(runner.INIT_BUILD, "v3247-gpu-h3-rb-render-cntl-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3244_gpu_h3_r0_output_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.50", required)
        self.assertIn(b"v3247-gpu-h3-rb-render-cntl-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-rb-render-cntl-r0-output-mov-f32-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.shader_payload=hand-assembled-ir3-r0-output-mov-f32-vs-position-fs-color-no-full-compiler",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.rb_render_cntl_source=mesa-freedreno-a6xx-fd6-gmem-update-render-cntl-ccu-single-cacheline",
            required,
        )
        self.assertIn(b"gpu.h3.draw.rb_render_cntl=0x%x", required)
        self.assertIn(
            b"gpu.h3.draw.rb_ccu_source=mesa-freedreno-a6xx-fd6-emit-gmem-cache-cntl-sysmem-adreno640v2",
            required,
        )
        self.assertNotIn(
            b"gpu.h3.draw.scope=first-triangle-h3-r0-output-full-state-mov-f32-shader",
            required,
        )

    def test_dispatch_programs_rb_render_cntl_candidate(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_H3_RB_RENDER_CNTL 0x00000010U", source)
        self.assertIn("#define GPU_H3_RB_CCU_CNTL 0x10000000U", source)
        self.assertIn("#define GPU_H3_VS_OUTPUT_REGID 0U", source)
        self.assertIn("#define GPU_H3_PS_OUTPUT_REGID 0U", source)
        self.assertIn("#define GPU_H3_SP_FULLREGFOOTPRINT 2U", source)

        self.assertIn(
            "GPU_H2_REG_RB_RENDER_CNTL,\n                              GPU_H3_RB_RENDER_CNTL",
            source,
        )
        self.assertIn(
            "GPU_H3_REG_RB_CCU_CNTL,\n                              GPU_H3_RB_CCU_CNTL",
            source,
        )
        self.assertTrue(
            '"gpu.h3.draw.scope=first-triangle-h3-rb-render-cntl-r0-output-mov-f32-shader'
            in source
            or '"gpu.h3.draw.scope=first-triangle-h3-cache-invalidate-rb-render-cntl-r0-output-mov-f32-shader'
            in source
            or '"gpu.h3.draw.scope=first-triangle-h3-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
            or '"gpu.h3.draw.scope=first-triangle-h3-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
            or '"gpu.h3.draw.scope=first-triangle-h3-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
            or '"gpu.h3.draw.scope=first-triangle-h3-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
            or '"gpu.h3.draw.scope=first-triangle-h3-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
            or '"gpu.h3.draw.scope=first-triangle-h3-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
            or '"gpu.h3.draw.scope=first-triangle-h3-cp-set-mode-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
        )
        self.assertIn(
            '"gpu.h3.draw.rb_render_cntl_source=mesa-freedreno-a6xx-fd6-gmem-update-render-cntl-ccu-single-cacheline',
            source,
        )
        self.assertIn('"gpu.h3.draw.rb_render_cntl=0x%x', source)
        self.assertIn(
            '"gpu.h3.draw.shader_payload=mesa-reference-ir3-minimal-vs-u32-z-w-instrlen1-plus-audited-fs-f32-r0x',
            source,
        )
        self.assertNotIn(
            '"gpu.h3.draw.scope=first-triangle-h3-r0-output-full-state-mov-f32-shader',
            source,
        )

    def test_builder_manifest_records_rb_render_cntl_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3244-r0-output-full-state-plus-v3246-shader-byte-audit"',
            source,
        )
        self.assertIn(
            '"scope": "first-triangle-h3-rb-render-cntl-r0-output-mov-f32-shader"',
            source,
        )
        self.assertIn(
            '"shader_payload": "hand-assembled-ir3-r0-output-mov-f32-vs-position-fs-color-no-full-compiler"',
            source,
        )
        self.assertIn(
            '"rb_render_cntl_source": "Mesa A6xx fd6_gmem update_render_cntl CCUSINGLECACHELINESIZE=2"',
            source,
        )
        self.assertIn('"rb_render_cntl": "0x00000010"', source)
        self.assertIn('"state_reg_writes_expected": 92', source)
        self.assertIn('"pm4_dwords_expected": 233', source)
        self.assertIn("gpu-h3-rb-render-cntl-r0-output-mov-f32-shader-timeout-guard", source)
        self.assertIn("preserve-v3244-ramdisk-overlay-v3247-init-helper-engine", source)
        self.assertIn('"bin/a90_doomgeneric_private_engine_v3247"', source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)
        self.assertIn("V3247 boot image too large for boot partition", source)


if __name__ == "__main__":
    unittest.main()
