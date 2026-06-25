from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3257_gpu_h3_vpc_so_override_probe.py"
)


class NativeGpuH3VpcSoOverrideSourceV3257Tests(unittest.TestCase):
    def test_v3257_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3257")
        self.assertEqual(runner.INIT_VERSION, "0.11.55")
        self.assertEqual(runner.INIT_BUILD, "v3257-gpu-h3-vpc-so-override-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3255_gpu_h3_sysmem_bin_control_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.55", required)
        self.assertIn(b"v3257-gpu-h3-vpc-so-override-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.vpc_so_override_source=mesa-freedreno-a6xx-fd6-sysmem-prep-enable-streamout-false",
            required,
        )
        self.assertIn(b"gpu.h3.draw.vpc_so_override=0x%x", required)
        self.assertNotIn(b"v3255-gpu-h3-sysmem-bin-control-probe", required)

    def test_dispatch_emits_mesa_sysmem_vpc_so_override_false(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_H3_REG_VPC_SO_OVERRIDE 0x9306U", source)
        self.assertIn("#define GPU_H3_VPC_SO_OVERRIDE 0x00000000U", source)
        self.assertTrue(
            '"gpu.h3.draw.scope=first-triangle-h3-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
            or '"gpu.h3.draw.scope=first-triangle-h3-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
            or '"gpu.h3.draw.scope=first-triangle-h3-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
        )
        self.assertIn(
            '"gpu.h3.draw.vpc_so_override_source=mesa-freedreno-a6xx-fd6-sysmem-prep-enable-streamout-false',
            source,
        )
        self.assertIn('"gpu.h3.draw.vpc_so_override=0x%x', source)
        self.assertIn(
            "GPU_H3_REG_VPC_SO_OVERRIDE,\n                              GPU_H3_VPC_SO_OVERRIDE",
            source,
        )

    def test_builder_manifest_records_vpc_so_override_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3255-sysmem-bin-control-plus-v3256-live-validation"',
            source,
        )
        self.assertIn('"vpc_so_override_register": VPC_SO_OVERRIDE_REG', source)
        self.assertIn('"vpc_so_override": VPC_SO_OVERRIDE', source)
        self.assertIn('"state_reg_writes_expected": 94', source)
        self.assertIn('"pm4_dwords_expected": 246', source)
        self.assertIn("VPC_SO_OVERRIDE(false)", source)
        self.assertIn("preserve-v3255-ramdisk-overlay-v3257-init-helper-engine", source)
        self.assertIn("STALE_V3255_ENGINE_RAMDISK_PATH", source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)


if __name__ == "__main__":
    unittest.main()
