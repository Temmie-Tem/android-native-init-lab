"""Tests for the V2581 ACDB store-get probe live runner."""

from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2581 = load_revalidation("native_audio_acdb_store_get_probe_live_handoff_v2581")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2581-test-"))
    defaults: dict[str, object] = {
        "dry_run": False,
        "run_live": False,
        "write_report": False,
        "report_path": root / "report.md",
        "exact_gate": None,
        "create_marker": False,
        "build_v2580_helper": False,
        "build_ioctl_trace": False,
        "v2580_build_root": root / "build-v2580",
        "v2580_manifest_path": root / "build-v2580/manifest.json",
        "helper_path": None,
        "helper_sha256": None,
        "ioctl_trace_build_root": root / "build-preload",
        "ioctl_trace_manifest_path": root / "build-preload/manifest.json",
        "ioctl_trace_so": None,
        "ioctl_trace_sha256": None,
        "out_dir": root / "run",
        "adb": "adb",
        "serial": None,
        "from_native": True,
        "android_timeout": 240.0,
        "flash_timeout": 420.0,
        "adb_command_timeout": 90.0,
        "adb_pull_timeout": 120.0,
        "helper_timeout": 90.0,
        "android_root_recheck_attempts": 1,
        "android_root_recheck_sleep_sec": 0.0,
        "android_settle_adb_retry_attempts": 1,
        "android_settle_adb_retry_sleep_sec": 0.0,
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class NativeAudioAcdbStoreGetProbeLiveHandoffV2581(unittest.TestCase):
    def test_to_v2490_args_forces_ioctl_only_preload_and_fake_allocate(self) -> None:
        local = args()
        artifacts = {
            "helper": {"path": "workspace/private/builds/audio/x/bin/helper", "sha256": "a" * 64},
            "ioctl_trace_preload": {"path": "workspace/private/builds/audio/x/bin/preload.so", "sha256": "b" * 64},
        }

        base = v2581.to_v2490_args(local, artifacts)

        self.assertFalse(base.use_combined_preload)
        self.assertFalse(base.enable_acdbtap_preload)
        self.assertFalse(base.disable_ioctl_trace)
        self.assertTrue(base.fake_audio_cal_allocate)
        self.assertEqual(base.helper_sha256, "a" * 64)
        self.assertEqual(base.ioctl_trace_sha256, "b" * 64)

    def test_live_requires_exact_gate_and_marker(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "exact gate"):
            v2581.require_live_gate(args(create_marker=True, exact_gate="wrong"))
        with self.assertRaisesRegex(RuntimeError, "create-marker"):
            v2581.require_live_gate(args(exact_gate=v2581.EXACT_GATE, create_marker=False))
        v2581.require_live_gate(args(exact_gate=v2581.EXACT_GATE, create_marker=True))

    def test_marker_command_creates_and_removes_gate(self) -> None:
        local = args(create_marker=True)

        command = v2581.marker_helper_command(local)
        flat = " ".join(command)

        self.assertIn("V2580_STORE_GET_GO", flat)
        self.assertIn("touch /data/local/tmp/a90-acdb-ownget/V2580_STORE_GET_GO", flat)
        self.assertIn("rm -f /data/local/tmp/a90-acdb-ownget/V2580_STORE_GET_GO", flat)
        self.assertIn("A90_ACDB_FAKE_ALLOCATE=1", flat)
        self.assertIn("LD_PRELOAD=/data/local/tmp/a90-acdb-ownget/liba90_ioctl_trace_v2531.so", flat)

    def test_summary_accepts_nonzero_case_return_metadata(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2581-summary-ok-"))
        write_jsonl(root / "acdb-storeget-v2580-events.jsonl", [
            {"event": "v2580_store_get", "stage": "start", "code": 0},
            {"event": "v2580_store_get", "stage": "before_init_v3", "code": 0},
            {"event": "v2580_store_get", "stage": "init_v3_return", "code": 0},
            {"event": "v2580_store_get", "stage": "case_return", "case": "store_selector_37", "selector": 37, "instance": 0, "ret": 0, "out_len": 128, "all_zero": False, "fnv1a32": "0x12345678"},
        ])

        summary = v2581.summarize_store_get_probe(root)

        self.assertEqual(summary["classification"], "v2581-store-get-nonzero-metadata-captured")
        self.assertTrue(summary["success"])
        self.assertEqual(summary["store_get"]["success_count"], 1)

    def test_summary_rejects_zero_success_metadata(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2581-summary-zero-"))
        write_jsonl(root / "acdb-storeget-v2580-events.jsonl", [
            {"event": "v2580_store_get", "stage": "init_v3_return", "code": 0},
            {"event": "v2580_store_get", "stage": "case_return", "case": "store_selector_37", "selector": 37, "instance": 0, "ret": 0, "out_len": 4916, "all_zero": True, "fnv1a32": "0x00000000"},
        ])

        summary = v2581.summarize_store_get_probe(root)

        self.assertEqual(summary["classification"], "v2581-store-get-case-returns-no-nonzero")
        self.assertFalse(summary["success"])
        self.assertEqual(summary["store_get"]["success_count"], 0)

    def test_summary_reports_gate_absent(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2581-summary-gate-"))
        write_jsonl(root / "acdb-storeget-v2580-events.jsonl", [
            {"event": "v2580_store_get", "stage": "start", "code": 0},
            {"event": "v2580_store_get", "stage": "gate_absent_no_live", "code": 0},
        ])

        summary = v2581.summarize_store_get_probe(root)

        self.assertEqual(summary["classification"], "v2581-store-get-gate-absent")
        self.assertFalse(summary["success"])


if __name__ == "__main__":
    unittest.main()
