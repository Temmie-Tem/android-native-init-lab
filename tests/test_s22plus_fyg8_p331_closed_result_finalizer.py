from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p331_closed_result_finalizer as finalizer  # noqa: E402
import device_action_f1_v2 as core  # noqa: E402


class P331ClosedResultFinalizerTests(unittest.TestCase):
    def test_reconstructs_exact_published_no_proof_without_mutation(self) -> None:
        path = finalizer.RUN_DIR / "live-result.json"
        before = path.read_bytes()
        value, payload, _live = finalizer.reconstruct()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(payload, before)
        self.assertEqual(
            {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()},
            finalizer.EXPECTED_RESULT,
        )
        self.assertEqual(value["current_state"], "CLOSED")
        self.assertEqual(value["verdict"], "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK")
        self.assertEqual(
            value["outcome_class"],
            "p331_authenticated_resident_heartbeat_unproved_rollback_verified",
        )
        self.assertFalse(value["recovery_required"])

    def test_finalizer_has_no_device_or_recovery_backend(self) -> None:
        source = Path(finalizer.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "SamsungOdinBackend",
            "recover_prepared(",
            "execute_prepared(",
            "subprocess",
            "adb_client",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn('parser.add_argument("--publish", action="store_true")', source)

    def test_publish_is_mode0400_and_no_clobber(self) -> None:
        value = {"closed": True}
        payload = json.dumps(value, indent=2, sort_keys=True).encode() + b"\n"
        with tempfile.TemporaryDirectory(prefix="p331-finalizer-") as name:
            run_dir = Path(name)
            live = SimpleNamespace(_write_exclusive=core._write_exclusive)
            with mock.patch.object(finalizer, "RUN_DIR", run_dir):
                finalizer._publish(live, value, payload)  # noqa: SLF001
                result = run_dir / "live-result.json"
                self.assertEqual(result.read_bytes(), payload)
                self.assertEqual(result.stat().st_mode & 0o777, 0o400)
                with self.assertRaises(finalizer.FinalizerError):
                    finalizer._publish(live, value, payload)  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
