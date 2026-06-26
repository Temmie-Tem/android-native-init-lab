from __future__ import annotations

import unittest
from pathlib import Path

from _loader import load_script


ROOT = Path(__file__).resolve().parents[1]
DISPATCH = ROOT / "workspace/public/src/native-init/v319/80_shell_dispatch.inc.c"
MONITOR = ROOT / "workspace/public/src/native-init/a90_monitor.c"
MONITOR_H = ROOT / "workspace/public/src/native-init/a90_monitor.h"

runner = load_script(
    "workspace/public/src/scripts/revalidation/build_native_init_boot_v3317_gpu_m0_monitor_sampler.py"
)


class NativeGpuM0MonitorSamplerSourceV3317Tests(unittest.TestCase):
    def test_v3317_identity_and_required_markers(self) -> None:
        self.assertEqual(runner.CYCLE, "V3317")
        self.assertEqual(runner.INIT_VERSION, "0.11.88")
        self.assertEqual(runner.INIT_BUILD, "v3317-gpu-m0-monitor-sampler")
        self.assertEqual(
            runner.BOOT_IMAGE.name,
            "boot_linux_v3317_gpu_m0_monitor_sampler.img",
        )

        required = b"\n".join(runner.REQUIRED_STRINGS)
        self.assertIn(b"0.11.88", required)
        self.assertIn(b"v3317-gpu-m0-monitor-sampler", required)
        self.assertIn(b"m0-monitor-sampler-probe", required)
        self.assertIn(b"gpu.m0.monitor.scope=read-only-sysfs-proc-sampler", required)
        self.assertIn(b"gpu.m0.monitor.power_write_attempted=0", required)
        self.assertIn(b"gpu.m0.monitor.cluster.detect_source=cpufreq-related-cpus-plus-max-freq", required)
        self.assertIn(b"gpu.m0.monitor.history.capacity=%u", required)
        self.assertIn(b"gpu.m0.monitor.result=sampler-pass", required)

    def test_monitor_source_contains_read_only_sampler_contract(self) -> None:
        source = MONITOR.read_text(encoding="utf-8")
        header = MONITOR_H.read_text(encoding="utf-8")

        self.assertIn("#define A90_MONITOR_M0_DEFAULT_SAMPLES 3U", header)
        self.assertIn("#define A90_MONITOR_M0_MAX_SAMPLES 16U", header)
        self.assertIn("struct a90_monitor_history", source)
        self.assertIn("monitor_discover_topology", source)
        self.assertIn("monitor_parse_cpu_list_mask", source)
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
        self.assertIn("gpu.m0.monitor.kms_present_attempted=0", source)
        self.assertNotIn("O_WRONLY", source)
        self.assertNotIn("O_RDWR", source)

    def test_dispatch_routes_m0_monitor_sampler(self) -> None:
        source = DISPATCH.read_text(encoding="utf-8")

        self.assertIn('strcmp(subcommand, "m0-monitor-sampler-probe") == 0', source)
        self.assertIn('strcmp(subcommand, "monitor-sampler-probe") == 0', source)
        self.assertIn('strcmp(argv[index], "--samples") == 0', source)
        self.assertIn('strcmp(argv[index], "--interval-ms") == 0', source)
        self.assertIn("A90_MONITOR_M0_DEFAULT_SAMPLES", source)
        self.assertIn("A90_MONITOR_M0_MAX_INTERVAL_MS", source)
        self.assertIn("a90_monitor_m0_sampler_probe(samples, interval_ms)", source)
        self.assertIn("m0-monitor-sampler-probe [--samples N] [--interval-ms N]", source)

    def test_builder_manifest_records_m0_live_validation(self) -> None:
        manifest = runner._minimal_gpu_m0_manifest()
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

        self.assertEqual(manifest["scope"], "gpu-m0-system-monitor-read-only-sampler")
        self.assertEqual(manifest["command"], "gpu m0-monitor-sampler-probe --samples 3 --interval-ms 200")
        self.assertEqual(manifest["expected_result"], "sampler-pass")
        self.assertFalse(manifest["power_write_attempted"])
        self.assertFalse(manifest["kms_present_attempted"])
        self.assertIn("require-cluster-count-3", manifest["next_live_validation"])
        self.assertIn("require-silver-gold-prime-derived-labels", manifest["next_live_validation"])
        self.assertIn("read-only M0 sampler", report)
        self.assertIn("data-layer only", report)
        self.assertIn("No backlight", report)


if __name__ == "__main__":
    unittest.main()
