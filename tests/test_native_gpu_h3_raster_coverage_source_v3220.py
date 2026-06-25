from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3220_gpu_h3_raster_coverage_probe.py"
)


class NativeGpuH3RasterCoverageSourceV3220Tests(unittest.TestCase):
    def test_v3220_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3220")
        self.assertEqual(runner.INIT_VERSION, "0.11.37")
        self.assertEqual(runner.INIT_BUILD, "v3220-gpu-h3-raster-coverage-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3218_gpu_h3_sp_cntl0_linkage_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.37", required)
        self.assertIn(b"v3220-gpu-h3-raster-coverage-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-raster-coverage-mov-f32-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.raster_coverage_source=mesa-freedreno-a6xx-gras-rb-msaa-defaults",
            required,
        )
        self.assertIn(b"gpu.h3.draw.gras_sc_ras_msaa_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_sc_dest_msaa_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_sc_screen_scissor_cntl=0x%x", required)
        self.assertNotIn(b"first-triangle-h3-sp-cntl0-linkage-mov-f32-shader", required)

    def test_dispatch_programs_gras_raster_coverage_defaults(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn("GPU_H2_REG_GRAS_SC_RAS_MSAA_CNTL 0x80a2U", source)
        self.assertIn("GPU_H2_REG_GRAS_SC_DEST_MSAA_CNTL 0x80a3U", source)
        self.assertIn("GPU_H2_REG_GRAS_SC_SCREEN_SCISSOR_CNTL 0x80afU", source)
        self.assertIn("GPU_H2_REG_GRAS_SC_RAS_MSAA_CNTL, 0", source)
        self.assertIn("GPU_H2_REG_GRAS_SC_DEST_MSAA_CNTL", source)
        self.assertIn("GPU_H2_REG_GRAS_SC_SCREEN_SCISSOR_CNTL, 0", source)
        self.assertIn("reg_writes += 9;", source)
        self.assertIn(
            '"gpu.h3.draw.raster_coverage_source=mesa-freedreno-a6xx-gras-rb-msaa-defaults',
            source,
        )
        self.assertIn('"gpu.h3.draw.gras_sc_ras_msaa_cntl=0x%x', source)
        self.assertIn('"gpu.h3.draw.gras_sc_dest_msaa_cntl=0x%x', source)
        self.assertIn('"gpu.h3.draw.gras_sc_screen_scissor_cntl=0x%x', source)

    def test_builder_manifest_records_raster_coverage_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"source_baseline": "v3218-gpu-h3-sp-cntl0-linkage-probe"', source)
        self.assertIn('"raster_coverage_source": "Mesa A6xx GRAS/RB non-MSAA raster coverage defaults"', source)
        self.assertIn('"gras_sc_ras_msaa_cntl": "0x00000000"', source)
        self.assertIn('"gras_sc_dest_msaa_cntl": "0x00000004"', source)
        self.assertIn('"gras_sc_screen_scissor_cntl": "0x00000000"', source)
        self.assertIn("fd6_emit.cc", source)
        self.assertIn("preserve-v3218-ramdisk-overlay-v3220-init-helper-engine", source)
        self.assertIn('"bin/a90_doomgeneric_private_engine_v3220"', source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)
        self.assertIn("V3220 boot image too large for boot partition", source)


if __name__ == "__main__":
    unittest.main()
