from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3222_gpu_h3_vpc_linkage_probe.py"
)


class NativeGpuH3VpcLinkageSourceV3222Tests(unittest.TestCase):
    def test_v3222_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3222")
        self.assertEqual(runner.INIT_VERSION, "0.11.38")
        self.assertEqual(runner.INIT_BUILD, "v3222-gpu-h3-vpc-linkage-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3220_gpu_h3_raster_coverage_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.38", required)
        self.assertIn(b"v3222-gpu-h3-vpc-linkage-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-vpc-linkage-mov-f32-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.vpc_linkage_source=mesa-freedreno-a6xx-position-psizeloc-clip-cull-linkage",
            required,
        )
        self.assertIn(b"gpu.h3.draw.vpc_vs_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_vs_clip_cull_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_vs_clip_cull_cntl_v2=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_cl_vs_clip_cull_distance=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_sc_ras_msaa_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_sc_dest_msaa_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_sc_screen_scissor_cntl=0x%x", required)
        self.assertNotIn(b"first-triangle-h3-sp-cntl0-linkage-mov-f32-shader", required)

    def test_dispatch_programs_vpc_position_clip_cull_linkage(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn("GPU_H2_REG_GRAS_CL_VS_CLIP_CULL_DISTANCE 0x8001U", source)
        self.assertIn("GPU_H2_REG_VPC_VS_CLIP_CULL_CNTL 0x9101U", source)
        self.assertIn("GPU_H2_REG_VPC_VS_CLIP_CULL_CNTL_V2 0x9311U", source)
        self.assertIn("GPU_H3_VPC_VS_CNTL (4U | (0U << 8) | (0xffU << 16))", source)
        self.assertIn("GPU_H3_VPC_VS_CLIP_CULL_CNTL ((0xffU << 8) | (0xffU << 16))", source)
        self.assertIn("GPU_H2_REG_GRAS_CL_VS_CLIP_CULL_DISTANCE", source)
        self.assertIn("GPU_H2_REG_VPC_VS_CLIP_CULL_CNTL", source)
        self.assertIn("GPU_H2_REG_VPC_VS_CNTL,\n                              GPU_H3_VPC_VS_CNTL", source)
        self.assertIn("GPU_H2_REG_VPC_VS_CLIP_CULL_CNTL_V2", source)
        self.assertTrue(
            "reg_writes += 22;" in source
            or "reg_writes += 24;" in source
        )
        self.assertIn(
            '"gpu.h3.draw.vpc_linkage_source=mesa-freedreno-a6xx-position-psizeloc-clip-cull-linkage',
            source,
        )
        self.assertIn('"gpu.h3.draw.vpc_vs_cntl=0x%x', source)
        self.assertIn('"gpu.h3.draw.vpc_vs_clip_cull_cntl=0x%x', source)
        self.assertIn('"gpu.h3.draw.vpc_vs_clip_cull_cntl_v2=0x%x', source)
        self.assertIn('"gpu.h3.draw.gras_cl_vs_clip_cull_distance=0x%x', source)

    def test_builder_manifest_records_vpc_linkage_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"source_baseline": "v3220-gpu-h3-raster-coverage-probe"', source)
        self.assertIn('"vpc_linkage_source": "Mesa A6xx position/psizeloc and clip/cull sentinel linkage"', source)
        self.assertIn('"vpc_vs_cntl": "0x00ff0004"', source)
        self.assertIn('"vpc_vs_clip_cull_cntl": "0x00ffff00"', source)
        self.assertIn('"vpc_vs_clip_cull_cntl_v2": "0x00ffff00"', source)
        self.assertIn('"gras_cl_vs_clip_cull_distance": "0x00000000"', source)
        self.assertIn("fd6_program.cc", source)
        self.assertIn("preserve-v3220-ramdisk-overlay-v3222-init-helper-engine", source)
        self.assertIn('"bin/a90_doomgeneric_private_engine_v3222"', source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)
        self.assertIn("V3222 boot image too large for boot partition", source)


if __name__ == "__main__":
    unittest.main()
