from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3259_gpu_h3_visibility_packets_probe.py"
)


class NativeGpuH3VisibilityPacketsSourceV3259Tests(unittest.TestCase):
    def test_v3259_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3259")
        self.assertEqual(runner.INIT_VERSION, "0.11.56")
        self.assertEqual(runner.INIT_BUILD, "v3259-gpu-h3-visibility-packets-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3257_gpu_h3_vpc_so_override_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.56", required)
        self.assertIn(b"v3259-gpu-h3-visibility-packets-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.visibility_packet_source=mesa-freedreno-a6xx-fd6-sysmem-prep-visibility-override",
            required,
        )
        self.assertIn(b"gpu.h3.draw.cp_skip_ib2_enable_global=0x%x", required)
        self.assertIn(b"gpu.h3.draw.cp_skip_ib2_enable_local=0x%x", required)
        self.assertIn(b"gpu.h3.draw.cp_set_visibility_override=0x%x", required)
        self.assertIn(b"gpu.h3.draw.cp_set_visibility_override_value=0x%x", required)
        self.assertNotIn(b"v3257-gpu-h3-vpc-so-override-probe", required)

    def test_dispatch_emits_visibility_packets_after_direct_render_marker(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        state_emit = source[source.index("static bool gpu_h2_append_3d_state_pm4"):]

        self.assertIn("#define GPU_H3_PM4_CP_SKIP_IB2_ENABLE_GLOBAL 0x1dU", source)
        self.assertIn("#define GPU_H3_PM4_CP_SKIP_IB2_ENABLE_LOCAL 0x23U", source)
        self.assertIn("#define GPU_H3_PM4_CP_SET_VISIBILITY_OVERRIDE 0x64U", source)
        self.assertIn("#define GPU_H3_CP_SKIP_IB2_ENABLE_GLOBAL_VALUE 0x00000000U", source)
        self.assertIn("#define GPU_H3_CP_SKIP_IB2_ENABLE_LOCAL_VALUE 0x00000001U", source)
        self.assertIn("#define GPU_H3_CP_SET_VISIBILITY_OVERRIDE_VALUE 0x00000001U", source)
        self.assertLess(
            state_emit.index("GPU_H3_A6XX_CP_SET_MARKER_RM6_DIRECT_RENDER"),
            state_emit.index("GPU_H3_PM4_CP_SKIP_IB2_ENABLE_GLOBAL"),
        )
        self.assertLess(
            state_emit.index("GPU_H3_PM4_CP_SKIP_IB2_ENABLE_GLOBAL"),
            state_emit.index("GPU_H3_PM4_CP_SKIP_IB2_ENABLE_LOCAL"),
        )
        self.assertLess(
            state_emit.index("GPU_H3_PM4_CP_SKIP_IB2_ENABLE_LOCAL"),
            state_emit.index("GPU_H3_PM4_CP_SET_VISIBILITY_OVERRIDE"),
        )
        self.assertLess(
            state_emit.index("GPU_H3_PM4_CP_SET_VISIBILITY_OVERRIDE"),
            state_emit.index("GPU_H3_REG_RB_CCU_CNTL,\n                              GPU_H3_RB_CCU_CNTL"),
        )
        self.assertTrue(
            '"gpu.h3.draw.scope=first-triangle-h3-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
            or '"gpu.h3.draw.scope=first-triangle-h3-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader'
            in source
        )
        self.assertIn(
            '"gpu.h3.draw.visibility_packet_source=mesa-freedreno-a6xx-fd6-sysmem-prep-visibility-override',
            source,
        )
        self.assertIn('"gpu.h3.draw.cp_skip_ib2_enable_global=0x%x', source)
        self.assertIn('"gpu.h3.draw.cp_skip_ib2_enable_local=0x%x', source)
        self.assertIn('"gpu.h3.draw.cp_set_visibility_override=0x%x', source)
        self.assertIn('"gpu.h3.draw.cp_skip_ib2_enable_global_value=0x%x', source)
        self.assertIn('"gpu.h3.draw.cp_skip_ib2_enable_local_value=0x%x', source)
        self.assertIn('"gpu.h3.draw.cp_set_visibility_override_value=0x%x', source)

    def test_builder_manifest_records_visibility_packet_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3257-vpc-so-override-plus-v3258-live-validation"',
            source,
        )
        self.assertIn('"visibility_packet_opcodes": VISIBILITY_PACKET_OPCODES', source)
        self.assertIn('"visibility_packet_values": VISIBILITY_PACKET_VALUES', source)
        self.assertIn('"state_reg_writes_expected": 94', source)
        self.assertIn('"pm4_dwords_expected": 252', source)
        self.assertIn("CP_SKIP_IB2_ENABLE_GLOBAL=0", source)
        self.assertIn("CP_SET_VISIBILITY_OVERRIDE=1", source)
        self.assertIn("preserve-v3257-ramdisk-overlay-v3259-init-helper-engine", source)
        self.assertIn("STALE_V3257_ENGINE_RAMDISK_PATH", source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)


if __name__ == "__main__":
    unittest.main()
