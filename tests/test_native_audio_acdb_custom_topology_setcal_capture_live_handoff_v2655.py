"""Tests for the V2655 custom-topology ACDB SET capture live wrapper."""

from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2655 = load_revalidation("native_audio_acdb_custom_topology_setcal_capture_live_handoff_v2655")


def args(**overrides: object) -> argparse.Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2655-test-"))
    defaults: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "write_report": False,
        "report_path": root / "report.md",
        "build_v2654_artifacts": False,
        "v2654_build_root": v2655.v2654.DEFAULT_BUILD_ROOT,
        "v2654_manifest_path": v2655.v2654.DEFAULT_MANIFEST,
        "helper_path": None,
        "helper_sha256": None,
        "preload_path": None,
        "preload_sha256": None,
        "out_dir": root / "run",
        "adb": "adb",
        "serial": None,
        "from_native": True,
        "android_timeout": 240.0,
        "flash_timeout": 420.0,
        "adb_command_timeout": 90.0,
        "adb_pull_timeout": 120.0,
        "helper_timeout": 90.0,
        "android_root_recheck_attempts": v2655.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS,
        "android_root_recheck_sleep_sec": v2655.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC,
        "android_settle_adb_retry_attempts": v2655.v2490.DEFAULT_SETTLE_ADB_RETRY_ATTEMPTS,
        "android_settle_adb_retry_sleep_sec": v2655.v2490.DEFAULT_SETTLE_ADB_RETRY_SLEEP_SEC,
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def setcal_event(seq: int, cal_type: int, cal_size: int, mem_handle: int, dmabuf_status: str) -> dict[str, object]:
    """Build a synthetic setcal_capture event matching the V2654 preload schema."""
    return {
        "event": "setcal_capture",
        "pid": 4198,
        "tid": 4198,
        "sequence": seq,
        "fd": 31,
        "request": "0xc00461cb",
        "header_valid": True,
        "data_size": 48,
        "version": 0,
        "cal_type": cal_type,
        "cal_type_size": 32,
        "cal_hdr_version": 3,
        "buffer_number": 0,
        "cal_size": cal_size,
        "mem_handle": mem_handle,
        "set_arg": {
            "path": f"/data/local/tmp/a90-acdb-ownget/setcal-arg-{seq:04d}.bin",
            "len": 48,
            "dump_rc": 0,
            "sha256": f"{cal_type:064x}",
            "all_zero": False,
        },
        "dmabuf": {
            "status": dmabuf_status,
            "path": (
                f"/data/local/tmp/a90-acdb-ownget/setcal-dmabuf-{seq:04d}.bin"
                if dmabuf_status == "dumped" else ""
            ),
            "len": cal_size if dmabuf_status == "dumped" else 0,
            "dump_rc": 0 if dmabuf_status == "dumped" else -1,
            "mmap_errno": 0 if dmabuf_status == "dumped" else 5,
            "sha256": (f"{seq:064x}" if dmabuf_status == "dumped" else "0" * 64),
            "all_zero": False,
        },
    }


def custom_topology_rows(all_dumped: bool = True) -> list[dict[str, object]]:
    failed = "dumped" if all_dumped else "mmap-failed"
    return [
        setcal_event(1, 39, 4916, 35, "dumped"),
        setcal_event(2, 20, 0, -1, "header-only"),
        setcal_event(3, 10, 2048, 36, "dumped"),
        setcal_event(4, 14, 1024, 37, "dumped"),
        setcal_event(5, 24, 4096, 38, failed),
    ]


