"""Tests for the V2673 lower-hidden-node ACDB SET capture live wrapper."""

from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2673 = load_revalidation("native_audio_acdb_lower_hidden_node_setcal_capture_live_handoff_v2673")


def args(**overrides: object) -> argparse.Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2673-test-"))
    defaults: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "write_report": False,
        "report_path": root / "report.md",
        "build_v2672_artifacts": False,
        "v2672_build_root": v2673.v2672.DEFAULT_BUILD_ROOT,
        "v2672_manifest_path": v2673.v2672.DEFAULT_MANIFEST,
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
        "android_root_recheck_attempts": v2673.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_ATTEMPTS,
        "android_root_recheck_sleep_sec": v2673.v2490.v2396.DEFAULT_ANDROID_ROOT_RECHECK_SLEEP_SEC,
        "android_settle_adb_retry_attempts": v2673.v2490.DEFAULT_SETTLE_ADB_RETRY_ATTEMPTS,
        "android_settle_adb_retry_sleep_sec": v2673.v2490.DEFAULT_SETTLE_ADB_RETRY_SLEEP_SEC,
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def lower_event(stage: str, code: int = 0, cal_type: int = 0, value: int = 0) -> dict[str, object]:
    return {
        "event": "v2672_lower_hidden",
        "stage": stage,
        "code": code,
        "cal_type": cal_type,
        "value": value,
    }


def helper_event(stage: str, code: int = 0) -> dict[str, object]:
    return {"event": "v2672_lower_hidden_helper", "stage": stage, "code": code}


