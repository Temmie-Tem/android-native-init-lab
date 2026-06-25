from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
BASIC = ROOT / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3196_gpu_g4_solid_fill_probe.py"
)


class NativeGpuG4SolidFillProbeSourceV3196Tests(unittest.TestCase):
    def test_v3196_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3196")
        self.assertEqual(runner.INIT_VERSION, "0.11.26")
        self.assertEqual(runner.INIT_BUILD, "v3196-gpu-g4-solid-fill-probe")

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.26", required)
        self.assertIn(b"v3196-gpu-g4-solid-fill-probe", required)
        self.assertIn(b"gpu.g0.fwclass_prepare.result=ok", required)
        self.assertIn(b"gpu.g1.context.version=1", required)
        self.assertIn(b"g2-mmap-probe", required)
        self.assertIn(b"gpu.g2.gpuobj.version=1", required)
        self.assertIn(b"g3-noop-submit-probe", required)
        self.assertIn(b"gpu.g3.noop.version=1", required)
        self.assertIn(b"g4-solid-fill-probe", required)
        self.assertIn(b"solid-fill-probe", required)
        self.assertIn(b"gpu.g4.fill.version=1", required)
        self.assertIn(b"gpu.g4.fill.scope=kgsl-a2d-solid-fill-readback-probe", required)
        self.assertIn(b"gpu.g4.fill.parent_enters_open=0", required)
        self.assertIn(b"gpu.g4.fill.parent_enters_ioctl=0", required)
        self.assertIn(
            b"gpu.g4.fill.ioctl_allowlist=drawctxt_create,gpuobj_alloc,gpuobj_info,gpuobj_sync,gpu_command,timestamp_event,waittimestamp,readtimestamp,gpuobj_free,drawctxt_destroy",
            required,
        )
        self.assertIn(
            b"gpu.g4.fill.pm4_source=mesa-freedreno-a6xx-fd6-clear-buffer-cp-blit-a2d",
            required,
        )
        self.assertIn(b"gpu.g4.fill.fmt6_32_uint=0x%x", required)
        self.assertIn(b"gpu.g4.fill.r2d_int32=0x%x", required)
        self.assertIn(b"gpu.g4.fill.render_attempted=1", required)
        self.assertIn(b"gpu.g4.fill.triangle_attempted=0", required)
        self.assertIn(b"gpu.g4.fill.kms_blit_attempted=0", required)
        self.assertIn(b"gpu.g4.fill.power_write_attempted=0", required)
        self.assertIn(b"gpu.g4.fill.proprietary_blob_attempted=0", required)
        self.assertIn(b"gpu.g4.fill.readback_verified=%d", required)

    def test_dispatch_exposes_bounded_child_only_solid_fill_probe(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn('strcmp(subcommand, "g4-solid-fill-probe")', source)
        self.assertIn('strcmp(subcommand, "solid-fill-probe")', source)
        self.assertIn("static int gpu_g4_solid_fill_probe_child(int write_fd)", source)
        self.assertIn("static int gpu_g4_solid_fill_probe(int timeout_ms", source)
        self.assertIn("struct gpu_g4_solid_fill_probe_result", source)
        self.assertIn("GPU_G4_A6XX_FMT6_32_UINT 0x4bU", source)
        self.assertIn("GPU_G4_A6XX_R2D_INT32 0x7U", source)
        self.assertIn("GPU_G4_A6XX_TILE6_LINEAR 0x0U", source)
        self.assertIn("GPU_G4_PM4_CP_BLIT 0x2cU", source)
        self.assertIn("GPU_G4_PM4_CP_SET_MARKER 0x65U", source)
        self.assertIn("GPU_G4_EVENT_PC_CCU_FLUSH_COLOR_TS 0x1dU", source)
        self.assertIn("GPU_G4_EVENT_CACHE_INVALIDATE 0x31U", source)
        self.assertIn("GPU_KGSL_GPUMEM_CACHE_FROM_GPU", source)
        self.assertIn("gpu_g4_pm4_pkt4_hdr", source)
        self.assertIn("gpu_g4_build_solid_fill_pm4", source)
        self.assertIn("GPU_G4_FILL_PATTERN 0xa5c3f00dU", source)
        self.assertIn("GPU_G4_SENTINEL_PATTERN 0x11111111U", source)
        self.assertIn("readback_mismatch_count", source)
        self.assertIn('"gpu.g4.fill.parent_enters_open=0', source)
        self.assertIn('"gpu.g4.fill.parent_enters_ioctl=0', source)
        self.assertIn('"gpu.g4.fill.render_attempted=1', source)
        self.assertIn('"gpu.g4.fill.triangle_attempted=0', source)
        self.assertIn('"gpu.g4.fill.kms_blit_attempted=0', source)
        self.assertIn('"gpu.g4.fill.power_write_attempted=0', source)
        self.assertIn("kill(pid, SIGKILL)", source)
        self.assertIn("waitpid(pid, &child_status, 0)", source)

    def test_g3_noop_submit_command_remains_available(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn('strcmp(subcommand, "g3-noop-submit-probe")', source)
        self.assertIn('strcmp(subcommand, "noop-submit-probe")', source)
        self.assertIn("static int gpu_g3_noop_submit_probe_child(int write_fd)", source)
        self.assertIn("static int gpu_g3_noop_submit_probe(int timeout_ms", source)
        self.assertIn("GPU_IOCTL_KGSL_DRAWCTXT_CREATE", source)
        self.assertIn("GPU_IOCTL_KGSL_GPUOBJ_ALLOC", source)
        self.assertIn("GPU_IOCTL_KGSL_GPUOBJ_INFO", source)
        self.assertIn("GPU_IOCTL_KGSL_GPUOBJ_SYNC", source)
        self.assertIn("GPU_IOCTL_KGSL_GPU_COMMAND", source)
        self.assertIn("GPU_IOCTL_KGSL_TIMESTAMP_EVENT", source)
        self.assertIn("GPU_IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID", source)
        self.assertIn("GPU_IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID", source)
        self.assertIn("GPU_IOCTL_KGSL_GPUOBJ_FREE", source)
        self.assertIn("GPU_IOCTL_KGSL_DRAWCTXT_DESTROY", source)
        self.assertIn("GPU_G3_NOOP_ALLOC_SIZE 4096ULL", source)
        self.assertIn("GPU_G3_NOOP_DWORDS 2U", source)
        self.assertIn("GPU_G3_WAIT_TIMEOUT_MS 1000U", source)
        self.assertIn("GPU_G3_PM4_CP_TYPE7_PKT 0x70000000U", source)
        self.assertIn("GPU_G3_PM4_CP_NOP 0x10U", source)
        self.assertIn("gpu_g3_pm4_pkt7_hdr", source)
        self.assertIn("GPU_KGSL_CMDLIST_IB", source)
        self.assertIn("GPU_KGSL_OBJLIST_MEMOBJ", source)
        self.assertIn(
            "GPU_KGSL_GPUMEM_CACHE_TO_GPU | GPU_KGSL_GPUMEM_CACHE_RANGE",
            source,
        )
        self.assertIn("GPU_KGSL_TIMESTAMP_EVENT_FENCE", source)
        self.assertIn("mmap(NULL,", source)
        self.assertIn("PROT_READ | PROT_WRITE", source)
        self.assertIn("MAP_SHARED", source)
        self.assertIn("__sync_synchronize()", source)
        self.assertIn("poll(&pfd, 1, 0)", source)
        self.assertIn('"gpu.g3.noop.parent_enters_open=0', source)
        self.assertIn('"gpu.g3.noop.parent_enters_ioctl=0', source)
        self.assertIn('"gpu.g3.noop.render_attempted=0', source)
        self.assertIn('"gpu.g3.noop.power_write_attempted=0', source)

    def test_help_lists_g0_g1_g2_g3_and_g4_commands(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        basic = BASIC.read_text(encoding="utf-8")
        self.assertIn("g3-noop-submit-probe [--timeout-ms N] [--materialize-devnode]", source)
        self.assertIn("g3-noop-submit-probe [--timeout-ms N] [--materialize-devnode]", basic)
        self.assertIn("g4-solid-fill-probe [--timeout-ms N] [--materialize-devnode]", source)
        self.assertIn("g4-solid-fill-probe [--timeout-ms N] [--materialize-devnode]", basic)
        self.assertIn("g0-fwclass-prepare", source)
        self.assertIn("g0-open-probe", source)
        self.assertIn("g1-context-probe", source)
        self.assertIn("g2-mmap-probe", source)

    def test_builder_manifest_records_g4_safety_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"gpu g4-solid-fill-probe --timeout-ms 5000 --materialize-devnode"', source)
        self.assertIn('"gpu g3-noop-submit-probe --timeout-ms 5000 --materialize-devnode"', source)
        self.assertIn('"IOCTL_KGSL_GPU_COMMAND"', source)
        self.assertIn('"IOCTL_KGSL_TIMESTAMP_EVENT"', source)
        self.assertIn('"IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID"', source)
        self.assertIn('"IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID"', source)
        self.assertIn('"IOCTL_KGSL_GPUOBJ_SYNC"', source)
        self.assertIn('"parent_enters_ioctl": False', source)
        self.assertIn('"pm4_source": "Mesa freedreno A6xx fd6_clear_buffer CP_BLIT A2D solid color path"', source)
        self.assertIn('"type4": "0x40000000"', source)
        self.assertIn('"type7": "0x70000000"', source)
        self.assertIn('"cp_blit": "0x2c"', source)
        self.assertIn('"fmt6_32_uint": "0x4b"', source)
        self.assertIn('"r2d_int32": "0x7"', source)
        self.assertIn('"readback_sync": "KGSL_GPUMEM_CACHE_FROM_GPU | KGSL_GPUMEM_CACHE_RANGE"', source)
        self.assertIn('"triangle-render"', source)
        self.assertIn('"KMS-blit"', source)
        self.assertIn('"GDSC-write"', source)
        self.assertIn('"proprietary-adreno-blob"', source)
        self.assertIn("NATIVE_INIT_V3195_GPU_G3_NOOP_SUBMIT_PROBE_LIVE_2026-06-25.md", source)


if __name__ == "__main__":
    unittest.main()
