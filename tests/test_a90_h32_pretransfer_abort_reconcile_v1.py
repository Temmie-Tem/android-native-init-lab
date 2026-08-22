"""Host-only H32 pre-write park and no-replay checks."""

from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "workspace/public/src/scripts/server-distro"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))


def load(name: str):
    source = MODULE_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class H32PretransferAbortTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.R = load("a90_h32_pretransfer_abort_reconcile_v1")
        cls.O = cls.R._owner
        cls.A = cls.R._adapter
        cls.H31 = load("a90_h31_pretransfer_abort_reconcile_v1")

    def test_exact_h32_identity_and_no_dispatch_log(self):
        self.assertEqual(self.H31.RUN_ID, "a90-h31-f1-20260822-01")
        self.assertEqual(self.H31.CAPABILITY, "A90_H31_PRETRANSFER_ABORT_RECONCILE_V1")
        self.assertEqual(self.R.RUN_ID, "a90-h32-f1-20260822-01")
        self.assertEqual(self.R.CANDIDATE["version"], "0.11.199")
        self.assertEqual(
            self.R.CANDIDATE["sha256"],
            "e56cb1201d63e26f275de10d6a4eb6a1686f6021b6613aa4dde1374930dd299d",
        )
        self.assertEqual(
            tuple(self.R.RECORD_HASHES),
            (
                "00-prepared.json",
                "10-approved.json",
                "20-candidate-intent.json",
                "21-candidate-launched.json",
                "22-candidate-result.json",
                "30-rollback-intent.json",
                "31-rollback-launched.json",
            ),
        )
        self.assertNotIn("flash-rollback.stdout", self.R.LOG_HASHES)
        self.assertNotIn("flash-rollback.stderr", self.R.LOG_HASHES)

    def test_candidate_receipt_is_pre_write_failure(self):
        if not self.R.LOG_DIRECTORY.is_dir():
            self.skipTest("private H32 execute logs are not present")
        stdout, _stderr = self.R._engine._require_logs()
        self.assertEqual(self.A._parse_owner_effect_receipt(stdout), "PRE_WRITE_FAILURE")

    def test_reconciliation_payload_cannot_claim_rollback_dispatch(self):
        manifest = {
            "rollback": self.R.ROLLBACK,
            "qualification": {"review": {"sha256": "b" * 64}},
        }
        snapshot = self.O.Snapshot(
            target_evidence_sha256="a" * 64,
            boot_id="01234567-89ab-cdef-0123-456789abcdef",
            version=self.R.ROLLBACK["version"],
            build=self.R.ROLLBACK["build"],
            healthy=True,
            recovery_available=True,
            recovery_evidence_sha256="b" * 64,
            fresh_state_observed=False,
            fresh_state_absent=False,
            other_targets_untouched=True,
            receipt_sha256="c" * 64,
        )
        payload = {
            "schema": self.R.SCHEMA,
            "decision": self.R.DECISION,
            "candidateReplay": False,
            "rollbackReplay": False,
            "candidateRetryPermitted": False,
            "currentReviewSha256": "d" * 64,
            "candidate": {
                "receiptSha256": self.R.CANDIDATE_RECEIPT_SHA256,
                "outcome": "PRE_WRITE_FAILURE",
                "transferStarted": False,
                "bootWriteStarted": False,
            },
            "rollback": {
                "intentRecorded": True,
                "launchedRecorded": True,
                "helperDispatched": False,
                "helperLogPresent": False,
                "transferStarted": False,
                "bootWriteStarted": False,
            },
            "recoveredSnapshot": snapshot.payload(),
        }
        self.R._engine._validate_payload(payload, manifest, "d" * 64)
        payload["rollback"] = dict(payload["rollback"])
        payload["rollback"]["helperDispatched"] = True
        with self.assertRaisesRegex(self.R.ContractError, "rollback reconciliation"):
            self.R._engine._validate_payload(payload, manifest, "d" * 64)

    def test_reconciler_source_has_no_effect_primitive(self):
        source = Path(self.R.__file__).read_text()
        for forbidden in ("adb push", "boot_dd_write", "twrp reboot", "flash-rollback"):
            self.assertNotIn(forbidden, source)

    def test_h32_closure_is_not_owner_only(self):
        current = self.R.execution_closure_sha256()
        with mock.patch.object(self.R._owner, "execution_closure_sha256", return_value="a" * 64):
            self.assertNotEqual(self.R.execution_closure_sha256(), current)

    def test_h32_closure_includes_same_length_h31_engine_bytes(self):
        original = Path.read_bytes
        current = self.R.execution_closure_sha256()

        def altered(path: Path) -> bytes:
            raw = original(path)
            if path == self.R._ENGINE_PATH:
                return b"X" + raw[1:]
            return raw

        with mock.patch.object(Path, "read_bytes", new=altered):
            self.assertNotEqual(self.R.execution_closure_sha256(), current)

    def test_h32_wrapper_has_no_public_engine_forwarding_or_h31_mutation(self):
        self.assertFalse(hasattr(self.R, "owner"))
        self.assertFalse(hasattr(self.R, "adapter"))
        self.assertFalse(hasattr(self.R, "_fresh_v2321_observation"))
        self.assertEqual(self.H31.RUN_ID, "a90-h31-f1-20260822-01")
        self.assertEqual(self.H31.CAPABILITY, "A90_H31_PRETRANSFER_ABORT_RECONCILE_V1")


if __name__ == "__main__":
    unittest.main()
