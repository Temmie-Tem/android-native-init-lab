"""Tests for the V2562 post-init armed ACDB live handoff wrapper."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2562_live = load_revalidation("native_audio_acdb_postinit_armed_capture_live_handoff_v2562")
v2562_build = load_revalidation("build_android_acdb_postinit_armed_capture_v2562")


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2562-live-test-"))
    defaults: dict[str, object] = {
        "dry_run": False,
        "run_live": False,
        "write_report": False,
        "report_path": root / "report.md",
        "build_v2562_artifacts": False,
        "v2562_build_root": root / "build",
        "v2562_manifest_path": root / "build/manifest.json",
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
        "android_root_recheck_attempts": 1,
        "android_root_recheck_sleep_sec": 0.0,
        "android_settle_adb_retry_attempts": 1,
        "android_settle_adb_retry_sleep_sec": 0.0,
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class NativeAudioAcdbPostinitArmedCaptureLiveHandoffV2562(unittest.TestCase):
    def test_to_v2490_args_forces_combined_preload_and_fake_allocate(self) -> None:
        local = args()
        artifacts = {
            "helper": {"path": "workspace/private/builds/audio/x/bin/helper", "sha256": "a" * 64},
            "preload": {"path": "workspace/private/builds/audio/x/bin/preload.so", "sha256": "b" * 64},
        }

        base = v2562_live.to_v2490_args(local, artifacts)

        self.assertTrue(base.use_combined_preload)
        self.assertFalse(base.enable_acdbtap_preload)
        self.assertFalse(base.disable_ioctl_trace)
        self.assertTrue(base.fake_audio_cal_allocate)
        self.assertEqual(base.helper_sha256, "a" * 64)
        self.assertEqual(base.combined_preload_sha256, "b" * 64)

    def test_summary_accepts_only_postinit_nonzero_4916_capture(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2562-summary-ok-"))
        acdbtap = root / "acdbtap"
        payload = b"A" * 4916
        raw = acdbtap / "acdbtap-00000002-cmd-00013296-len-00001334.bin"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(payload)
        write_jsonl(root / "acdb-ownget-events.jsonl", [
            {"event": "topology_helper", "stage": "init_v3_return", "code": 0},
            {"event": "topology_helper", "stage": "armed_before_common_topology", "code": 0},
        ])
        write_jsonl(acdbtap / "acdbtap-events.jsonl", [
            {"seq": "0x00000001", "cmd": "0x00013297", "in_len": "0x00000008", "out_len": "0x00000004", "ret": "0x00000000", "raw_path": "/data/local/tmp/a90-acdb-tap/size.bin", "sha256": hashlib.sha256(b"\x34\x13\x00\x00").hexdigest()},
            {"seq": "0x00000002", "cmd": "0x00013296", "in_len": "0x00000008", "out_len": "0x00001334", "ret": "0x00000000", "raw_path": "/data/local/tmp/a90-acdb-tap/" + raw.name, "sha256": hashlib.sha256(payload).hexdigest()},
        ])

        summary = v2562_live.summarize_postinit_capture(root)

        self.assertEqual(summary["classification"], "v2562-postinit-armed-topology-captured")
        self.assertTrue(summary["success"])
        self.assertTrue(summary["init_v3_ok"])
        self.assertTrue(summary["helper_armed_before_common_topology"])
        self.assertEqual(summary["topology_success_count"], 1)

    def test_summary_rejects_zero_4916_capture(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2562-summary-zero-"))
        acdbtap = root / "acdbtap"
        raw = acdbtap / "acdbtap-00000002-cmd-00013296-len-00001334.bin"
        raw.parent.mkdir(parents=True, exist_ok=True)
        raw.write_bytes(b"\0" * 4916)
        write_jsonl(root / "acdb-ownget-events.jsonl", [
            {"event": "topology_helper", "stage": "init_v3_return", "code": 0},
            {"event": "topology_helper", "stage": "armed_before_common_topology", "code": 0},
        ])
        write_jsonl(acdbtap / "acdbtap-events.jsonl", [
            {"seq": "0x00000002", "cmd": "0x00013296", "in_len": "0x00000008", "out_len": "0x00001334", "ret": "0x00000000", "raw_path": "/data/local/tmp/a90-acdb-tap/" + raw.name, "sha256": hashlib.sha256(b"\0" * 4916).hexdigest()},
        ])

        summary = v2562_live.summarize_postinit_capture(root)

        self.assertNotEqual(summary["classification"], "v2562-postinit-armed-topology-captured")
        self.assertFalse(summary["success"])

    def test_summary_identifies_topology_inside_init_before_manual_arm(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2562-summary-init-topology-"))
        (root / "ownget.rc").write_text("139\n", encoding="utf-8")
        (root / "ownget.stderr.txt").write_text("Segmentation fault\n", encoding="utf-8")
        (root / "logcat-acdb-loader.txt").write_text(
            "ACDB -> send_common_custom_topology\n"
            "ACDB -> ACDB_CMD_GET_AVCS_CUSTOM_TOPO_INFO_SIZE_V3\n"
            "ACDB -> ACDB_CMD_GET_AVCS_CUSTOM_TOPO_INFO_V3\n",
            encoding="utf-8",
        )

        summary = v2562_live.summarize_postinit_capture(root)

        self.assertEqual(summary["classification"], "v2562-init-internal-topology-before-manual-arm-sigsegv")
        self.assertTrue(summary["acdb_log_has_common_topology"])
        self.assertTrue(summary["acdb_log_has_topology_get"])
        self.assertTrue(summary["helper_sigsegv"])

    def test_summary_flags_real_set_passthrough(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2562-summary-set-"))
        write_jsonl(root / "ioctl-trace-events.jsonl", [
            {"event": "ioctl_trace", "name": "AUDIO_SET_CALIBRATION", "intercept": "pass-through"},
        ])

        summary = v2562_live.summarize_postinit_capture(root)

        self.assertEqual(summary["classification"], "v2562-boundary-violation-real-audio-set-passthrough")
        self.assertFalse(summary["success"])

    def test_dry_run_reports_not_ready_without_artifacts(self) -> None:
        payload = v2562_live.dry_run_payload(args())

        self.assertFalse(payload["ok"])
        self.assertIn("V2562 post-init armed helper/preload artifacts are not ready", payload["live_blockers"])

    def test_builder_manifest_can_be_selected_when_artifacts_exist(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2562-select-test-"))
        helper = root / "helper"
        preload = root / "preload.so"
        helper.write_bytes(b"helper")
        preload.write_bytes(b"preload")
        helper.chmod(0o600)
        preload.chmod(0o600)
        manifest = {
            "ok": True,
            "build": {
                "helper": {"ok": True, "path": v2562_build.rel(helper), "sha256": hashlib.sha256(b"helper").hexdigest()},
                "preload": {"ok": True, "path": v2562_build.rel(preload), "sha256": hashlib.sha256(b"preload").hexdigest()},
            },
            "source_state": {"required": {"helper_arms_after_init": True}},
            "toolchain": {"preload_cflags": ["-DA90_ACDBTAP_AUTO_ARM_ON_INITIALIZE=0"]},
        }
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        selected = v2562_live.selected_artifacts(args(v2562_manifest_path=manifest_path))

        self.assertTrue(selected["ok"], selected)
        self.assertTrue(selected["manifest"]["manual_arm_only"])


if __name__ == "__main__":
    unittest.main()
