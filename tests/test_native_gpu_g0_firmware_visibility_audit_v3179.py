from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = (
    ROOT
    / "docs/reports/NATIVE_INIT_V3179_GPU_G0_FIRMWARE_VISIBILITY_AUDIT_2026-06-25.md"
)
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"


class NativeGpuG0FirmwareVisibilityAuditV3179Tests(unittest.TestCase):
    def test_report_records_firmware_artifact_presence_without_claiming_live_visibility(self) -> None:
        report = REPORT.read_text(encoding="utf-8")

        self.assertIn("v3179-gpu-g0-firmware-visibility-host-audit", report)
        self.assertIn("live runtime visibility still pending", report)
        self.assertIn("/firmware/a630_sqe.fw", report)
        self.assertIn("/firmware/a640_gmu.bin", report)
        self.assertIn("image/a640_zap.mdt", report)
        self.assertIn("a0e1b583f620fabe32729ce367959d1960638663244d7d0cfc21b9a5215a018b", report)
        self.assertIn("3ff0c02708bbe78641db887fa62f3a7f9337934d0c2ce0b961ef7c43172591d2", report)
        self.assertIn("firmware visibility fix or mount/path", report)
        self.assertIn("GMU/GDSC/RPMh/HFI/OOB startup", report)
        self.assertIn("power-rail writes remain forbidden", report)
        self.assertIn("No device contact, flash, reboot, KGSL open", report)

    def test_v3177_status_surface_checks_runtime_firmware_paths_needed_by_report(self) -> None:
        dispatch = DISPATCH.read_text(encoding="utf-8")
        start = dispatch.index("static int gpu_g0_status(void)")
        end = dispatch.index("static int gpu_g0_open_probe_child", start)
        status = dispatch[start:end]

        self.assertIn('"/sys/module/firmware_class/parameters/path"', status)
        self.assertIn('"/vendor/firmware/a630_sqe.fw"', status)
        self.assertIn('"/vendor/firmware/a640_gmu.bin"', status)
        self.assertIn('"/firmware/a630_sqe.fw"', status)
        self.assertIn('"/firmware/a640_gmu.bin"', status)
        self.assertIn('"/vendor/firmware/a640_zap.mdt"', status)
        self.assertIn('"/firmware_mnt/image/a640_zap.mdt"', status)


if __name__ == "__main__":
    unittest.main()
