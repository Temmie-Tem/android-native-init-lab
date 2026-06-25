from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3268_gpu_h3_raster_mode_probe.py"
)


class NativeGpuH3RasterModeSourceV3268Tests(unittest.TestCase):
    def test_v3268_identity_and_base(self) -> None:
        self.assertEqual(runner.CYCLE, "V3268")
        self.assertEqual(runner.INIT_VERSION, "0.11.60")
        self.assertEqual(runner.INIT_BUILD, "v3268-gpu-h3-raster-mode-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3265_gpu_h3_cp_set_mode_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.60", required)
        self.assertIn(b"v3268-gpu-h3-raster-mode-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-raster-mode-cp-set-mode-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.raster_mode_source=mesa-freedreno-a6xx-fd6-rasterizer-polymode-triangles",
            required,
        )

    def test_dispatch_emits_vpc_and_pc_raster_triangle_mode(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        state_emit = source[source.index("static bool gpu_h2_append_3d_state_pm4"):]

        self.assertIn("#define GPU_H3_A6XX_POLYMODE6_TRIANGLES 3U", source)
        self.assertIn("#define GPU_H3_REG_VPC_RAST_CNTL 0x9108U", source)
        self.assertIn("#define GPU_H3_REG_PC_DGEN_RAST_CNTL 0x9981U", source)
        self.assertIn("#define GPU_H3_VPC_RAST_CNTL GPU_H3_A6XX_POLYMODE6_TRIANGLES", source)
        self.assertIn("#define GPU_H3_PC_DGEN_RAST_CNTL GPU_H3_A6XX_POLYMODE6_TRIANGLES", source)
        self.assertIn(
            '"gpu.h3.draw.scope=first-triangle-h3-raster-mode-cp-set-mode-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader',
            source,
        )
        self.assertLess(
            state_emit.index("GPU_H3_REG_VPC_UNKNOWN_9210"),
            state_emit.index("GPU_H3_REG_VPC_RAST_CNTL"),
        )
        self.assertLess(
            state_emit.index("GPU_H3_REG_VPC_RAST_STREAM_CNTL"),
            state_emit.index("GPU_H3_REG_PC_DGEN_RAST_CNTL"),
        )
        self.assertIn('"gpu.h3.draw.raster_mode_source=mesa-freedreno-a6xx-fd6-rasterizer-polymode-triangles', source)
        self.assertIn('"gpu.h3.draw.vpc_rast_cntl=0x%x', source)
        self.assertIn('"gpu.h3.draw.pc_dgen_rast_cntl=0x%x', source)

    def test_builder_manifest_records_raster_mode_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3265-cp-set-mode-plus-v3266-live-no-pixel-and-v3267-ccu-audit"',
            source,
        )
        self.assertIn('"raster_mode_source": RASTER_MODE_SOURCE', source)
        self.assertIn('"raster_mode_value": RASTER_MODE_VALUE', source)
        self.assertIn('"state_reg_writes_expected": 100', source)
        self.assertIn('"pm4_dwords_expected": 266', source)
        self.assertIn("preserve-v3265-ramdisk-overlay-v3268-init-helper-engine", source)


if __name__ == "__main__":
    unittest.main()
