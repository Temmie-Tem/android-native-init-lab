from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3224_gpu_h3_mrt_component_mask_probe.py"
)


class NativeGpuH3MrtComponentMaskSourceV3224Tests(unittest.TestCase):
    def test_v3224_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3224")
        self.assertEqual(runner.INIT_VERSION, "0.11.39")
        self.assertEqual(runner.INIT_BUILD, "v3224-gpu-h3-mrt-component-mask-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3222_gpu_h3_vpc_linkage_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.39", required)
        self.assertIn(b"v3224-gpu-h3-mrt-component-mask-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-mrt-component-mask-mov-f32-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.mrt_component_mask_source=mesa-freedreno-a6xx-mrt-components-full-rt0",
            required,
        )
        self.assertIn(b"gpu.h3.draw.color_output_mask=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_vs_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_vs_clip_cull_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.vpc_vs_clip_cull_cntl_v2=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_cl_vs_clip_cull_distance=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_sc_ras_msaa_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_sc_dest_msaa_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.gras_sc_screen_scissor_cntl=0x%x", required)
        self.assertNotIn(b"first-triangle-h3-sp-cntl0-linkage-mov-f32-shader", required)

    def test_dispatch_programs_full_rt0_component_mask(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn("#define GPU_H3_COLOR_OUTPUT_MASK 0xfU", source)
        self.assertIn("uint32_t rb_mrt_control = (color_output_mask & 0xfU) << 7;", source)
        self.assertIn("GPU_H2_REG_RB_PS_OUTPUT_MASK,\n                              color_output_mask", source)
        self.assertIn("GPU_H2_REG_SP_PS_OUTPUT_MASK,\n                              color_output_mask", source)
        self.assertIn(
            '"gpu.h3.draw.mrt_component_mask_source=mesa-freedreno-a6xx-mrt-components-full-rt0',
            source,
        )
        self.assertIn('"gpu.h3.draw.color_output_mask=0x%x', source)

    def test_builder_manifest_records_mrt_component_mask_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"source_baseline": "v3222-gpu-h3-vpc-linkage-probe"', source)
        self.assertIn('"mrt_component_mask_source": "Mesa A6xx fd6 full RT0 component mask"', source)
        self.assertIn('"color_output_mask": "0xf"', source)
        self.assertIn('"rb_ps_output_mask": "0x0000000f"', source)
        self.assertIn('"sp_ps_output_mask": "0x0000000f"', source)
        self.assertIn('"rb_mrt0_component_enable": "0x00000780"', source)
        self.assertIn("fd6_emit.cc", source)
        self.assertIn("preserve-v3222-ramdisk-overlay-v3224-init-helper-engine", source)
        self.assertIn('"bin/a90_doomgeneric_private_engine_v3224"', source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)
        self.assertIn("V3224 boot image too large for boot partition", source)


if __name__ == "__main__":
    unittest.main()
