"""Host-only tests for the V2490 own-process ACDB GET live runner."""

from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2490 = load_revalidation("native_audio_acdb_ownprocess_get_live_handoff_v2490")
v2489 = load_revalidation("build_android_acdb_ownprocess_get_v2489")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2490-test-"))
    defaults: dict[str, object] = {
        "dry_run": True,
        "run_live": False,
        "build_helper": False,
        "out_dir": root / "run",
        "adb": "adb",
        "serial": None,
        "from_native": False,
        "android_timeout": 240.0,
        "flash_timeout": 420.0,
        "adb_command_timeout": 90.0,
        "adb_pull_timeout": 120.0,
        "helper_timeout": 60.0,
        "android_root_recheck_attempts": 4,
        "android_root_recheck_sleep_sec": 2.0,
        "helper_path": None,
        "helper_sha256": None,
        "helper_build_root": v2489.DEFAULT_BUILD_ROOT,
        "helper_manifest_path": v2489.DEFAULT_MANIFEST,
        "readelf": "readelf",
        "file": "file",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class NativeAudioAcdbOwnprocessGetV2490(unittest.TestCase):
    def test_dry_run_is_ownprocess_only_and_live_ready_when_artifact_exists(self) -> None:
        payload = v2490.dry_run_payload(args())

        self.assertEqual(payload["decision"], "v2490-acdb-ownprocess-get-live-runner-dry-run")
        self.assertTrue(payload["live_ready"], payload.get("live_blockers"))
        self.assertTrue(payload["command_safety"]["ok"], payload["command_safety"])
        self.assertTrue(payload["helper"]["ok"], payload["helper"])
        self.assertIn("own-process helper only", "\n".join(payload["hard_boundary"]))
        flat_commands = json.dumps(payload["commands"], sort_keys=True)
        self.assertNotIn("magisk --install-module", flat_commands)
        self.assertNotIn("android.hardware.audio.service", flat_commands)
        self.assertNotIn("AudioTrack", flat_commands)
        self.assertNotIn("/dev/msm_audio_cal", flat_commands)
        self.assertNotIn("0xc00461cb", flat_commands.lower())

    def test_command_safety_rejects_inhal_and_native_calibration_paths(self) -> None:
        payload = {
            "commands": {
                "bad": [
                    "adb",
                    "shell",
                    "su",
                    "-c",
                    "magisk --install-module x; restart android.hardware.audio.service; echo /dev/msm_audio_cal 0xc00461cb; tinyplay x",
                ]
            }
        }
        safety = v2490.command_safety(payload)

        self.assertFalse(safety["ok"])
        names = {item["name"] for item in safety["findings"]}
        self.assertIn("magisk_install", names)
        self.assertIn("hal_restart", names)
        self.assertIn("native_msm_audio_cal", names)
        self.assertIn("native_cal_set_constant", names)
        self.assertIn("tinyplay", names)

    def test_parse_ownget_artifacts_classifies_4916_success(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        event = root / "acdb-ownget-events.jsonl"
        raw = root / "acdb-ownget-00000001-000130da-in0-out4916.bin"
        raw.write_bytes(b"x" * 4916)
        event.write_text(json.dumps({
            "event": "acdb_ioctl",
            "seq": 1,
            "cmd": "0x000130da",
            "in_len": 0,
            "out_len": 4916,
            "ret": 0,
            "is_target_4916": True,
            "sha256": "0" * 64,
            "raw_path": f"/data/local/tmp/a90-acdb-ownget/{raw.name}",
        }) + "\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "acdb-get-success-4916")
        self.assertTrue(summary["full_success"])
        self.assertTrue(summary["operator_valuable"])
        self.assertFalse(summary["counts_toward_fails_twice"])

    def test_parse_ownget_artifacts_preserves_no_4916_partial(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        event = root / "acdb-ownget-events.jsonl"
        raw = root / "acdb-ownget-00000001-00011394-in0-out4.bin"
        raw.write_bytes(b"\x34\x13\x00\x00")
        event.write_text(json.dumps({
            "event": "acdb_ioctl",
            "seq": 1,
            "cmd": "0x00011394",
            "in_len": 0,
            "out_len": 4,
            "ret": 0,
            "is_target_4916": False,
            "sha256": "1" * 64,
            "raw_path": f"/data/local/tmp/a90-acdb-ownget/{raw.name}",
        }) + "\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "acdb-get-full-outbuf-set-no-4916")
        self.assertTrue(summary["partial_success"])
        self.assertTrue(summary["operator_valuable"])
        self.assertFalse(summary["counts_toward_fails_twice"])

    def test_parse_ownget_artifacts_maps_namespace_api_error_bucket(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "acdb-ownget-events.jsonl").write_text(json.dumps({
            "event": "symbol_probe",
            "scope": "libdl",
            "symbol": "__loader_android_dlopen_ext",
            "found": False,
        }) + "\n" + json.dumps({
            "event": "error",
            "stage": "dlsym-android_dlopen_ext",
            "code": -3,
        }) + "\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "namespace-api-symbol-missing")
        self.assertEqual(summary["symbol_event_count"], 1)
        self.assertEqual(summary["symbol_events"][0]["symbol"], "__loader_android_dlopen_ext")
        self.assertTrue(summary["operator_valuable"])
        self.assertTrue(summary["counts_toward_fails_twice"])

    def test_parse_ownget_artifacts_classifies_dlopen_error(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-artifacts-"))
        (root / "acdb-ownget-events.jsonl").write_text(json.dumps({
            "event": "error",
            "stage": "dlopen-libaudcal",
            "code": -1,
        }) + "\n")

        summary = v2490.parse_ownget_artifacts(root)

        self.assertEqual(summary["classification"], "ownprocess-error-dlopen-libaudcal")
        self.assertTrue(summary["operator_valuable"])
        self.assertTrue(summary["counts_toward_fails_twice"])

    def test_select_pulled_artifact_dir_accepts_flat_adb_pull_layout(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-pull-"))
        (root / "acdb-ownget-events.jsonl").write_text("{}\n")

        self.assertEqual(v2490.select_pulled_artifact_dir(root), root)

    def test_select_pulled_artifact_dir_accepts_nested_adb_pull_layout(self) -> None:
        root = Path(tempfile.mkdtemp(prefix="a90-v2490-pull-"))
        nested = root / "a90-acdb-ownget"
        nested.mkdir()
        (nested / "acdb-ownget-events.jsonl").write_text("{}\n")

        self.assertEqual(v2490.select_pulled_artifact_dir(root), nested)

    def test_cli_dry_run_outputs_json(self) -> None:
        import subprocess
        import sys

        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/native_audio_acdb_ownprocess_get_live_handoff_v2490.py",
                "--dry-run",
            ],
            cwd=v2490.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2490-acdb-ownprocess-get-live-runner-dry-run")
        self.assertTrue(payload["command_safety"]["ok"])


if __name__ == "__main__":
    unittest.main()
