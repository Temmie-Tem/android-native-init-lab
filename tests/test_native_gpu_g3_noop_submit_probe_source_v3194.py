from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
BASIC = ROOT / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3194_gpu_g3_noop_submit_probe.py"
)


class NativeGpuG3NoopSubmitProbeSourceV3194Tests(unittest.TestCase):
    def test_v3194_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3194")
        self.assertEqual(runner.INIT_VERSION, "0.11.25")
        self.assertEqual(runner.INIT_BUILD, "v3194-gpu-g3-noop-submit-probe")

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.25", required)
        self.assertIn(b"v3194-gpu-g3-noop-submit-probe", required)
        self.assertIn(b"gpu.g0.fwclass_prepare.result=ok", required)
        self.assertIn(b"gpu.g1.context.version=1", required)
        self.assertIn(b"g2-mmap-probe", required)
        self.assertIn(b"gpu.g2.gpuobj.version=1", required)
        self.assertIn(b"g3-noop-submit-probe", required)
        self.assertIn(b"noop-submit-probe", required)
        self.assertIn(b"gpu.g3.noop.version=1", required)
        self.assertIn(b"gpu.g3.noop.scope=kgsl-noop-submit-fence-probe", required)
        self.assertIn(b"gpu.g3.noop.parent_enters_open=0", required)
        self.assertIn(b"gpu.g3.noop.parent_enters_ioctl=0", required)
        self.assertIn(
            b"gpu.g3.noop.ioctl_allowlist=drawctxt_create,gpuobj_alloc,gpuobj_info,gpuobj_sync,gpu_command,timestamp_event,waittimestamp,readtimestamp,gpuobj_free,drawctxt_destroy",
            required,
        )
        self.assertIn(b"gpu.g3.noop.pm4_source=mesa-freedreno-pkt7-cp-nop", required)
        self.assertIn(b"gpu.g3.noop.mapped_write_attempted=1", required)
        self.assertIn(b"gpu.g3.noop.cache_sync_attempted=1", required)
        self.assertIn(b"gpu.g3.noop.submit_attempted=1", required)
        self.assertIn(b"gpu.g3.noop.fence_attempted=1", required)
        self.assertIn(b"gpu.g3.noop.render_attempted=0", required)
        self.assertIn(b"gpu.g3.noop.power_write_attempted=0", required)

    def test_dispatch_exposes_bounded_child_only_noop_submit_probe(self) -> None:
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
        self.assertIn("kill(pid, SIGKILL)", source)
        self.assertIn("waitpid(pid, &child_status, 0)", source)

    def test_help_lists_g0_g1_g2_and_g3_commands(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        basic = BASIC.read_text(encoding="utf-8")
        expected = "g3-noop-submit-probe [--timeout-ms N] [--materialize-devnode]"
        self.assertIn(expected, source)
        self.assertIn(expected, basic)
        self.assertIn("g0-fwclass-prepare", source)
        self.assertIn("g0-open-probe", source)
        self.assertIn("g1-context-probe", source)
        self.assertIn("g2-mmap-probe", source)

    def test_builder_manifest_records_g3_safety_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"gpu g3-noop-submit-probe --timeout-ms 5000 --materialize-devnode"', source)
        self.assertIn('"IOCTL_KGSL_GPU_COMMAND"', source)
        self.assertIn('"IOCTL_KGSL_TIMESTAMP_EVENT"', source)
        self.assertIn('"IOCTL_KGSL_DEVICE_WAITTIMESTAMP_CTXTID"', source)
        self.assertIn('"IOCTL_KGSL_CMDSTREAM_READTIMESTAMP_CTXTID"', source)
        self.assertIn('"IOCTL_KGSL_GPUOBJ_SYNC"', source)
        self.assertIn('"parent_enters_ioctl": False', source)
        self.assertIn('"pm4_source": "Mesa freedreno pkt7 helper + CP_NOP opcode"', source)
        self.assertIn('"type7": "0x70000000"', source)
        self.assertIn('"cp_nop": "0x10"', source)
        self.assertIn('"dwords": 2', source)
        self.assertIn('"freedreno-render"', source)
        self.assertIn('"solid-fill"', source)
        self.assertIn('"triangle-render"', source)
        self.assertIn('"KMS-blit"', source)
        self.assertIn('"GDSC-write"', source)
        self.assertIn('"proprietary-adreno-blob"', source)
        self.assertIn("NATIVE_INIT_V3193_GPU_G2_MMAP_PROBE_LIVE_2026-06-25.md", source)


if __name__ == "__main__":
    unittest.main()
