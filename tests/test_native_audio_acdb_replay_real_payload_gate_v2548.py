"""Host-only tests for V2548 ACDB real payload replay gate."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path

from _loader import load_revalidation

v2548 = load_revalidation("native_audio_acdb_replay_real_payload_gate_v2548")


def args(**overrides: object) -> Namespace:
    root = Path(tempfile.mkdtemp(prefix="a90-v2548-test-"))
    source = root / "source.bin"
    stable = root / "stable.bin"
    defaults: dict[str, object] = {
        "dry_run": True,
        "stage_payload": False,
        "require_stable_payload": False,
        "source_payload_path": source,
        "stable_payload_path": stable,
        "expected_payload_sha256": "",
        "manifest_path": root / "manifest.json",
    }
    defaults.update(overrides)
    return Namespace(**defaults)


def write_payload(path: Path, *, zero: bool = False) -> str:
    if zero:
        data = b"\x00" * v2548.EXPECTED_PAYLOAD_LEN
    else:
        data = (b"A90_REAL_PAYLOAD_TEST" * ((v2548.EXPECTED_PAYLOAD_LEN // 21) + 1))[: v2548.EXPECTED_PAYLOAD_LEN]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


class AcdbReplayRealPayloadGateV2548(unittest.TestCase):
    def test_payload_state_accepts_exact_nonzero_payload(self) -> None:
        local = args()
        digest = write_payload(local.source_payload_path)

        state = v2548.payload_state(local.source_payload_path, expected_sha256=digest)

        self.assertTrue(state["ok"], state)
        self.assertEqual(state["size"], v2548.EXPECTED_PAYLOAD_LEN)
        self.assertEqual(state["sha256"], digest)
        self.assertFalse(state["all_zero"])
        self.assertTrue(state["checks"]["zero_hash_rejected"])

    def test_payload_state_rejects_zero_or_wrong_hash(self) -> None:
        local = args()
        zero_digest = write_payload(local.source_payload_path, zero=True)

        zero_state = v2548.payload_state(local.source_payload_path, expected_sha256=zero_digest)
        wrong_hash_state = v2548.payload_state(local.source_payload_path, expected_sha256="f" * 64)

        self.assertFalse(zero_state["ok"], zero_state)
        self.assertFalse(zero_state["checks"]["nonzero_ok"])
        self.assertFalse(zero_state["checks"]["zero_hash_rejected"])
        self.assertFalse(wrong_hash_state["ok"], wrong_hash_state)
        self.assertFalse(wrong_hash_state["checks"]["sha256_ok"])

    def test_stage_payload_copies_to_private_mode_0600(self) -> None:
        local = args()
        digest = write_payload(local.source_payload_path)

        result = v2548.stage_payload(local.source_payload_path, local.stable_payload_path, expected_sha256=digest)

        self.assertTrue(result["ok"], result)
        self.assertTrue(local.stable_payload_path.exists())
        self.assertEqual(result["target"]["mode"], "0o600")
        self.assertEqual(result["target"]["sha256"], digest)

    def test_manifest_is_host_only_and_keeps_live_set_blocked(self) -> None:
        local = args(require_stable_payload=False)
        digest = write_payload(local.source_payload_path)
        local.expected_payload_sha256 = digest

        payload = v2548.manifest(local)

        self.assertEqual(payload["decision"], "v2548-acdb-real-payload-gate-host-only")
        self.assertTrue(payload["host_only"])
        self.assertEqual(payload["device_action"], "none")
        self.assertEqual(payload["native_calibration_ioctls"], "none")
        self.assertTrue(payload["capture_payload_source"]["ok"])
        self.assertFalse(payload["replay_policy"]["native_set_live_ran"])
        self.assertFalse(payload["replay_policy"]["safe_to_run_live_set_from_this_unit"])
        self.assertTrue(payload["replay_policy"]["mem_handle_policy"]["android_mem_handle_37_is_not_reused"])

    def test_cli_stage_payload_outputs_ready_manifest(self) -> None:
        local = args(require_stable_payload=True)
        digest = write_payload(local.source_payload_path)
        completed = subprocess.run(
            [
                sys.executable,
                "workspace/public/src/scripts/revalidation/native_audio_acdb_replay_real_payload_gate_v2548.py",
                "--stage-payload",
                "--require-stable-payload",
                "--source-payload-path",
                str(local.source_payload_path),
                "--stable-payload-path",
                str(local.stable_payload_path),
                "--expected-payload-sha256",
                digest,
                "--manifest-path",
                str(local.manifest_path),
            ],
            cwd=v2548.ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(payload["ok"], payload)
        self.assertTrue(payload["stable_replay_payload"]["ok"])
        self.assertTrue(local.manifest_path.exists())


if __name__ == "__main__":
    unittest.main()
