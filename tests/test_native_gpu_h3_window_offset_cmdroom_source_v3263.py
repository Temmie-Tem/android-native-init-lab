from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3263_gpu_h3_window_offset_cmdroom_probe.py"
)


class NativeGpuH3WindowOffsetCmdroomSourceV3263Tests(unittest.TestCase):
    def test_v3263_identity_and_base(self) -> None:
        self.assertEqual(runner.CYCLE, "V3263")
        self.assertEqual(runner.INIT_VERSION, "0.11.58")
        self.assertEqual(runner.INIT_BUILD, "v3263-gpu-h3-window-offset-cmdroom-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3259_gpu_h3_visibility_packets_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.58", required)
        self.assertIn(b"v3263-gpu-h3-window-offset-cmdroom-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-window-offset-visibility-packets-vpc-so-override-off-sysmem-bin-control-sp-update-cntl-compiler-vs-instrlen-cache-invalidate-rb-render-cntl-r0-output-shader",
            required,
        )
        self.assertIn(b"gpu.h3.draw.window_offset_source=mesa-freedreno-a6xx-fd6-sysmem-prep-set-window-offset-zero", required)

    def test_dispatch_has_window_offsets_and_enough_cmd_room(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn("#define GPU_G4_CMD_MAX_DWORDS 384U", source)
        self.assertIn("#define GPU_H3_REG_RB_WINDOW_OFFSET 0x8890U", source)
        self.assertIn("#define GPU_H3_REG_RB_RESOLVE_WINDOW_OFFSET 0x88d4U", source)
        self.assertIn("#define GPU_H3_REG_SP_WINDOW_OFFSET 0xb4d1U", source)
        self.assertIn("#define GPU_H3_REG_TPL1_WINDOW_OFFSET 0xb307U", source)
        self.assertIn("#define GPU_H3_WINDOW_OFFSET 0x00000000U", source)
        self.assertIn('"gpu.h3.draw.rb_window_offset=0x%x', source)
        self.assertIn('"gpu.h3.draw.tpl1_window_offset=0x%x', source)

    def test_builder_manifest_records_cmdroom_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")

        self.assertIn(
            '"source_baseline": "v3261-window-offset-plus-v3262-cmd-write-overflow-live-validation"',
            source,
        )
        self.assertIn('"cmd_max_dwords": CMD_MAX_DWORDS', source)
        self.assertIn("CMD_MAX_DWORDS = 320", source)
        self.assertIn('"state_reg_writes_expected": 98', source)
        self.assertIn('"pm4_dwords_expected": 260', source)
        self.assertIn("cmd_write_rc=-1", source)
        self.assertIn("preserve-v3259-ramdisk-overlay-v3263-init-helper-engine", source)


if __name__ == "__main__":
    unittest.main()
