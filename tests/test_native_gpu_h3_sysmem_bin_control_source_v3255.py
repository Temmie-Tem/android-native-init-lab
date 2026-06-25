from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3255_gpu_h3_sysmem_bin_control_probe.py"
)


class NativeGpuH3SysmemBinControlSourceV3255Tests(unittest.TestCase):
    def test_v3255_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3255")
        self.assertEqual(runner.INIT_VERSION, "0.11.54")
        self.assertEqual(runner.INIT_BUILD, "v3255-gpu-h3-sysmem-bin-control-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3253_gpu_h3_sp_update_cntl_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.54", required)
        self.assertIn(b"v3255-gpu-h3-sysmem-bin-control-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.bin_control_source=mesa-freedreno-a6xx-fd6-sysmem-prep-set-bin-size",
            required,
        )
        self.assertIn(b"gpu.h3.draw.gras_sc_bin_cntl=0x%x", required)
        self.assertIn(b"gpu.h3.draw.rb_cntl=0x%x", required)
        self.assertNotIn(b"v3253-gpu-h3-sp-update-cntl-probe", required)

    def test_dispatch_emits_sysmem_bin_controls(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_H3_REG_GRAS_SC_BIN_CNTL 0x80a1U", source)
        self.assertIn("#define GPU_H3_REG_RB_CNTL 0x8800U", source)
        self.assertIn("#define GPU_H3_A6XX_BIN_CNTL_SYSMEM_RENDERING \\", source)
        self.assertIn("#define GPU_H3_GRAS_SC_BIN_CNTL GPU_H3_A6XX_BIN_CNTL_SYSMEM_RENDERING", source)
        self.assertIn("#define GPU_H3_RB_CNTL GPU_H3_A6XX_BIN_CNTL_SYSMEM_RENDERING", source)
        self.assertLess(
            source.index("GPU_H2_REG_GRAS_SC_CNTL, 2"),
            source.index("GPU_H3_REG_GRAS_SC_BIN_CNTL,\n                              GPU_H3_GRAS_SC_BIN_CNTL"),
        )
        self.assertLess(
            source.index("GPU_H3_REG_RB_CNTL,\n                              GPU_H3_RB_CNTL"),
            source.index("GPU_H2_REG_RB_RENDER_CNTL,\n                              GPU_H3_RB_RENDER_CNTL"),
        )
        self.assertIn(
            '"gpu.h3.draw.scope=first-triangle-h3-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader',
            source,
        )
        self.assertIn(
            '"gpu.h3.draw.bin_control_source=mesa-freedreno-a6xx-fd6-sysmem-prep-set-bin-size',
            source,
        )
        self.assertIn('"gpu.h3.draw.gras_sc_bin_cntl=0x%x', source)
        self.assertIn('"gpu.h3.draw.rb_cntl=0x%x', source)

    def test_builder_manifest_records_sysmem_bin_control_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3253-sp-update-cntl-plus-v3254-live-validation"',
            source,
        )
        self.assertIn('"sysmem_bin_control_registers": BIN_CONTROL_REGS', source)
        self.assertIn('"sysmem_bin_control": BIN_CONTROL', source)
        self.assertIn('"state_reg_writes_expected": 94', source)
        self.assertIn('"pm4_dwords_expected": 246', source)
        self.assertIn("GRAS_SC_BIN_CNTL=0x02c00000", source)
        self.assertIn("RB_CNTL=0x02c00000", source)
        self.assertIn("preserve-v3253-ramdisk-overlay-v3255-init-helper-engine", source)
        self.assertIn("STALE_V3253_ENGINE_RAMDISK_PATH", source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)


if __name__ == "__main__":
    unittest.main()
