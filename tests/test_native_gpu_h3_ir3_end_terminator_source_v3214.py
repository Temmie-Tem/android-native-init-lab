from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3214_gpu_h3_ir3_end_terminator_probe.py"
)


class NativeGpuH3Ir3EndTerminatorSourceV3214Tests(unittest.TestCase):
    def test_v3214_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3214")
        self.assertEqual(runner.INIT_VERSION, "0.11.34")
        self.assertEqual(runner.INIT_BUILD, "v3214-gpu-h3-ir3-end-terminator-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3212_gpu_h3_draw_envelope_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.34", required)
        self.assertIn(b"v3214-gpu-h3-ir3-end-terminator-probe", required)
        self.assertIn(b"h3-draw-envelope-probe", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-draw-envelope-ir3-end-terminator",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.shader_payload=hand-assembled-ir3-end-only-no-full-compiler",
            required,
        )
        self.assertIn(b"gpu.h3.draw.ir3_end_opcode_hi=0x%x", required)
        self.assertNotIn(b"zero-placeholder-no-full-compiler", required)

    def test_dispatch_uses_ir3_end_terminator_stream(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn("GPU_H1_IR3_END_LO 0x00000000U", source)
        self.assertIn("GPU_H1_IR3_END_HI 0x03000000U", source)
        self.assertIn("GPU_H1_IR3_END_LO, GPU_H1_IR3_END_HI", source)
        self.assertIn(
            '"gpu.h3.draw.scope=first-triangle-h3-draw-envelope-ir3-end-terminator',
            source,
        )
        self.assertIn(
            '"gpu.h3.draw.shader_payload=hand-assembled-ir3-end-only-no-full-compiler',
            source,
        )
        self.assertIn('"gpu.h3.draw.ir3_end_opcode_hi=0x%x', source)

    def test_builder_manifest_records_terminator_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"source_baseline": "v3212-gpu-h3-draw-envelope-probe"', source)
        self.assertIn('"ir3_end_opcode": "0x0300000000000000"', source)
        self.assertIn('"shader_payload": "hand-assembled-ir3-end-only-no-full-compiler"', source)
        self.assertIn("pending-gpu-h3-ir3-end-terminator-live-validation", source)
        self.assertIn("ir3-cat0.xml", source)
        self.assertIn("ir3.xml", source)
        self.assertIn("preserve-v3212-ramdisk-overlay-v3214-init-helper-engine", source)
        self.assertIn("BOOT_PARTITION_MAX_BYTES = 64 * 1024 * 1024", source)
        self.assertIn("V3214 boot image too large for boot partition", source)
        self.assertIn('"removed_stale_entries": removed_stale_entries', source)


if __name__ == "__main__":
    unittest.main()
