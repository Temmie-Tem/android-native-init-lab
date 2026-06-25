from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
BASIC = ROOT / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3212_gpu_h3_draw_envelope_probe.py"
)


class NativeGpuH3DrawEnvelopeSourceV3212Tests(unittest.TestCase):
    def test_v3212_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3212")
        self.assertEqual(runner.INIT_VERSION, "0.11.33")
        self.assertEqual(runner.INIT_BUILD, "v3212-gpu-h3-draw-envelope-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3210_gpu_h2_3d_state_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.33", required)
        self.assertIn(b"v3212-gpu-h3-draw-envelope-probe", required)
        self.assertIn(b"h2-3d-state-probe", required)
        self.assertIn(b"h3-draw-envelope-probe", required)
        self.assertIn(b"draw-envelope-probe", required)
        self.assertIn(b"gpu.h3.draw.version=1", required)
        self.assertIn(
            b"gpu.h3.draw.scope=first-triangle-h3-draw-envelope-placeholder-shader",
            required,
        )
        self.assertIn(
            b"gpu.h3.draw.source=mesa-freedreno-a6xx-fd6-draw-plus-vfd-fetch-dest",
            required,
        )
        self.assertIn(b"gpu.h3.draw.shader_payload=zero-placeholder-no-full-compiler", required)
        self.assertIn(b"gpu.h3.draw.vertex_format=fmt6-32-32-float", required)
        self.assertIn(b"gpu.h3.draw.draw_attempted=1", required)
        self.assertIn(b"gpu.h3.draw.shader_execution_attempted=1", required)
        self.assertIn(b"gpu.h3.draw.kms_blit_attempted=0", required)
        self.assertIn(b"gpu.h3.draw.cp_draw_packet=0x%x", required)
        self.assertIn(b"gpu.h3.draw.readback_changed_count=%u", required)

    def test_dispatch_exposes_child_only_h3_draw_envelope(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn('strcmp(subcommand, "h3-draw-envelope-probe")', source)
        self.assertIn('strcmp(subcommand, "draw-envelope-probe")', source)
        self.assertIn("static int gpu_h3_draw_envelope_probe_child(int write_fd)", source)
        self.assertIn("static int gpu_h3_draw_envelope_probe(int timeout_ms", source)
        self.assertIn("struct gpu_h3_draw_envelope_probe_result", source)
        self.assertIn("GPU_H3_PM4_CP_DRAW_INDX_OFFSET 0x38U", source)
        self.assertIn("GPU_H3_DI_PT_TRILIST 4U", source)
        self.assertIn("GPU_H3_DI_SRC_SEL_AUTO_INDEX 2U", source)
        self.assertIn("GPU_H3_A6XX_FMT6_32_32_FLOAT 0x67U", source)
        self.assertIn("GPU_H3_REG_VFD_VERTEX_BUFFER0_BASE 0xa010U", source)
        self.assertIn("GPU_H3_REG_VFD_FETCH_INSTR0 0xa090U", source)
        self.assertIn("GPU_H3_REG_VFD_DEST_CNTL0 0xa0d0U", source)
        self.assertIn("gpu_h3_build_draw_envelope_pm4", source)
        self.assertIn("gpu_h3_pm4_emit_draw_indx_offset", source)
        self.assertIn("GPU_IOCTL_KGSL_GPU_COMMAND", source)
        self.assertIn("GPU_IOCTL_KGSL_TIMESTAMP_EVENT", source)
        self.assertIn("GPU_IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID", source)
        self.assertIn("GPU_KGSL_GPUMEM_CACHE_FROM_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE", source)
        self.assertIn('"gpu.h3.draw.parent_enters_open=0', source)
        self.assertIn('"gpu.h3.draw.parent_enters_ioctl=0', source)
        self.assertIn('"gpu.h3.draw.draw_attempted=1', source)
        self.assertIn('"gpu.h3.draw.shader_execution_attempted=1', source)
        self.assertIn('"gpu.h3.draw.kms_blit_attempted=0', source)
        self.assertIn("kill(pid, SIGKILL)", source)
        self.assertIn("waitpid(pid, &child_status, 0)", source)

        h3_start = source.index("static bool gpu_h3_build_draw_envelope_pm4")
        h3_end = source.index("static void gpu_g0_print_read_attr", h3_start)
        h3_stream = source[h3_start:h3_end]
        self.assertIn("gpu_h3_append_shader_state_pm4", h3_stream)
        self.assertIn("gpu_h2_append_3d_state_pm4", h3_stream)
        self.assertIn("GPU_H3_REG_VFD_VERTEX_BUFFER0_BASE", h3_stream)
        self.assertIn("GPU_H3_REG_VFD_FETCH_INSTR0", h3_stream)
        self.assertIn("GPU_H3_REG_VFD_DEST_CNTL0", h3_stream)
        self.assertIn("gpu_h3_pm4_emit_draw_indx_offset", h3_stream)
        self.assertIn("GPU_G4_EVENT_PC_CCU_FLUSH_COLOR_TS", h3_stream)
        self.assertNotIn("a90_kms_present", h3_stream)

    def test_help_lists_h3_command(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        basic = BASIC.read_text(encoding="utf-8")
        needle = "h3-draw-envelope-probe [--timeout-ms N] [--materialize-devnode]"
        self.assertIn(needle, source)
        self.assertIn(needle, basic)

    def test_builder_manifest_records_h3_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"gpu h3-draw-envelope-probe --timeout-ms 5000 --materialize-devnode"', source)
        self.assertIn('"draw_attempted": True', source)
        self.assertIn('"shader_execution_attempted": True', source)
        self.assertIn('"kms_blit_attempted": False', source)
        self.assertIn('"vertex_format": "FMT6_32_32_FLOAT"', source)
        self.assertIn('"shader_payload": "zero-placeholder-no-full-compiler"', source)
        self.assertIn("fd6_draw.cc", source)
        self.assertIn("a6xx.xml", source)
        self.assertIn("adreno_pm4.xml", source)
        self.assertIn("CP_DRAW_INDX_OFFSET", source)
        self.assertIn("pending-gpu-h3-draw-envelope-live-validation", source)
        self.assertIn("preserve-v3210-ramdisk-overlay-v3212-init-helper-engine", source)


if __name__ == "__main__":
    unittest.main()
