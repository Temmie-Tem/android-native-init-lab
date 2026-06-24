from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
BASIC = ROOT / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3188_gpu_g1_context_probe.py"
)


class NativeGpuG1ContextProbeSourceV3188Tests(unittest.TestCase):
    def test_v3188_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3188")
        self.assertEqual(runner.INIT_VERSION, "0.11.22")
        self.assertEqual(runner.INIT_BUILD, "v3188-gpu-g1-context-probe")

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.22", required)
        self.assertIn(b"v3188-gpu-g1-context-probe", required)
        self.assertIn(b"gpu.g0.fwclass_prepare.result=ok", required)
        self.assertIn(b"g1-context-probe", required)
        self.assertIn(b"gpu.g1.context.version=1", required)
        self.assertIn(b"gpu.g1.context.parent_enters_ioctl=0", required)
        self.assertIn(b"gpu.g1.context.ioctl_allowlist=drawctxt_create,drawctxt_destroy", required)
        self.assertIn(b"gpu.g1.context.gpuobj_alloc_attempted=0", required)
        self.assertIn(b"gpu.g1.context.submit_attempted=0", required)
        self.assertIn(b"gpu.g1.context.power_write_attempted=0", required)

    def test_dispatch_exposes_bounded_child_only_context_probe(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn('strcmp(subcommand, "g1-context-probe")', source)
        self.assertIn('strcmp(subcommand, "context-probe")', source)
        self.assertIn("static int gpu_g1_context_probe_child", source)
        self.assertIn("static int gpu_g1_context_probe(int timeout_ms", source)
        self.assertIn("GPU_IOCTL_KGSL_DRAWCTXT_CREATE", source)
        self.assertIn("GPU_IOCTL_KGSL_DRAWCTXT_DESTROY", source)
        self.assertIn("GPU_G1_CONTEXT_FLAGS", source)
        self.assertIn("GPU_KGSL_CONTEXT_NO_GMEM_ALLOC", source)
        self.assertIn("GPU_KGSL_CONTEXT_PREAMBLE", source)
        self.assertIn("GPU_KGSL_CONTEXT_NO_SNAPSHOT", source)
        self.assertIn('"gpu.g1.context.parent_enters_open=0', source)
        self.assertIn('"gpu.g1.context.parent_enters_ioctl=0', source)
        self.assertIn('"gpu.g1.context.mmap_attempted=0', source)
        self.assertIn('"gpu.g1.context.gpuobj_alloc_attempted=0', source)
        self.assertIn('"gpu.g1.context.submit_attempted=0', source)
        self.assertIn('"gpu.g1.context.power_write_attempted=0', source)
        self.assertIn("kill(pid, SIGKILL)", source)

    def test_help_lists_g0_and_g1_commands(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        basic = BASIC.read_text(encoding="utf-8")
        expected = "g1-context-probe [--timeout-ms N] [--materialize-devnode]"
        self.assertIn(expected, source)
        self.assertIn(expected, basic)
        self.assertIn("g0-fwclass-prepare", source)
        self.assertIn("g0-open-probe", source)

    def test_builder_manifest_records_g1_safety_boundary(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('"gpu g1-context-probe --timeout-ms 5000 --materialize-devnode"', source)
        self.assertIn('"IOCTL_KGSL_DRAWCTXT_CREATE"', source)
        self.assertIn('"IOCTL_KGSL_DRAWCTXT_DESTROY"', source)
        self.assertIn('"parent_enters_ioctl": False', source)
        self.assertIn('"kgsl-gpuobj-alloc"', source)
        self.assertIn('"kgsl-submit"', source)
        self.assertIn('"freedreno-render"', source)
        self.assertIn('"GDSC-write"', source)
        self.assertIn("NATIVE_INIT_V3187_GPU_G0_FRESH_BOOT_REPEAT_2026-06-25.md", source)


if __name__ == "__main__":
    unittest.main()
