"""Host-only tests for the V2474 native ACDB replay scaffold."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2474 = load_revalidation("native_audio_acdb_replay_scaffold_v2474")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2474-test-"))
    defaults: dict[str, object] = {
        "dry_run": True,
        "materialize_placeholder": False,
        "build_helper": False,
        "build_root": root / "build",
        "manifest_path": root / "build/manifest.json",
        "placeholder_path": root / "build/placeholder.bin",
        "cc": "aarch64-linux-gnu-gcc",
        "strip": "aarch64-linux-gnu-strip",
        "no_strip": True,
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class AcdbReplayScaffoldV2474(unittest.TestCase):
    def test_manifest_is_host_only_and_live_blocked(self) -> None:
        payload = v2474.manifest(args())

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["decision"], "v2474-acdb-replay-scaffold-host-only")
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["flash_action"], "none")
        self.assertTrue(payload["safety"]["native_calibration_ioctls_blocked_live"])
        self.assertFalse(payload["safety"]["execute_compiled_in_by_default"])
        self.assertTrue(payload["safety"]["source_guard_ok"])
        self.assertEqual(payload["replay_shape"]["cal_type"], 39)
        self.assertEqual(payload["replay_shape"]["expected_payload_len"], 4916)
        self.assertEqual(
            payload["replay_shape"]["sequence"],
            [
                "AUDIO_ALLOCATE_CALIBRATION",
                "AUDIO_SET_CALIBRATION",
                "AUDIO_DEALLOCATE_CALIBRATION",
            ],
        )

    def test_source_contains_execute_guard_and_required_replay_tokens(self) -> None:
        state = v2474.helper_source_state()

        self.assertTrue(state["exists"])
        self.assertTrue(state["execute_guard_default_disabled"])
        self.assertTrue(state["default_refuses_execute"])
        self.assertTrue(state["contains_live_ioctl_scaffold"])
        self.assertTrue(all(state["required_tokens"].values()), state["required_tokens"])

    def test_placeholder_payload_is_private_synthetic_and_exact_length(self) -> None:
        local_args = args(materialize_placeholder=True)

        payload = v2474.manifest(local_args)
        placeholder = payload["placeholder_payload"]

        self.assertEqual(placeholder["size"], 4916)
        self.assertEqual(placeholder["mode"], "0o600")
        self.assertTrue(placeholder["synthetic_placeholder"])
        self.assertFalse(placeholder["usable_for_live_replay"])
        self.assertEqual(len(placeholder["sha256"]), 64)
        data = local_args.placeholder_path.read_bytes()
        self.assertIn(b"NOT_REAL_ACDB_BYTES_DO_NOT_USE_FOR_LIVE_REPLAY", data)

    def test_cross_validation_inputs_are_private_and_not_committable(self) -> None:
        state = v2474.cross_validation_state()

        self.assertFalse(state["committable"])
        self.assertIn("workspace/private/inputs/audio/acdb_replay", state["root"])
        self.assertGreaterEqual(len(state["expected_private_inputs"]), 5)
        for entry in state["expected_private_inputs"]:
            self.assertTrue(entry["private_only"])

    @unittest.skipUnless(shutil.which("aarch64-linux-gnu-gcc"), "aarch64-linux-gnu-gcc unavailable")
    def test_build_helper_compiles_default_execute_disabled_binary(self) -> None:
        local_args = args(build_helper=True)

        payload = v2474.manifest(local_args)
        build = payload["build"]

        self.assertFalse(build["compile_defines"]["A90_ENABLE_NATIVE_CALIBRATION_EXECUTE"])
        self.assertTrue(build["build_record"]["ok"], build["build_record"])
        self.assertEqual(build["tool"]["name"], "a90_acdb_replay_scaffold_v2474")
        self.assertFalse(build["tool"]["execute_compiled_in"])
        self.assertIn("ARM aarch64", build["tool"]["file"])

    def test_cli_outputs_json_and_writes_manifest(self) -> None:
        local_args = args()
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_replay_scaffold_v2474.py")
        completed = subprocess.run(
            [
                sys.executable,
                str(script),
                "--dry-run",
                "--build-root",
                str(local_args.build_root),
                "--manifest-path",
                str(local_args.manifest_path),
                "--placeholder-path",
                str(local_args.placeholder_path),
                "--no-strip",
            ],
            cwd=v2474.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2474-acdb-replay-scaffold-host-only")
        self.assertTrue(local_args.manifest_path.exists())


if __name__ == "__main__":
    unittest.main()
