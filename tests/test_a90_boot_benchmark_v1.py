"""Host-only tests for A90 automatic-handoff benchmark markers."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = REPO_ROOT / "workspace/public/src/scripts/server-distro"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import a90_boot_benchmark_v1 as benchmark  # noqa: E402


def marker(stage: str, ms: int, *, cpu0: str = "1000000") -> str:
    values = {
        "schema": benchmark.SCHEMA,
        "stage": stage,
        "boottime_ms": str(ms),
        "clock_ok": "1",
        "telemetry_sampled": "1",
        "sample_duration_ms": "5",
        "prior_emit_duration_ms": "5",
        "cpu_temp_c": "41.2C",
        "gpu_temp_c": "39.0C",
        "battery_temp_c": "31.5C",
        "cpu_usage_pct": "12%",
        "gpu_usage_pct": "0%",
        "memory_mb": "512/6144MB",
        "load1": "0.25",
        "cpu0_khz": cpu0,
        "cpu4_khz": "1800000",
        "cpu7_khz": "2400000",
        "gpu_hz": "257000000",
        "battery_current_ua": "-450000",
        "battery_voltage_uv": "4000000",
        "power_now_raw": "na",
        "power_avg_raw": "na",
        "calculated_power_uw": "-1800000",
        "mmc_read_sectors": "100",
        "mmc_write_sectors": "200",
    }
    return "A90BENCH " + " ".join(f"{key}={values[key]}" for key in benchmark.FIELDS)


class A90BootBenchmarkV1Tests(unittest.TestCase):
    def test_parses_stage_metrics_and_phase_deltas(self) -> None:
        text = "\n".join(
            (
                marker("auto_handoff_dispatched", 1000),
                marker("handoff_begin", 1010),
                marker("source_sha_initial_done", 1110),
                marker("switch_root_exec", 1510),
            )
        )
        result = benchmark.parse_run([text])
        self.assertEqual(result["schema"], benchmark.RESULT_SCHEMA)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["phase_durations_ms"]["handoff_total_ms"], 505)
        self.assertEqual(result["phase_durations_ms"]["source_sha_initial_ms"], 95)
        self.assertEqual(result["records"][0]["cpu0_khz"], 1000000)
        self.assertEqual(result["records"][-1]["since_first_ms"], 510)

    def test_accepts_na_optional_numeric_telemetry(self) -> None:
        result = benchmark.parse_run([marker("native_cache_stage_ready", 20, cpu0="na")])
        self.assertIsNone(result["records"][0]["cpu0_khz"])

    def test_rejects_failed_boottime_sample(self) -> None:
        failed = marker("handoff_begin", 0).replace(" clock_ok=1", " clock_ok=0")
        with self.assertRaisesRegex(benchmark.BenchmarkError, "CLOCK_BOOTTIME"):
            benchmark.parse_run([failed])

    def test_rejects_field_drift(self) -> None:
        bad_fields = marker("handoff_begin", 10).replace(" cpu0_khz=", " cpu_zero_khz=")
        with self.assertRaisesRegex(benchmark.BenchmarkError, "fields changed"):
            benchmark.parse_run([bad_fields])

    def test_selects_unique_handoff_boot_from_accumulated_log(self) -> None:
        unarmed = "\n".join(
            (
                marker("native_cache_stage_ready", 100),
                marker("native_runtime_ready", 200),
                marker("auto_handoff_unarmed_native", 300),
            )
        )
        handoff = "\n".join(
            (
                marker("native_cache_stage_ready", 90),
                marker("native_runtime_ready", 190),
                marker("native_services_ready", 290),
                marker("auto_handoff_check", 300),
                marker("auto_handoff_dispatched", 310),
                marker("handoff_begin", 320),
                marker("source_sha_initial_done", 420),
                marker("display_release_done", 430),
                marker("source_sha_post_display_done", 530),
                marker("loop_attached", 640),
                marker("root_mounted", 650),
                marker("writable_set_ready", 655),
                marker("distro_init_verified", 660),
                marker("display_marker_ready", 670),
                marker("mount_moves_done", 680),
                marker("switch_root_exec", 690),
            )
        )
        returned = "\n".join(
            (
                marker("native_cache_stage_ready", 110),
                marker("native_runtime_ready", 210),
                marker("auto_handoff_latched_native", 310),
            )
        )
        result = benchmark.parse_run(
            ["\n".join((unarmed, handoff, returned))],
            require_complete=True,
        )
        self.assertEqual(result["boot_segments_total"], 3)
        self.assertEqual(result["selected_segment_index"], 1)
        self.assertEqual(result["status"], "complete")

    def test_complete_handoff_accepts_missing_pre_runtime_capture_marker(self) -> None:
        text = "\n".join(
            marker(stage, 100 + index * 10)
            for index, stage in enumerate(benchmark.COMPLETE_STAGES)
        )
        result = benchmark.parse_run([text], require_complete=True)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["missing_complete_stages"], [])
        self.assertIsNone(result["phase_durations_ms"]["native_runtime_ms"])
        self.assertEqual(
            [record["stage"] for record in result["records"]],
            list(benchmark.COMPLETE_STAGES),
        )

    def test_complete_handoff_requires_auto_handoff_check(self) -> None:
        stages = [
            stage
            for stage in benchmark.COMPLETE_STAGES
            if stage != "auto_handoff_check"
        ]
        text = "\n".join(
            marker(stage, 100 + index * 10)
            for index, stage in enumerate(stages)
        )
        with self.assertRaisesRegex(
            benchmark.BenchmarkError,
            "auto_handoff_check",
        ):
            benchmark.parse_run([text], require_complete=True)

    def test_rejects_complete_handoff_with_inverted_stage_order(self) -> None:
        stages = list(benchmark.COMPLETE_STAGES)
        first = stages.index("handoff_begin")
        second = stages.index("source_receipt_initial_done")
        stages[first], stages[second] = stages[second], stages[first]
        text = "\n".join(
            marker(stage, 100 + index * 10)
            for index, stage in enumerate(stages)
        )
        with self.assertRaisesRegex(benchmark.BenchmarkError, "out of order"):
            benchmark.parse_run([text], require_complete=True)

    def test_rejects_hybrid_legacy_and_fast_integrity_stage_families(self) -> None:
        stages = list(benchmark.LEGACY_COMPLETE_STAGES)
        stages.insert(
            stages.index("source_sha_initial_done") + 1,
            "source_receipt_initial_done",
        )
        stages.insert(
            stages.index("source_sha_post_display_done") + 1,
            "source_identity_post_display_done",
        )
        text = "\n".join(
            marker(stage, 100 + index * 10)
            for index, stage in enumerate(stages)
        )
        with self.assertRaisesRegex(benchmark.BenchmarkError, "mixes legacy and fast"):
            benchmark.parse_run([text], require_complete=True)

    def test_deduplicates_identical_marker_and_splits_conflict(self) -> None:
        line = marker("handoff_begin", 10)
        result = benchmark.parse_run([line + "\n" + line])
        self.assertEqual(len(result["records"]), 1)
        segments = benchmark.parse_runs(
            [line + "\n" + marker("handoff_begin", 11)]
        )
        self.assertEqual(len(segments), 2)

    def test_compares_phase_duration(self) -> None:
        baseline = benchmark.parse_run(
            [marker("auto_handoff_dispatched", 100) + "\n" + marker("switch_root_exec", 600)]
        )
        candidate = benchmark.parse_run(
            [marker("auto_handoff_dispatched", 100) + "\n" + marker("switch_root_exec", 540)]
        )
        comparison = benchmark.compare_runs(baseline, candidate)
        self.assertEqual(comparison["schema"], benchmark.COMPARISON_SCHEMA)
        self.assertEqual(
            comparison["phase_comparison"]["handoff_total_ms"]["delta_ms"],
            -60,
        )

    def test_compares_legacy_sha_to_fast_receipt_as_source_integrity(self) -> None:
        legacy = benchmark.parse_run([
            marker("handoff_begin", 100)
            + "\n"
            + marker("source_sha_initial_done", 200)
        ])
        fast = benchmark.parse_run([
            marker("handoff_begin", 100)
            + "\n"
            + marker("source_receipt_initial_done", 110)
        ])
        comparison = benchmark.compare_runs(legacy, fast)
        self.assertEqual(
            comparison["phase_comparison"]["source_integrity_initial_ms"]["delta_ms"],
            -90,
        )


if __name__ == "__main__":
    unittest.main()
