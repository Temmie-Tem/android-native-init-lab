"""Private-free H31 pre-write park reconciliation checks."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
import sys
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "workspace/public/src/scripts/server-distro"
sys.path.insert(0, str(MODULE_DIR))


def load(name: str):
    source = MODULE_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


O = load("a90_boot_only_f1_minimal_v1")
A = load("a90_boot_only_f1_adapter_v1")
R = load("a90_h31_pretransfer_abort_reconcile_v1")


class H31PretransferAbortReconcileTest(unittest.TestCase):
    def test_unset_evidence_pin_fails_closed(self):
        with self.assertRaisesRegex(R.ContractError, "still UNSET"):
            R._require_sha(R.UNSET_SHA256, "test pin")

    def test_owner_accepts_only_h31_31_plus_41_prefix(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run"
            run.mkdir(mode=0o700)
            manifest_sha = "a" * 64
            for name in O.H31_PRETRANSFER_ABORT_PATH:
                O.publish_record(run, name, O._record(O.RECORD_KINDS[name], manifest_sha, {}))
            self.assertEqual(tuple(O.read_records(run)), O.H31_PRETRANSFER_ABORT_PATH)
            self.assertEqual(
                O.recovery_decision(run),
                "PRETRANSFER_ABORT_RECONCILED_NO_REPLAY",
            )

    def test_owner_rejects_rollback_result_or_terminal_after_h31_launch(self):
        manifest_sha = "a" * 64
        records = {
            name: O._record(O.RECORD_KINDS[name], manifest_sha, {})
            for name in O.H31_PRETRANSFER_ABORT_PATH[:-1]
        }
        records["32-rollback-result.json"] = O._record(
            "ROLLBACK_RESULT", manifest_sha, {}
        )
        with self.assertRaisesRegex(R.ContractError, "31\\+41 prefix"):
            R._require_records(records, manifest_sha, closed=False)

    def test_candidate_receipt_duration_is_bound_to_fixed_hash(self):
        stdout = b"candidate receipt"
        stderr = b"candidate stderr"
        argv = ("fixed", "candidate")
        expected = {
            "argv": list(argv),
            "returncode": 1,
            "quiescent": True,
            "stdoutSha256": O.sha256_bytes(stdout),
            "stderrSha256": O.sha256_bytes(stderr),
            "durationMs": 9,
        }
        digest = O.sha256_bytes(O.canonical_json(expected))
        self.assertEqual(
            R.bind_effect_receipt(
                expected_sha256=digest,
                argv=argv,
                stdout=stdout,
                stderr=stderr,
                maximum_duration_ms=20,
            ),
            9,
        )
        with self.assertRaisesRegex(R.ContractError, "do not bind"):
            R.bind_effect_receipt(
                expected_sha256=digest,
                argv=argv,
                stdout=b"mutated",
                stderr=stderr,
                maximum_duration_ms=20,
            )

    def test_candidate_structured_receipt_and_exact_log_inventory(self):
        receipt = A.canonical_json(
            {
                "schema": A.OWNER_RECEIPT_SCHEMA,
                "mode": A.OWNER_RECEIPT_MODE,
                "outcome": "PRE_WRITE_FAILURE",
                "writeStarted": False,
                "bootWrittenReadbackExact": False,
                "systemReturnAttempted": False,
                "systemReturnCommandOk": False,
                "systemReturnConfirmed": False,
            }
        )
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            stdout_path = directory / "011-flash-candidate.stdout"
            stderr_path = directory / "011-flash-candidate.stderr"
            stdout_path.write_bytes(receipt)
            stderr_path.write_bytes(b"")
            stdout_path.chmod(0o600)
            stderr_path.chmod(0o600)
            hashes = {
                stdout_path.name: O.sha256_bytes(receipt),
                stderr_path.name: O.sha256_bytes(b""),
            }
            with (
                mock.patch.object(R, "LOG_DIRECTORY", directory),
                mock.patch.object(R, "LOG_HASHES", hashes),
            ):
                stdout, stderr = R._require_logs()
            self.assertEqual(stdout, receipt)
            self.assertEqual(stderr, b"")

            (directory / "flash-rollback.stdout").write_bytes(b"forbidden")
            with (
                mock.patch.object(R, "LOG_DIRECTORY", directory),
                mock.patch.object(R, "LOG_HASHES", hashes),
                self.assertRaisesRegex(R.ContractError, "log inventory is not exact"),
            ):
                R._require_logs()

    def test_reconciliation_payload_requires_no_replay_and_no_rollback_dispatch(self):
        manifest = {
            "rollback": R.ROLLBACK,
            "qualification": {
                "review": {"sha256": "b" * 64},
            },
        }
        snapshot = O.Snapshot(
            target_evidence_sha256="a" * 64,
            boot_id="01234567-89ab-cdef-0123-456789abcdef",
            version=R.ROLLBACK["version"],
            build=R.ROLLBACK["build"],
            healthy=True,
            recovery_available=True,
            recovery_evidence_sha256="b" * 64,
            fresh_state_observed=False,
            fresh_state_absent=False,
            other_targets_untouched=True,
            receipt_sha256="c" * 64,
        )
        payload = {
            "schema": R.SCHEMA,
            "decision": R.DECISION,
            "candidateReplay": False,
            "rollbackReplay": False,
            "candidateRetryPermitted": False,
            "currentReviewSha256": "d" * 64,
            "candidate": {
                "receiptSha256": R.CANDIDATE_RECEIPT_SHA256,
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
        R._validate_payload(payload, manifest, "d" * 64)
        mutated = dict(payload)
        mutated["rollback"] = dict(payload["rollback"])
        mutated["rollback"]["helperDispatched"] = True
        with self.assertRaisesRegex(R.ContractError, "rollback reconciliation"):
            R._validate_payload(mutated, manifest, "d" * 64)

    def test_active_cleanup_never_removes_candidate_guard(self):
        with tempfile.TemporaryDirectory() as temp:
            active = Path(temp) / "active.guard"
            active.write_bytes(b"active")
            manifest = {"candidate": {"sha256": "a" * 64}}
            with (
                mock.patch.object(R.owner, "_require_candidate_guard") as candidate,
                mock.patch.object(R.owner, "_active_guard", return_value=(active, b"active")),
                mock.patch.object(R.owner, "_verify_input", return_value=b"active"),
                mock.patch.object(R.owner, "_fsync_directory"),
            ):
                R._release_active_if_present(manifest)
            candidate.assert_called_once_with(manifest)
            self.assertFalse(active.exists())

    def test_reconcile_source_rechecks_review_and_candidate_after_cleanup(self):
        source = (MODULE_DIR / "a90_h31_pretransfer_abort_reconcile_v1.py").read_text()
        for occurrence in (
            "_release_active_if_present(manifest)\n        if _review_lease()",
            "_release_active_if_present(manifest)\n    if _review_lease()",
        ):
            self.assertIn(occurrence, source)
        self.assertGreaterEqual(
            source.count("owner._require_candidate_guard(manifest)"), 5
        )


if __name__ == "__main__":
    unittest.main()