def setcal_event(seq: int, cal_type: int, cal_size: int, mem_handle: int, dmabuf_status: str) -> dict[str, object]:
    return {
        "event": "setcal_capture",
        "pid": 4198,
        "tid": 4198,
        "sequence": seq,
        "fd": -1,
        "request": "0xc00461cb",
        "header_valid": True,
        "data_size": 32,
        "version": 0,
        "cal_type": cal_type,
        "cal_type_size": 16,
        "cal_hdr_version": 0,
        "buffer_number": 0,
        "cal_size": cal_size,
        "mem_handle": mem_handle,
        "set_arg": {
            "path": f"/data/local/tmp/a90-acdb-ownget/setcal-arg-{seq:04d}.bin",
            "len": 32,
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


def target_rows(all_dumped: bool = True) -> list[dict[str, object]]:
    last_status = "dumped" if all_dumped else "mmap-failed"
    return [
        setcal_event(1, 24, 4096, 38, "dumped"),
        setcal_event(2, 10, 2048, 36, "dumped"),
        setcal_event(3, 14, 1024, 37, last_status),
    ]


class NativeAudioAcdbLowerHiddenNodeSetcalCaptureLiveHandoffV2673(unittest.TestCase):
    def test_read_v2672_manifest_checks_setcal_contract(self) -> None:
        manifest = v2673.read_v2672_manifest(v2673.v2672.DEFAULT_MANIFEST)

        self.assertTrue(manifest["ok"], manifest)
        self.assertTrue(manifest["setcal_contract_ok"], manifest)


    def test_v2672_event_reader_accepts_unquoted_hex_values(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2673-hex-jsonl-"))
        path = root / "acdb-v2672-lower-hidden-events.jsonl"
        path.write_text(
            '{"event":"v2672_lower_hidden","stage":"loader_base_resolved",'
            '"code":0,"cal_type":0,"value":0xf3b04000}\n',
            encoding="utf-8",
        )

        rows = v2673.read_v2672_jsonl(path)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["value"], 0xF3B04000)

    def test_summarize_lower_hidden_success(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2673-full-"))
        write_jsonl(
            root / "acdb-v2672-lower-hidden-helper-events.jsonl",
            [helper_event("init_v3_return"), helper_event("armed_before_lower_hidden_nodes"), helper_event("lower_hidden_nodes_return")],
        )
        write_jsonl(
            root / "acdb-v2672-lower-hidden-events.jsonl",
            [
                lower_event("loader_base_resolved"),
                lower_event("create_cal_node_return", cal_type=24),
                lower_event("allocate_cal_block_return", cal_type=24),
                lower_event("acdb_ioctl_get_return", cal_type=24, value=4096),
                lower_event("fake_set_ioctl_return", cal_type=24, value=38),
                lower_event("lower_hidden_sequence_complete"),
            ],
        )
        write_jsonl(root / "setcal-events.jsonl", target_rows(all_dumped=True))

        summary = v2673.summarize_setcal_capture(root)

        self.assertEqual(summary["classification"], "v2673-lower-hidden-custom-setcal-captured")
        self.assertTrue(summary["success"])
        self.assertTrue(summary["operator_valuable"])
        self.assertEqual(summary["custom_cal_types_captured"], [10, 14, 24])
        self.assertEqual(summary["missing_custom_cal_types"], [])
        self.assertTrue(summary["custom_payloads_dumped"])
        self.assertEqual(summary["fake_set_codes"], [0])

    def test_summarize_partial_when_target_dmabuf_fails(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2673-partial-"))
        write_jsonl(root / "setcal-events.jsonl", target_rows(all_dumped=False))

        summary = v2673.summarize_setcal_capture(root)

        self.assertEqual(summary["classification"], "v2673-lower-hidden-custom-setcal-partial")
        self.assertFalse(summary["success"])
        self.assertTrue(summary["partial_success"])
        self.assertFalse(summary["custom_payloads_dumped"])
        self.assertEqual(summary["custom_payload_failed_count"], 1)

    def test_summarize_lower_sequence_without_setcal_is_frontier_signal(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2673-seq-no-set-"))
        write_jsonl(root / "acdb-v2672-lower-hidden-helper-events.jsonl", [helper_event("armed_before_lower_hidden_nodes")])
        write_jsonl(
            root / "acdb-v2672-lower-hidden-events.jsonl",
            [
                lower_event("loader_base_resolved"),
                lower_event("acdb_ioctl_get_return", cal_type=10, value=2048),
                lower_event("lower_hidden_sequence_complete", code=-22),
            ],
        )

        summary = v2673.summarize_setcal_capture(root)

        self.assertEqual(summary["classification"], "v2673-lower-hidden-sequence-complete-no-setcal")
        self.assertFalse(summary["success"])
        self.assertTrue(summary["partial_success"])
        self.assertTrue(summary["operator_valuable"])
        self.assertFalse(summary["counts_toward_fails_twice"])
        self.assertEqual(summary["acdb_get_codes"], [0])
        self.assertEqual(summary["sequence_codes"], [-22])

    def test_summarize_helper_started_without_lower_events(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2673-helper-only-"))
        write_jsonl(root / "acdb-v2672-lower-hidden-helper-events.jsonl", [helper_event("armed_before_lower_hidden_nodes")])

        summary = v2673.summarize_setcal_capture(root)

        self.assertEqual(summary["classification"], "v2673-helper-started-lower-runner-no-lower-events")
        self.assertTrue(summary["operator_valuable"])
        self.assertFalse(summary["counts_toward_fails_twice"])

    def test_summarize_flags_real_set_pass_through(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2673-boundary-"))
        write_jsonl(root / "setcal-events.jsonl", target_rows(all_dumped=True))
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

        summary = v2673.summarize_setcal_capture(root)

        self.assertEqual(summary["classification"], "v2673-boundary-violation-real-audio-set-passthrough")
        self.assertFalse(summary["success"])

    def test_dry_run_ready_uses_v2672_artifacts(self) -> None:
        payload = v2673.dry_run_payload(args())

        self.assertTrue(payload["ok"], payload.get("live_blockers"))
        self.assertTrue(payload["live_ready"])
        self.assertIn("lower-hidden-node", payload["decision"])
        self.assertEqual(payload["capture_contract"]["target_cal_types"], [10, 14, 24])
        self.assertTrue(payload["v2672_artifacts"]["manifest"]["setcal_contract_ok"])


if __name__ == "__main__":
    unittest.main()
