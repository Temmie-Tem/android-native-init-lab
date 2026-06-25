from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3218_gpu_h3_sp_cntl0_linkage_probe.py"
)


class NativeGpuH3SPCntl0LinkageSourceV3218Tests(unittest.TestCase):
    def test_v3218_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3218")
        self.assertEqual(runner.INIT_VERSION, "0.11.36")
        self.assertEqual(runner.INIT_BUILD, "v3218-gpu-h3-sp-cntl0-linkage-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3216_gpu_h3_minimal_ir3_mov_shader_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.36", required)
        self.assertIn(b"v3218-gpu-h3-sp-cntl0-linkage-probe", required)
        self.assertIn(b"h3-draw-envelope-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-sp-cntl0-linkage-mov-f32-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.shader_payload=hand-assembled-ir3-mov-f32-vs-position-fs-color-no-full-compiler",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.sp_cntl0_source=mesa-freedreno-a6xx-sp-footprint-mergedregs",
            required,
        )
        self.assertIn(b"gpu.h3.draw.sp_vs_cntl0=0x%x", required)
        self.assertIn(b"gpu.h3.draw.sp_ps_cntl0=0x%x", required)
        self.assertIn(b"gpu.h3.draw.readback_change_expected=1", required)
        self.assertNotIn(b"first-triangle-h3-minimal-ir3-mov-f32-shader", required)

    def test_dispatch_uses_h3_specific_sp_cntl0_values(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn("GPU_H3_SP_XS_CNTL_0_FULLREGFOOTPRINT(n)", source)
        self.assertIn("GPU_H3_SP_VS_CNTL_0_MERGEDREGS (1U << 20)", source)
        self.assertIn("GPU_H3_SP_PS_CNTL_0_INOUTREGOVERLAP (1U << 24)", source)
        self.assertIn("GPU_H3_SP_PS_CNTL_0_MERGEDREGS (1U << 31)", source)
        self.assertIn("uint32_t vs_cntl_0 = GPU_H3_SP_VS_CNTL_0;", source)
        self.assertIn("uint32_t ps_cntl_0 = GPU_H3_SP_PS_CNTL_0;", source)
        self.assertIn("GPU_H1_REG_SP_VS_CNTL_0, vs_cntl_0", source)
        self.assertIn("GPU_H1_REG_SP_PS_CNTL_0, ps_cntl_0", source)
        self.assertTrue(
            '"gpu.h3.draw.scope=first-triangle-h3-sp-cntl0-linkage-mov-f32-shader'
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
        )
        self.assertIn('"gpu.h3.draw.sp_vs_cntl0=0x%x', source)
        self.assertIn('"gpu.h3.draw.sp_ps_cntl0=0x%x', source)

    def test_builder_manifest_records_sp_cntl0_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"source_baseline": "v3216-gpu-h3-minimal-ir3-mov-shader-probe"', source)
        self.assertIn('"sp_vs_cntl0": "0x00100080"', source)
        self.assertIn('"sp_ps_cntl0": "0x81000080"', source)
        self.assertIn("fd6_program.cc", source)
        self.assertIn("pending-gpu-h3-sp-cntl0-linkage-shader-live-validation", source)
        self.assertIn("preserve-v3216-ramdisk-overlay-v3218-init-helper-engine", source)
        self.assertIn('"bin/a90_doomgeneric_private_engine_v3218"', source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)
        self.assertIn("V3218 boot image too large for boot partition", source)


if __name__ == "__main__":
    unittest.main()
