"""Host-only tests for the V2429 ACDB M1 temporary Magisk module planner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _loader import load_revalidation

v2429 = load_revalidation("native_audio_acdb_m1_magisk_module_planner_v2429")


def args(**overrides: object) -> argparse.Namespace:
    values: dict[str, object] = {
        "dry_run": True,
        "materialize_module_template": False,
        "module_out_dir": v2429.DEFAULT_MODULE_OUT_DIR,
        "cc": v2429.DEFAULT_CC,
        "stimulus_apk": v2429.v2396.DEFAULT_STIMULUS_APK,
        "capture_duration_sec": v2429.DEFAULT_CAPTURE_DURATION_SEC,
        "max_bytes": v2429.DEFAULT_MAX_BYTES,
        "process_poll_sec": v2429.DEFAULT_PROCESS_POLL_SEC,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


class AcdbM1MagiskModulePlannerV2429(unittest.TestCase):
    def test_dry_run_defines_m1_boundary_without_device_action(self) -> None:
        payload = v2429.dry_run_payload(args())

        self.assertEqual(payload["run_id"], "V2429")
        self.assertEqual(payload["decision"], "v2429-acdb-m1-magisk-module-planner-dry-run")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertFalse(payload["module"]["native_runtime_dependency"])
        self.assertFalse(payload["module"]["persistent_module_baseline"])
        self.assertTrue(payload["module"]["uses_service_sh"])
        self.assertFalse(payload["module"]["uses_post_fs_data"])
        self.assertIn("V2428", payload["m1_reason"])
        self.assertIn("temporary Magisk service module", payload["approval_phrase_required_for_future_live"])
        self.assertTrue(payload["command_safety"]["ok"])
        self.assertIn("M1 module template not materialized", " ".join(payload["future_live_blockers"]))

    def test_module_template_uses_service_sh_and_existing_observer_cli(self) -> None:
        files = v2429.module_files(
            v2429.DEFAULT_CAPTURE_DURATION_SEC,
            v2429.DEFAULT_MAX_BYTES,
            v2429.DEFAULT_PROCESS_POLL_SEC,
            include_helper=True,
        )
        service = files["service.sh"].decode()
        flat = "\n".join(value.decode(errors="replace") for value in files.values())

        self.assertIn("MODDIR=\"${0%/*}\"", service)
        self.assertIn("--tgid \"$pid\"", service)
        self.assertIn("--fd-pid \"$pid\"", service)
        self.assertIn("--device-substr /dev/msm_audio_cal", service)
        self.assertIn("HELPER_MAX_DURATION_SEC=\"120\"", service)
        self.assertIn("helper_duration=\"$remaining\"", service)
        self.assertIn("helper_duration=\"$HELPER_MAX_DURATION_SEC\"", service)
        self.assertIn("helper_duration=$helper_duration", service)
        self.assertIn("--duration-sec \"$helper_duration\"", service)
        self.assertNotIn("--duration-sec \"$remaining\"", service)
        self.assertIn("threadset-clone-following", service)
        self.assertIn(f"bin/{v2429.HELPER_NAME}", files)
        self.assertNotIn("post-fs-data.sh", flat)
        self.assertNotIn("magisk --install-module", flat)
        self.assertNotIn("AUDIO_SET_CALIBRATION", flat)
        self.assertNotIn("tinyplay", flat)

    def test_materialize_module_template_builds_private_zip_and_helper(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = v2429.dry_run_payload(args(
                materialize_module_template=True,
                module_out_dir=Path(temp_dir),
            ))
            module = payload["module"]

            self.assertTrue(module["ok"])
            self.assertTrue(module["helper"]["ok"])
            self.assertTrue(module["helper"]["module_binary"]["ok"])
            self.assertTrue(module["zip"]["ok"])
            self.assertEqual(module["zip"]["mode"], "0o600")
            self.assertTrue((Path(temp_dir) / "service.sh").exists())
            self.assertTrue((Path(temp_dir) / "bin" / v2429.HELPER_NAME).exists())
            self.assertTrue((Path(temp_dir) / f"{v2429.MODULE_ID}.zip").exists())
            self.assertEqual(payload["future_live_blockers"], [])

    def test_cli_dry_run_outputs_json(self) -> None:
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_m1_magisk_module_planner_v2429.py")
        completed = subprocess.run(
            [sys.executable, str(script), "--dry-run"],
            cwd=v2429.ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        payload = json.loads(completed.stdout)
        self.assertEqual(payload["run_id"], "V2429")
        self.assertTrue(payload["command_safety"]["ok"])


if __name__ == "__main__":
    unittest.main()
