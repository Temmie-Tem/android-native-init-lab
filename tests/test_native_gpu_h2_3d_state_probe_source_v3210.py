from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
BASIC = ROOT / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3210_gpu_h2_3d_state_probe.py"
)


class NativeGpuH2_3DStateProbeSourceV3210Tests(unittest.TestCase):
    def test_v3210_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3210")
        self.assertEqual(runner.INIT_VERSION, "0.11.32")
        self.assertEqual(runner.INIT_BUILD, "v3210-gpu-h2-3d-state-probe")
        self.assertEqual(
            runner.BASE_BOOT.name,
            "boot_linux_v3208_gpu_h1_shader_state_probe.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.32", required)
        self.assertIn(b"v3210-gpu-h2-3d-state-probe", required)
        self.assertIn(b"gpu.h1.shader.version=1", required)
        self.assertIn(b"h2-3d-state-probe", required)
        self.assertIn(b"3d-state-probe", required)
        self.assertIn(b"gpu.h2.state.version=1", required)
        self.assertIn(
            b"gpu.h2.state.scope=first-triangle-h2-3d-fixed-function-state-no-draw",
            required,
        )
        self.assertIn(
            b"gpu.h2.state.source=mesa-freedreno-a6xx-fd6-emit-draw-plus-a6xx-xml",
            required,
        )
        self.assertIn(b"gpu.h2.state.offscreen=u32-linear-128x128", required)
        self.assertIn(b"gpu.h2.state.draw_attempted=0", required)
        self.assertIn(b"gpu.h2.state.shader_execution_attempted=0", required)
        self.assertIn(b"gpu.h2.state.kms_blit_attempted=0", required)
        self.assertIn(b"gpu.h2.state.power_write_attempted=0", required)
        self.assertIn(b"gpu.h2.state.proprietary_blob_attempted=0", required)
        self.assertIn(b"gpu.h2.state.color_format=0x%x", required)
        self.assertIn(b"gpu.h2.state.state_reg_writes=%u", required)
        self.assertIn(b"3d-state-retired-no-draw", required)

    def test_dispatch_exposes_child_only_h2_3d_state_probe(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn('strcmp(subcommand, "h2-3d-state-probe")', source)
        self.assertIn('strcmp(subcommand, "3d-state-probe")', source)
        self.assertIn("static int gpu_h2_3d_state_probe_child(int write_fd)", source)
        self.assertIn("static int gpu_h2_3d_state_probe(int timeout_ms", source)
        self.assertIn("struct gpu_h2_3d_state_probe_result", source)
        self.assertIn("GPU_H2_REG_GRAS_CL_VIEWPORT 0x8010U", source)
        self.assertIn("GPU_H2_REG_RB_MRT0_BUF_INFO 0x8822U", source)
        self.assertIn("GPU_H2_REG_RB_MRT0_BASE 0x8825U", source)
        self.assertIn("GPU_H2_REG_VFD_MODE_CNTL 0xa009U", source)
        self.assertIn("GPU_H2_REG_SP_PS_MRT_REG0 0xa996U", source)
        self.assertIn("gpu_h2_build_3d_state_pm4", source)
        self.assertIn("GPU_IOCTL_KGSL_GPU_COMMAND", source)
        self.assertIn("GPU_IOCTL_KGSL_TIMESTAMP_EVENT", source)
        self.assertIn("GPU_IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID", source)
        self.assertIn("GPU_IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID", source)
        self.assertIn("GPU_IOCTL_KGSL_GPUOBJ_SYNC", source)
        self.assertIn("GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE", source)
        self.assertIn('"gpu.h2.state.parent_enters_open=0', source)
        self.assertIn('"gpu.h2.state.parent_enters_ioctl=0', source)
        self.assertIn('"gpu.h2.state.draw_attempted=0', source)
        self.assertIn('"gpu.h2.state.shader_execution_attempted=0', source)
        self.assertIn('"gpu.h2.state.kms_blit_attempted=0', source)
        self.assertIn('"gpu.h2.state.offscreen=u32-linear-128x128', source)
        self.assertIn("kill(pid, SIGKILL)", source)
        self.assertIn("waitpid(pid, &child_status, 0)", source)

        h2_start = source.index("static bool gpu_h2_append_3d_state_pm4")
        h2_end = source.index("static bool gpu_h2_build_3d_state_pm4", h2_start)
        h2_stream = source[h2_start:h2_end]
        self.assertIn("GPU_H2_REG_GRAS_CL_VIEWPORT", h2_stream)
        self.assertIn("GPU_H2_REG_RB_MRT0_BASE", h2_stream)
        self.assertIn("GPU_H2_REG_VFD_MODE_CNTL", h2_stream)
        self.assertIn("GPU_H2_REG_SP_PS_MRT_REG0", h2_stream)
        self.assertIn("GPU_G4_PM4_CP_WAIT_FOR_IDLE", h2_stream)
        self.assertNotIn("CP_DRAW_INDX_OFFSET", h2_stream)
        self.assertNotIn("a90_kms_present", h2_stream)
        self.assertNotIn("gpu_h1_build_shader_state_pm4", h2_stream)

    def test_help_lists_h2_command(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        basic = BASIC.read_text(encoding="utf-8")
        needle = "h2-3d-state-probe [--timeout-ms N] [--materialize-devnode]"
        self.assertIn(needle, source)
        self.assertIn(needle, basic)
        self.assertIn("h1-shader-state-probe [--timeout-ms N] [--materialize-devnode]", source)
        self.assertIn("h1-shader-state-probe [--timeout-ms N] [--materialize-devnode]", basic)

    def test_builder_manifest_records_h2_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"gpu h2-3d-state-probe --timeout-ms 5000 --materialize-devnode"', source)
        self.assertIn('"shader_execution_attempted": False', source)
        self.assertIn('"draw_attempted": False', source)
        self.assertIn('"kms_blit_attempted": False', source)
        self.assertIn('"fixed_function_state": "GRAS/RB/VPC/PC/VFD/SP-output"', source)
        self.assertIn('"offscreen": "u32-linear-128x128"', source)
        self.assertIn('"full-ir3-compiler-port"', source)
        self.assertIn('"triangle-render"', source)
        self.assertIn('"shader-execution"', source)
        self.assertIn('"GDSC-write"', source)
        self.assertIn('"proprietary-adreno-blob"', source)
        self.assertIn("fd6_emit.cc", source)
        self.assertIn("fd6_draw.cc", source)
        self.assertIn("a6xx.xml", source)
        self.assertIn("adreno_pm4.xml", source)
        self.assertIn("GRAS_CL_VIEWPORT", source)
        self.assertIn("RB_MRT0_BASE", source)
        self.assertIn("VFD_MODE_CNTL", source)
        self.assertIn("SP_PS_MRT_REG0", source)
        self.assertIn("CP_DRAW_INDX_OFFSET", source)
        self.assertIn("not-emitted", source)
        self.assertIn("pending-gpu-h2-3d-state-live-validation", source)
        self.assertIn("preserve-v3208-ramdisk-overlay-v3210-init-helper-engine", source)
        self.assertIn("a90/audio/manifests/audio-setcal-internal-speaker-safe.manifest", source)
        self.assertIn("_patch_missing_audio_bundle_gate", source)
        self.assertIn("_overlay_preserved_v3208_ramdisk", source)
        self.assertIn("_finalize_manifest_after_overlay", source)


if __name__ == "__main__":
    unittest.main()
