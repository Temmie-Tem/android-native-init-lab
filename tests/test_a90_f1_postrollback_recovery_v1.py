from __future__ import annotations

import copy
import importlib.util
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path


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


R = load("a90_f1_postrollback_recovery_v1")
O = R.owner


class PostrollbackRecoveryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.qualification_review = "a" * 64
        self.current_review = "b" * 64
        self.manifest = {
            "runId": "test-run",
            "expectedStart": {
                "version": O.V2321_ROLLBACK_VERSION,
                "build": O.V2321_ROLLBACK_BUILD,
            },
            "candidate": {"path": "/candidate", "size": 1, "sha256": "c" * 64},
            "rollback": {
                "path": "/rollback",
                "size": 1,
                "sha256": O.V2321_ROLLBACK_SHA256,
                "version": O.V2321_ROLLBACK_VERSION,
                "build": O.V2321_ROLLBACK_BUILD,
            },
            "qualification": {
                "review": {"sha256": self.qualification_review},
                "hazard": {"id": "hazard", "accepted": True},
            },
        }
        self.snapshot = O.Snapshot(
            target_evidence_sha256="d" * 64,
            boot_id="01234567-89ab-cdef-0123-456789abcdef",
            version=O.V2321_ROLLBACK_VERSION,
            build=O.V2321_ROLLBACK_BUILD,
            healthy=True,
            recovery_available=True,
            recovery_evidence_sha256=self.qualification_review,
            fresh_state_observed=False,
            fresh_state_absent=False,
            other_targets_untouched=True,
            receipt_sha256="e" * 64,
        )

    def test_exact_recovery_payload_preserves_unproved_rollback(self) -> None:
        payload = R._payload(self.snapshot, self.current_review)
        self.assertEqual(
            R._validate_payload(
                payload,
                self.manifest,
                self.qualification_review,
                self.current_review,
            ),
            payload,
        )
        self.assertEqual(payload["rollbackOutcome"], "UNPROVED_EXTERNAL_CONTINUATION")
        self.assertFalse(payload["candidateReplay"])
        self.assertFalse(payload["rollbackReplay"])

    def test_recovery_payload_rejects_replay_review_and_health_drift(self) -> None:
        for key, value in (
            ("candidateReplay", True),
            ("rollbackReplay", True),
            ("currentReviewSha256", "f" * 64),
        ):
            with self.subTest(key=key):
                payload = R._payload(self.snapshot, self.current_review)
                payload[key] = value
                with self.assertRaises(O.ContractError):
                    R._validate_payload(
                        payload,
                        self.manifest,
                        self.qualification_review,
                        self.current_review,
                    )
        unhealthy = self.snapshot.payload()
        unhealthy["healthy"] = False
        payload = R._payload(self.snapshot, self.current_review)
        payload["recoveredSnapshot"] = unhealthy
        payload["recoveredSnapshotSha256"] = O.sha256_bytes(O.canonical_json(unhealthy))
        with self.assertRaises(O.ContractError):
            R._validate_payload(
                payload,
                self.manifest,
                self.qualification_review,
                self.current_review,
            )

    def test_only_consumed_rollback_terminal_is_admitted(self) -> None:
        manifest_sha = "f" * 64
        records = {
            name: {"manifestSha256": manifest_sha, "payload": {}}
            for name in O.ROLLBACK_PATH
        }
        checkpoint = lambda role: {
            "role": role,
            "path": self.manifest[role]["path"],
            "dev": 1,
            "ino": 2,
            "mode": 0o100600,
            "uid": 1000,
            "gid": 1000,
            "nlink": 1,
            "size": self.manifest[role]["size"],
            "sha256": self.manifest[role]["sha256"],
        }
        prepared_snapshot = replace(
            self.snapshot, fresh_state_observed=True, fresh_state_absent=True
        )
        records["00-prepared.json"]["schema"] = O.RECORD_SCHEMA
        records["00-prepared.json"]["kind"] = "PREPARED"
        records["00-prepared.json"]["payload"] = {
            "schema": O.PREPARED_SCHEMA,
            "runId": self.manifest["runId"],
            "candidate": checkpoint("candidate"),
            "rollback": checkpoint("rollback"),
            "snapshot": prepared_snapshot.payload(),
        }
        approval = O.approval_token(
            manifest_sha, prepared_snapshot, self.manifest["runId"]
        )
        records["10-approved.json"]["payload"] = {
            "approvalSha256": O.sha256_bytes(approval.encode("ascii"))
        }
        records["20-candidate-intent.json"]["payload"] = {
            "sha256": self.manifest["candidate"]["sha256"]
        }
        records["21-candidate-launched.json"]["payload"] = {"attempt": 1}
        records["22-candidate-result.json"]["payload"] = {
            "returncode": 1,
            "completed": False,
            "quiescent": True,
            "receiptSha256": "3" * 64,
            "outcome": "WRITE_OR_READBACK_UNCLASSIFIED",
        }
        records["30-rollback-intent.json"]["payload"] = {
            "sha256": self.manifest["rollback"]["sha256"]
        }
        records["31-rollback-launched.json"]["payload"] = {"attempt": 1}
        records["32-rollback-result.json"]["payload"] = {
            "returncode": 1,
            "completed": False,
            "quiescent": True,
            "receiptSha256": "1" * 64,
            "outcome": "WRITE_OR_READBACK_UNCLASSIFIED",
        }
        records["40-terminal.json"]["payload"] = {
            "schema": O.RESULT_SCHEMA,
            "terminal": "RECOVERY_REQUIRED",
            "reason": "ROLLBACK_HEALTH_UNPROVED",
            "snapshot": None,
            "candidateReplay": False,
            "qualification": {
                "recoveryEvidenceSha256": self.qualification_review,
                "hazardId": "hazard",
                "hazardAccepted": True,
            },
        }
        R._require_prefix(records, self.manifest, manifest_sha)
        for name in (
            "00-prepared.json", "10-approved.json",
            "21-candidate-launched.json", "22-candidate-result.json",
        ):
            with self.subTest(empty_payload=name):
                malformed = copy.deepcopy(records)
                malformed[name]["payload"] = {}
                with self.assertRaises(O.ContractError):
                    R._require_prefix(malformed, self.manifest, manifest_sha)
        for name in ("21-candidate-launched.json", "31-rollback-launched.json"):
            for invalid in (True, 1.0, "1"):
                with self.subTest(typed_attempt=(name, invalid)):
                    malformed = copy.deepcopy(records)
                    malformed[name]["payload"]["attempt"] = invalid
                    with self.assertRaises(O.ContractError):
                        R._require_prefix(malformed, self.manifest, manifest_sha)
        for mutate in (
            lambda: records["40-terminal.json"]["payload"].__setitem__(
                "terminal", "PASS_A90_RESIDENT_INSTALLED"
            ),
            lambda: records["40-terminal.json"]["payload"].__setitem__(
                "reason", "ROLLBACK_HELPER_NOT_QUIESCENT"
            ),
            lambda: records["32-rollback-result.json"]["payload"].__setitem__(
                "quiescent", False
            ),
        ):
            with self.subTest(mutate=mutate):
                records["40-terminal.json"]["payload"]["terminal"] = "RECOVERY_REQUIRED"
                records["40-terminal.json"]["payload"]["reason"] = "ROLLBACK_HEALTH_UNPROVED"
                records["32-rollback-result.json"]["payload"]["quiescent"] = True
                mutate()
                with self.assertRaises(O.ContractError):
                    R._require_prefix(records, self.manifest, manifest_sha)

    def test_review_is_outside_its_own_closure(self) -> None:
        self.assertNotIn(str(R.REVIEW_PATH.relative_to(ROOT)), O.EXECUTION_SOURCE_RELS)
        self.assertRegex(R.execution_closure_sha256(), r"^[0-9a-f]{64}$")

    def test_review_and_guards_are_rechecked_immediately_before_observation(self) -> None:
        source = (MODULE_DIR / "a90_f1_postrollback_recovery_v1.py").read_text()
        backend = source.index('backend = owner._live_backend(manifest, "postrollback-recovery")')
        lease = source.index(
            "if _review_lease() != (current_review_sha, review_closure):", backend
        )
        active = source.index("owner._require_active_guard(manifest)", lease)
        candidate = source.index("owner._require_candidate_guard(manifest)", active)
        observe = source.index("snapshot = backend.observe(", candidate)
        self.assertLess(backend, lease)
        self.assertLess(lease, active)
        self.assertLess(active, candidate)
        self.assertLess(candidate, observe)

    def test_dangling_active_guard_is_present_not_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "active-run.guard"
            path.symlink_to(Path(temporary) / "missing")
            self.assertTrue(R._directory_entry_present(path))
            path.unlink()
            self.assertFalse(R._directory_entry_present(path))


if __name__ == "__main__":
    unittest.main()
