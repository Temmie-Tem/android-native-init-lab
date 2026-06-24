from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs/reports/NATIVE_INIT_V3176_GPU_G0_HOST_SOURCE_AUDIT_2026-06-25.md"
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
BASIC = ROOT / "workspace/public/src/native-init/v319/60_shell_basic_commands.inc.c"


class NativeGpuG0HostSourceAuditV3176Tests(unittest.TestCase):
    def test_report_records_g0_scope_and_video_prereq(self) -> None:
        report = REPORT.read_text(encoding="utf-8")

        self.assertIn("Cycle: `V3176`", report)
        self.assertIn("HOST-SIDE SOURCE AUDIT PASS; live bounded probe still pending", report)
        self.assertIn("Video 0.11.0 promotion is closed", report)
        self.assertIn("G0 remains the only active GPU rung", report)
        self.assertIn("G1-G5 are still gated", report)

    def test_report_contains_load_bearing_kernel_evidence(self) -> None:
        report = REPORT.read_text(encoding="utf-8")

        for marker in (
            "kgsl.c:4982-4990",
            "kgsl.c:1413-1445",
            "kgsl.c:1372-1399",
            "adreno.c:1689-1719",
            "adreno_a6xx.c:1123-1143",
            "adreno.c:1926-2020",
            "adreno_a6xx_gmu.c:346-363",
            "adreno_a6xx_gmu.c:574-620",
            "adreno_a6xx_gmu.c:1008-1116",
            "sm8150-gpu.dtsi:66-83",
            "sm8150-gpu.dtsi:141-145",
            "sm8150-gpu.dtsi:350-385",
        ):
            self.assertIn(marker, report)

    def test_report_states_root_cause_and_bright_line_decision(self) -> None:
        report = REPORT.read_text(encoding="utf-8")

        self.assertIn("not a passive devnode open", report)
        self.assertIn("runtime PM, Adreno init, firmware request, GMU cold boot", report)
        self.assertIn("There is no clean standalone sysfs bring-up hook", report)
        self.assertIn("only bright-line-clean path is to let the existing kernel KGSL runtime-PM/open path", report)
        self.assertIn("Direct GDSC/regulator/PMIC/GPIO/power-rail writes remain forbidden", report)
        self.assertIn("do not run unbounded open", report)

    def test_native_probe_surface_is_still_bounded(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")
        start = source.index("struct gpu_g0_open_probe_result")
        end = source.index("static int handle_audio", start)
        gpu_section = source[start:end]

        self.assertIn("pid = fork();", gpu_section)
        self.assertIn("return gpu_g0_open_probe_child(GPU_G0_DEVNODE, flags, pipefd[1]);", gpu_section)
        self.assertIn("fd = open(path, flags | O_CLOEXEC);", gpu_section)
        self.assertIn("poll(&pfd, 1, poll_ms)", gpu_section)
        self.assertIn("kill(pid, SIGKILL)", gpu_section)
        self.assertIn("GPU_G0_MAX_TIMEOUT_MS 10000", gpu_section)
        self.assertIn('"gpu.g0.open.parent_enters_open=0', gpu_section)
        self.assertIn('"gpu.g0.open.ioctl_attempted=0', gpu_section)
        self.assertIn('"gpu.g0.open.mmap_attempted=0', gpu_section)
        self.assertIn('"gpu.g0.open.power_write_attempted=0', gpu_section)
        self.assertNotIn("ioctl(", gpu_section)
        self.assertNotIn("mmap(", gpu_section)

    def test_gpu_command_is_exposed_without_advancing_to_g1(self) -> None:
        dispatch = DISPATCH.read_text(encoding="utf-8")
        basic = BASIC.read_text(encoding="utf-8")

        self.assertIn('gpu [g0-status|g0-open-probe', dispatch)
        self.assertIn("gpu [g0-status|g0-open-probe", basic)
        self.assertNotIn("gpu g1", dispatch.lower())
        self.assertNotIn("kgsl_gpuobj_alloc", dispatch)
        self.assertNotIn("IOCTL_KGSL_GPUOBJ_ALLOC", dispatch)


if __name__ == "__main__":
    unittest.main()
