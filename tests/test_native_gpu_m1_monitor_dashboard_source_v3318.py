from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
MONITOR = ROOT / "workspace/public/src/native-init/a90_monitor.c"
MONITOR_H = ROOT / "workspace/public/src/native-init/a90_monitor.h"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3318_gpu_m1_monitor_dashboard.py"
)


class NativeGpuM1MonitorDashboardSourceV3318Tests(unittest.TestCase):
    def test_v3318_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3318")
        self.assertEqual(runner.INIT_VERSION, "0.11.89")
        self.assertEqual(runner.INIT_BUILD, "v3318-gpu-m1-monitor-dashboard")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3318_gpu_m1_monitor_dashboard.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.89", required)
        self.assertIn(b"v3318-gpu-m1-monitor-dashboard", required)
        self.assertIn(b"m1-monitor-dashboard-probe", required)
        self.assertIn(b"gpu.m1.monitor.scope=static-dashboard-existing-draw-primitives", required)
        self.assertIn(b"gpu.m1.monitor.power_write_attempted=0", required)
        self.assertIn(b"gpu.m1.monitor.kgsl_submit_attempted=0", required)
        self.assertIn(b"gpu.m1.monitor.kms_present_attempted=1", required)
        self.assertIn(b"gpu.m1.monitor.present_rc=%d", required)
        self.assertIn(b"gpu.m1.monitor.result=dashboard-presented", required)

    def test_monitor_source_contains_static_dashboard_contract(self) -> None:
        source = MONITOR.read_text(encoding="utf-8")
        header = MONITOR_H.read_text(encoding="utf-8")

        self.assertIn("#define A90_MONITOR_M0_DEFAULT_SAMPLES 3U", header)
        self.assertIn("#define A90_MONITOR_M0_MAX_SAMPLES 16U", header)
        self.assertIn("#define A90_MONITOR_M1_DEFAULT_HOLD_MS 5000U", header)
        self.assertIn("#define A90_MONITOR_M1_MAX_HOLD_MS 60000U", header)
        self.assertIn("struct a90_monitor_history", source)
        self.assertIn("monitor_discover_topology", source)
        self.assertIn("monitor_parse_cpu_list_mask", source)
        self.assertIn("monitor_draw_dashboard", source)
        self.assertIn("monitor_draw_cluster_row", source)
        self.assertIn("monitor_draw_cpu_grid", source)
        self.assertIn("a90_kms_begin_frame", source)
        self.assertIn('a90_kms_present("gpu-m1-monitor-dashboard", true)', source)
        self.assertIn("cpufreq/related_cpus", source)
        self.assertIn("cpufreq/cpuinfo_max_freq", source)
        self.assertIn("Silver", source)
        self.assertIn("Gold", source)
        self.assertIn("Prime", source)
        self.assertIn("/proc/stat", source)
        self.assertIn("/proc/meminfo", source)
        self.assertIn("/proc/loadavg", source)
        self.assertIn("/sys/class/kgsl/kgsl-3d0/gpu_busy_percentage", source)
        self.assertIn("/sys/class/kgsl/kgsl-3d0/devfreq/cur_freq", source)
        self.assertIn("/sys/class/power_supply/battery/capacity", source)
        self.assertIn("a90_sensormap_collect_summary", source)
        self.assertIn("gpu.m1.monitor.kms_present_attempted=1", source)
        self.assertIn("gpu.m1.monitor.kgsl_submit_attempted=0", source)
        self.assertNotIn("O_WRONLY", source)
        self.assertNotIn("O_RDWR", source)

    def test_dispatch_routes_m1_monitor_dashboard(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn('strcmp(subcommand, "m1-monitor-dashboard-probe") == 0', source)
        self.assertIn('strcmp(subcommand, "monitor-dashboard-probe") == 0', source)
        self.assertIn('strcmp(argv[index], "--samples") == 0', source)
        self.assertIn('strcmp(argv[index], "--interval-ms") == 0', source)
        self.assertIn('strcmp(argv[index], "--hold-ms") == 0', source)
        self.assertIn("A90_MONITOR_M0_DEFAULT_SAMPLES", source)
        self.assertIn("A90_MONITOR_M1_DEFAULT_HOLD_MS", source)
        self.assertIn("A90_MONITOR_M1_MAX_HOLD_MS", source)
        self.assertIn("a90_monitor_m1_dashboard_probe(samples, interval_ms, hold_ms)", source)
        self.assertIn("m1-monitor-dashboard-probe [--samples N] [--interval-ms N] [--hold-ms N]", source)

    def test_builder_manifest_records_m1_live_validation(self) -> None:
        manifest = runner._minimal_gpu_m1_manifest()
        report = runner.render_report(
            {
                "decision": runner.DECISION,
                "boot_image": str(runner.BOOT_IMAGE),
                "boot_sha256": "0" * 64,
                "init_version": runner.INIT_VERSION,
                "init_build": runner.INIT_BUILD,
            },
            (),
            (),
        )

        self.assertEqual(manifest["scope"], "gpu-m1-static-system-monitor-dashboard")
        self.assertEqual(
            manifest["command"],
            "gpu m1-monitor-dashboard-probe --samples 3 --interval-ms 200 --hold-ms 5000",
        )
        self.assertEqual(manifest["expected_result"], "dashboard-presented")
        self.assertFalse(manifest["power_write_attempted"])
        self.assertFalse(manifest["kgsl_submit_attempted"])
        self.assertTrue(manifest["kms_present_attempted"])
        self.assertIn("require-cluster-count-3", manifest["next_live_validation"])
        self.assertIn("require-silver-gold-prime-derived-labels", manifest["next_live_validation"])
        self.assertIn("static dashboard renderer", report)
        self.assertIn("KMS-present only", report)
        self.assertIn("No backlight", report)


if __name__ == "__main__":
    unittest.main()
