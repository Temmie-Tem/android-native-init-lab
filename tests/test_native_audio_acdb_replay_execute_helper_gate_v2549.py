"""Host-only tests for the V2549 ACDB replay execute-helper gate."""

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

v2549 = load_revalidation("native_audio_acdb_replay_execute_helper_gate_v2549")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2549-test-"))
    payload_path = root / "payload.bin"
    payload_path.write_bytes(bytes([0x41]) * v2549.EXPECTED_PAYLOAD_LEN)
    defaults: dict[str, object] = {
        "dry_run": True,
        "build_helper": False,
        "require_payload": False,
        "payload": payload_path,
        "hold_sec": 10,
        "build_root": root / "build",
        "manifest_path": root / "build/manifest.json",
        "cc": "aarch64-linux-gnu-gcc",
        "strip": "aarch64-linux-gnu-strip",
        "no_strip": True,
    }
    defaults.update(overrides)
    return Namespace(**defaults)


class AcdbReplayExecuteHelperGateV2549(unittest.TestCase):
    def test_payload_state_accepts_expected_private_payload_when_present(self) -> None:
        state = v2549.payload_state(v2549.STABLE_PAYLOAD)

        self.assertTrue(state["exists"])
        self.assertTrue(state["ready"], state)
        self.assertEqual(state["size"], 4916)
        self.assertEqual(state["sha256"], v2549.EXPECTED_PAYLOAD_SHA256)
        self.assertFalse(state["all_zero"])
        self.assertFalse(state["committable"])

    def test_payload_state_rejects_zero_or_wrong_hash_payload(self) -> None:
        local_args = args()
        local_args.payload.write_bytes(b"\x00" * v2549.EXPECTED_PAYLOAD_LEN)
        state = v2549.payload_state(local_args.payload)

        self.assertFalse(state["ready"])
        self.assertTrue(state["all_zero"])

    def test_source_contains_required_execute_tokens(self) -> None:
        state = v2549.helper_source_state()

        self.assertTrue(state["exists"])
        self.assertTrue(state["ready"], state["required_tokens"])
        self.assertTrue(all(state["required_tokens"].values()))

    def test_manifest_is_host_only_and_future_live_gated(self) -> None:
        payload = v2549.manifest(args(payload=v2549.STABLE_PAYLOAD, require_payload=True))

        self.assertTrue(payload["ok"])
        self.assertEqual(payload["decision"], "v2549-acdb-replay-execute-helper-gate-host-only")
        self.assertEqual(payload["device_action"], "none")
        self.assertFalse(payload["native_calibration_ioctls_run"])
        self.assertTrue(payload["safety"]["future_live_requires_exact_gate"])
        self.assertEqual(payload["replay_contract"]["cal_type"], 39)
        self.assertEqual(payload["replay_contract"]["payload_len"], 4916)
        self.assertIn("AUDIO_SET_CALIBRATION", " ".join(payload["replay_contract"]["sequence"]))
        self.assertIn("AUDIO_SET_CALIBRATION ok", " ".join(payload["future_live_plan"]["steps"]))

    @unittest.skipUnless(shutil.which("aarch64-linux-gnu-gcc"), "aarch64-linux-gnu-gcc unavailable")
    def test_build_helper_compiles_execute_enabled_binary(self) -> None:
        local_args = args(payload=v2549.STABLE_PAYLOAD, require_payload=True, build_helper=True)

        payload = v2549.manifest(local_args)
        build = payload["build"]

        self.assertTrue(build["built"])
        self.assertTrue(build["compile_defines"]["A90_ENABLE_NATIVE_CALIBRATION_EXECUTE"])
        self.assertTrue(build["tool"]["execute_compiled_in"])
        self.assertIn("ARM aarch64", build["tool"]["file"])
        self.assertTrue(build["static_probe"]["strings_has_execute_format"])
        self.assertTrue(build["static_probe"]["strings_has_execute_ioctl_marker"])
        self.assertFalse(build["static_probe"]["strings_has_blocked_default_message"])

    def test_cli_outputs_json_and_writes_manifest(self) -> None:
        local_args = args(payload=v2549.STABLE_PAYLOAD)
        script = Path("workspace/public/src/scripts/revalidation/native_audio_acdb_replay_execute_helper_gate_v2549.py")
        completed = subprocess.run(
            [
                sys.executable,
                str(script),
                "--dry-run",
                "--require-payload",
                "--payload",
                str(local_args.payload),
                "--build-root",
                str(local_args.build_root),
                "--manifest-path",
                str(local_args.manifest_path),
                "--no-strip",
            ],
            cwd=v2549.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["decision"], "v2549-acdb-replay-execute-helper-gate-host-only")
        self.assertTrue(local_args.manifest_path.exists())


if __name__ == "__main__":
    unittest.main()
