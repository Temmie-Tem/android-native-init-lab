from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3265_gpu_h3_cp_set_mode_probe.py"
)


class NativeGpuH3CpSetModeSourceV3265Tests(unittest.TestCase):
    def test_v3265_identity_and_base(self) -> None:
        self.assertEqual(runner.CYCLE, "V3265")
        self.assertEqual(runner.INIT_VERSION, "0.11.59")
        self.assertEqual(runner.INIT_BUILD, "v3265-gpu-h3-cp-set-mode-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3263_gpu_h3_window_offset_cmdroom_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.59", required)
        self.assertIn(b"v3265-gpu-h3-cp-set-mode-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-cp-set-mode-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.cp_set_mode_source=mesa-freedreno-a6xx-fd6-emit-restore-cp-set-mode-zero",
            required,
        )

    def test_dispatch_emits_cp_set_mode_before_shader_state(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        draw_emit = source[source.index("static bool gpu_h3_build_draw_envelope_pm4"):]

        self.assertIn("#define GPU_H3_PM4_CP_SET_MODE 0x63U", source)
        self.assertIn("#define GPU_H3_CP_SET_MODE_RESTORE_VALUE 0x00000000U", source)
        self.assertLess(
            draw_emit.index("GPU_G4_EVENT_CACHE_INVALIDATE"),
            draw_emit.index("GPU_H3_PM4_CP_SET_MODE"),
        )
        self.assertLess(
            draw_emit.index("GPU_H3_PM4_CP_SET_MODE"),
            draw_emit.index("gpu_h3_append_shader_state_pm4"),
        )
        self.assertIn('"gpu.h3.draw.cp_set_mode=0x%x', source)
        self.assertIn('"gpu.h3.draw.cp_set_mode_value=0x%x', source)

    def test_builder_manifest_records_cp_set_mode_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3263-window-offset-cmdroom-plus-v3264-live-no-pixel"',
            source,
        )
        self.assertIn('"cp_set_mode_opcode": CP_SET_MODE_OPCODE', source)
        self.assertIn('"cp_set_mode_value": CP_SET_MODE_VALUE', source)
        self.assertIn('"state_reg_writes_expected": 98', source)
        self.assertIn('"pm4_dwords_expected": 262', source)
        self.assertIn("preserve-v3263-ramdisk-overlay-v3265-init-helper-engine", source)


if __name__ == "__main__":
    unittest.main()
