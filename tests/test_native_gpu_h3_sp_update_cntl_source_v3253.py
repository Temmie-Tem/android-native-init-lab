from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3253_gpu_h3_sp_update_cntl_probe.py"
)


class NativeGpuH3SpUpdateCntlSourceV3253Tests(unittest.TestCase):
    def test_v3253_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3253")
        self.assertEqual(runner.INIT_VERSION, "0.11.53")
        self.assertEqual(runner.INIT_BUILD, "v3253-gpu-h3-sp-update-cntl-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3251_gpu_h3_compiler_vs_instrlen_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.53", required)
        self.assertIn(b"v3253-gpu-h3-sp-update-cntl-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.sp_update_cntl_source=mesa-freedreno-a6xx-fd6-program-and-draw-stateobj",
            required,
        )
        self.assertIn(b"gpu.h3.draw.sp_update_cntl=0x%x", required)
        self.assertNotIn(b"v3251-gpu-h3-compiler-vs-instrlen-probe", required)

    def test_dispatch_emits_sp_update_cntl_before_shader_state(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_H3_REG_SP_UPDATE_CNTL 0xbb08U", source)
        self.assertIn("#define GPU_H3_SP_UPDATE_CNTL_DRAW_STATE 0x0000009fU", source)
        self.assertLess(
            source.index("GPU_H3_REG_SP_UPDATE_CNTL,\n                              GPU_H3_SP_UPDATE_CNTL_DRAW_STATE"),
            source.index("GPU_H3_REG_SP_MODE_CNTL,\n                              GPU_H3_SP_MODE_CNTL"),
        )
        self.assertTrue(
            '"gpu.h3.draw.scope=first-triangle-h3-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
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
        self.assertIn(
            '"gpu.h3.draw.sp_update_cntl_source=mesa-freedreno-a6xx-fd6-program-and-draw-stateobj',
            source,
        )
        self.assertIn('"gpu.h3.draw.sp_update_cntl=0x%x', source)

    def test_builder_manifest_records_mesa_draw_state_bootstrap(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3251-compiler-vs-instrlen-plus-v3252-live-validation"',
            source,
        )
        self.assertIn('"sp_update_cntl_register": SP_UPDATE_CNTL_REG', source)
        self.assertIn('"sp_update_cntl": SP_UPDATE_CNTL', source)
        self.assertIn('"pm4_dwords_expected": 242', source)
        self.assertIn("SP_UPDATE_CNTL=0x0000009f", source)
        self.assertIn("preserve-v3251-ramdisk-overlay-v3253-init-helper-engine", source)
        self.assertIn("STALE_V3251_ENGINE_RAMDISK_PATH", source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)


if __name__ == "__main__":
    unittest.main()