class NativeAudioAcdbCustomTopologySetcalCaptureLiveHandoffV2655(unittest.TestCase):
    def test_read_v2654_manifest_checks_setcal_contract(self) -> None:
        manifest = v2655.read_v2654_manifest(v2655.v2654.DEFAULT_MANIFEST)

        self.assertTrue(manifest["ok"], manifest)
        self.assertTrue(manifest["setcal_contract_ok"], manifest)

    def test_summarize_custom_topology_captured(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2655-full-"))
        write_jsonl(root / "setcal-events.jsonl", custom_topology_rows(all_dumped=True))

        summary = v2655.summarize_setcal_capture(root)

        self.assertEqual(summary["classification"], "v2655-custom-topology-setcal-captured")
        self.assertTrue(summary["success"])
        self.assertTrue(summary["operator_valuable"])
        self.assertEqual(summary["setcal_record_count"], 5)
        self.assertEqual(summary["custom_cal_types_captured"], [10, 14, 24])
        self.assertEqual(summary["missing_custom_cal_types"], [])
        self.assertTrue(summary["custom_topology_complete"])
        self.assertTrue(summary["custom_payloads_dumped"])
        self.assertEqual(summary["custom_payload_record_count"], 3)
        self.assertEqual(summary["supplemental_cal20_count"], 1)
        self.assertEqual(summary["dmabuf_dumped_count"], 4)
        self.assertEqual(summary["dmabuf_failed_count"], 0)
        self.assertEqual(summary["real_audio_set_pass_through_count"], 0)

    def test_summarize_partial_when_custom_dmabuf_fails(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2655-partial-"))
        write_jsonl(root / "setcal-events.jsonl", custom_topology_rows(all_dumped=False))

        summary = v2655.summarize_setcal_capture(root)

        self.assertEqual(summary["classification"], "v2655-custom-topology-setcal-partial")
        self.assertFalse(summary["success"])
        self.assertTrue(summary["partial_success"])
        self.assertTrue(summary["custom_topology_complete"])
        self.assertFalse(summary["custom_payloads_dumped"])
        self.assertEqual(summary["custom_payload_failed_count"], 1)
        self.assertEqual(summary["dmabuf_failed_count"], 1)

    def test_summarize_records_without_custom_topology(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2655-nocustom-"))
        write_jsonl(
            root / "setcal-events.jsonl",
            [
                setcal_event(1, 20, 0, -1, "header-only"),
                setcal_event(2, 39, 4916, 20, "dumped"),
            ],
        )

        summary = v2655.summarize_setcal_capture(root)

        self.assertEqual(summary["classification"], "v2655-setcal-records-no-custom-topology")
        self.assertTrue(summary["partial_success"])
        self.assertFalse(summary["custom_topology_complete"])
        self.assertEqual(summary["custom_cal_types_captured"], [])
        self.assertEqual(summary["supplemental_cal20_count"], 1)

    def test_summarize_preinit_skip_common_topology_is_partial_evidence(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2655-preinit-"))
        write_jsonl(
            root / "acdb-v2608-preinit-no-send-events.jsonl",
            [
                {"event": "v2608_preinit_no_send", "stage": "entered_common_topology_hook"},
                {"event": "v2608_preinit_no_send", "stage": "skip_real_common_topology"},
            ],
        )

        summary = v2655.summarize_setcal_capture(root)

        self.assertEqual(summary["classification"], "v2655-common-topology-hook-skipped-real-call-no-setcal")
        self.assertFalse(summary["success"])
        self.assertTrue(summary["partial_success"])
        self.assertTrue(summary["operator_valuable"])
        self.assertFalse(summary["counts_toward_fails_twice"])
        self.assertTrue(summary["skipped_common_topology"])

    def test_summarize_missing_one_custom_type_is_partial(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2655-missing-"))
        write_jsonl(
            root / "setcal-events.jsonl",
            [
                setcal_event(1, 10, 2048, 36, "dumped"),
                setcal_event(2, 24, 4096, 38, "dumped"),
            ],
        )

        summary = v2655.summarize_setcal_capture(root)

        self.assertEqual(summary["classification"], "v2655-custom-topology-setcal-partial")
        self.assertFalse(summary["success"])
        self.assertEqual(summary["custom_cal_types_captured"], [10, 24])
        self.assertEqual(summary["missing_custom_cal_types"], [14])

    def test_summarize_flags_real_set_pass_through(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2655-boundary-"))
        write_jsonl(root / "setcal-events.jsonl", custom_topology_rows(all_dumped=True))
        write_jsonl(
            root / "ioctl-trace-events.jsonl",
            [
                {
                    "event": "ioctl_trace",
                    "name": "AUDIO_SET_CALIBRATION",
                    "intercept": "passed-through",
                    "ret": 0,
                }
            ],
        )

        summary = v2655.summarize_setcal_capture(root)

        self.assertEqual(summary["classification"], "v2655-boundary-violation-real-audio-set-passthrough")
        self.assertFalse(summary["success"])
        self.assertEqual(summary["real_audio_set_pass_through_count"], 1)

    def test_summarize_no_pulled_artifacts_detects_preflash_bridge_timeout(self) -> None:
        run_dir = Path(tempfile.mkdtemp(prefix="a90-v2655-preflash-"))
        (run_dir / "flash-android.stderr.txt").write_text(
            "\n".join(
                [
                    "[native-init-flash] requesting recovery from native init bridge",
                    "[native-init-flash] phase.native_init_flash.native_to_recovery.elapsed_sec=180.046 ok=0",
                    "[native-init-flash] error: bridge command timeout for 'recovery': [Errno 111] Connection refused",
                ]
            ),
            encoding="utf-8",
        )

        summary = v2655.summarize_no_pulled_artifacts(
            {
                "out_dir": str(run_dir.relative_to(v2655.ROOT)) if run_dir.is_relative_to(v2655.ROOT) else str(run_dir),
                "error": "flash-android failed rc=1",
                "counts_toward_fails_twice": None,
            }
        )

        self.assertEqual(summary["classification"], "v2655-preflash-native-bridge-unavailable")
        self.assertEqual(summary["failure_phase"], "native_to_recovery_before_android_flash")
        self.assertFalse(summary["counts_toward_fails_twice"])
        self.assertFalse(summary["operator_valuable"])

    def test_dry_run_uses_v2490_engine_with_v2654_artifacts(self) -> None:
        payload = v2655.dry_run_payload(args())

        self.assertTrue(payload["ok"], payload.get("live_blockers"))
        self.assertTrue(payload["capture_contract"]["header_only_ok"])
        self.assertFalse(payload["capture_contract"]["fake_audio_cal_allocate"] is False)
        self.assertEqual(payload["capture_contract"]["target_cal_types"], [10, 14, 24])
        self.assertEqual(
            payload["capture_contract"]["set_intercept"],
            "AUDIO_SET_CALIBRATION always fake-successed; never reaches kernel SET",
        )
        self.assertTrue(payload["v2654_artifacts"]["ok"])
        self.assertTrue(payload["v2490_engine"]["live_ready"])


if __name__ == "__main__":
    unittest.main()
