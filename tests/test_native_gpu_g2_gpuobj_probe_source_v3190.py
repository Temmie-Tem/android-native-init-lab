from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
BASIC = ROOT / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3190_gpu_g2_gpuobj_probe.py"
)


class NativeGpuG2GpuobjProbeSourceV3190Tests(unittest.TestCase):
    def test_v3190_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3190")
        self.assertEqual(runner.INIT_VERSION, "0.11.23")
        self.assertEqual(runner.INIT_BUILD, "v3190-gpu-g2-gpuobj-probe")

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.23", required)
        self.assertIn(b"v3190-gpu-g2-gpuobj-probe", required)
        self.assertIn(b"gpu.g0.fwclass_prepare.result=ok", required)
        self.assertIn(b"gpu.g1.context.version=1", required)
        self.assertIn(b"g2-gpuobj-probe", required)
        self.assertIn(b"gpu.g2.gpuobj.version=1", required)
        self.assertIn(b"gpu.g2.gpuobj.parent_enters_ioctl=0", required)
        self.assertIn(
            b"gpu.g2.gpuobj.ioctl_allowlist=drawctxt_create,gpuobj_alloc,gpuobj_free,drawctxt_destroy",
            required,
        )
        self.assertIn(b"gpu.g2.gpuobj.alloc_size=%llu", required)
        self.assertIn(b"gpu.g2.gpuobj.mmap_attempted=0", required)
        self.assertIn(b"gpu.g2.gpuobj.submit_attempted=0", required)
        self.assertIn(b"gpu.g2.gpuobj.power_write_attempted=0", required)

    def test_dispatch_exposes_bounded_child_only_gpuobj_probe(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn('strcmp(subcommand, "g2-gpuobj-probe")', source)
        self.assertIn('strcmp(subcommand, "gpuobj-probe")', source)
        self.assertIn("static int gpu_g2_gpuobj_probe_child", source)
        self.assertIn("static int gpu_g2_gpuobj_probe(int timeout_ms", source)
        self.assertIn("GPU_IOCTL_KGSL_DRAWCTXT_CREATE", source)
        self.assertIn("GPU_IOCTL_KGSL_GPUOBJ_ALLOC", source)
        self.assertIn("GPU_IOCTL_KGSL_GPUOBJ_FREE", source)
        self.assertIn("GPU_IOCTL_KGSL_DRAWCTXT_DESTROY", source)
        self.assertIn("GPU_G2_GPUOBJ_ALLOC_SIZE 4096ULL", source)
        self.assertIn("GPU_G2_GPUOBJ_ALLOC_FLAGS 0ULL", source)
        self.assertIn('"gpu.g2.gpuobj.parent_enters_open=0', source)
        self.assertIn('"gpu.g2.gpuobj.parent_enters_ioctl=0', source)
        self.assertIn('"gpu.g2.gpuobj.mmap_attempted=0', source)
        self.assertIn('"gpu.g2.gpuobj.submit_attempted=0', source)
        self.assertIn('"gpu.g2.gpuobj.power_write_attempted=0', source)
        self.assertIn("kill(pid, SIGKILL)", source)
        self.assertIn("waitpid(pid, &child_status, 0)", source)

    def test_help_lists_g0_g1_and_g2_commands(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        basic = BASIC.read_text(encoding="utf-8")
        expected = "g2-gpuobj-probe [--timeout-ms N] [--materialize-devnode]"
        self.assertIn(expected, source)
        self.assertIn(expected, basic)
        self.assertIn("g0-fwclass-prepare", source)
        self.assertIn("g0-open-probe", source)
        self.assertIn("g1-context-probe", source)

    def test_builder_manifest_records_g2a_safety_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"gpu g2-gpuobj-probe --timeout-ms 5000 --materialize-devnode"', source)
        self.assertIn('"IOCTL_KGSL_DRAWCTXT_CREATE"', source)
        self.assertIn('"IOCTL_KGSL_GPUOBJ_ALLOC"', source)
        self.assertIn('"IOCTL_KGSL_GPUOBJ_FREE"', source)
        self.assertIn('"IOCTL_KGSL_DRAWCTXT_DESTROY"', source)
        self.assertIn('"parent_enters_ioctl": False', source)
        self.assertIn('"gpuobj_alloc_size": 4096', source)
        self.assertIn('"kgsl-mmap"', source)
        self.assertIn('"kgsl-submit"', source)
        self.assertIn('"freedreno-render"', source)
        self.assertIn('"GDSC-write"', source)
        self.assertIn("NATIVE_INIT_V3189_GPU_G1_CONTEXT_PROBE_LIVE_2026-06-25.md", source)


if __name__ == "__main__":
    unittest.main()
