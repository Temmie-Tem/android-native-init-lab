from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
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


M = load("a90_boot_only_f1_minimal_v1")
A = load("a90_boot_only_f1_adapter_v1")
R = load("a90_h27_pretransfer_abort_reconcile_v1")


def phase(role: str, size: int, digest: str) -> str:
    prefix = "[native-init-flash 00:00:00] "
    common = (
        f"{prefix}local image size: {size}\n"
        f"{prefix}local image sha256: {digest}\n"
        f"{prefix}phase.native_init_flash.inspect_local_image.elapsed_sec=0.001 ok=1\n"
    )
    if role == "candidate":
        return (
            common
            + f"{prefix}phase.native_init_flash.native_to_recovery.elapsed_sec=0.001 ok=1\n"
            + f"{prefix}phase.native_init_flash.wait_recovery_adb.elapsed_sec=1.000 ok=1\n"
            + f"{prefix}phase.native_init_flash.total.elapsed_sec=1.002 ok=0\n"
            + f"{prefix}error: [Errno 27] File too large\n"
        )
    return (
        common
        + f"{prefix}phase.native_init_flash.total.elapsed_sec=0.002 ok=0\n"
        + f"{prefix}error: ADB baseline already contains a recovery endpoint\n"
    )


class PretransferAbortReconcileTest(unittest.TestCase):
    def setUp(self):
        self.manifest = {
            "candidate": {"size": 58_368_000, "sha256": "a" * 64},
            "rollback": {"size": 60_882_944, "sha256": "b" * 64},
        }
        self.candidate = phase(
            "candidate",
            self.manifest["candidate"]["size"],
            self.manifest["candidate"]["sha256"],
        ).encode()
        self.rollback = phase(
            "rollback",
            self.manifest["rollback"]["size"],
            self.manifest["rollback"]["sha256"],
        ).encode()

    def test_receipt_duration_is_recovered_only_from_exact_logs(self):
        argv = ("python", "helper", "candidate")
        receipt = {
            "argv": list(argv),
            "returncode": 1,
            "quiescent": True,
            "stdoutSha256": M.sha256_bytes(b"stdout"),
            "stderrSha256": M.sha256_bytes(b"stderr"),
            "durationMs": 17,
        }
        digest = M.sha256_bytes(M.canonical_json(receipt))
        self.assertEqual(
            R.bind_effect_receipt(
                expected_sha256=digest,
                argv=argv,
                returncode=1,
                quiescent=True,
                stdout=b"stdout",
                stderr=b"stderr",
                maximum_duration_ms=20,
            ),
            17,
        )
        with self.assertRaisesRegex(M.ContractError, "one bound"):
            R.bind_effect_receipt(
                expected_sha256=digest,
                argv=argv,
                returncode=1,
                quiescent=True,
                stdout=b"changed",
                stderr=b"stderr",
                maximum_duration_ms=20,
            )

    def test_empty_direct_log_is_valid_but_symlink_is_not(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            empty = root / "empty.log"
            empty.touch(mode=0o600)
            self.assertEqual(R._read_log(empty, "empty log"), b"")
            link = root / "link.log"
            link.symlink_to(empty)
            with self.assertRaisesRegex(M.ContractError, "identity mismatch"):
                R._read_log(link, "linked log")

    def test_exact_pretransfer_failure_logs_are_accepted(self):
        R.validate_pretransfer_logs(
            candidate_stderr=self.candidate,
            rollback_stderr=self.rollback,
            manifest=self.manifest,
        )

    def test_any_transfer_or_write_stage_is_rejected(self):
        for token in (
            "phase.native_init_flash.adb_push.elapsed_sec=0.001 ok=0",
            "phase.native_init_flash.boot_dd_write.elapsed_sec=0.001 ok=1",
            "phase.native_init_flash.boot_readback_sha256.elapsed_sec=0.001 ok=1",
            "sealed local image copy: /tmp/boot.img",
        ):
            with self.subTest(token=token), self.assertRaisesRegex(
                M.ContractError, "forbidden stage"
            ):
                R.validate_pretransfer_logs(
                    candidate_stderr=self.candidate + (token + "\n").encode(),
                    rollback_stderr=self.rollback,
                    manifest=self.manifest,
                )

    def test_rollback_must_not_enter_recovery_or_transfer(self):
        with self.assertRaisesRegex(M.ContractError, "rollback advanced"):
            R.validate_pretransfer_logs(
                candidate_stderr=self.candidate,
                rollback_stderr=(
                    self.rollback
                    + b"requesting recovery from native init bridge\n"
                ),
                manifest=self.manifest,
            )

    def test_owner_accepts_only_the_appended_reconciliation_record(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "run"
            run.mkdir(mode=0o700)
            digest = "c" * 64
            for name in M.PRETRANSFER_ABORT_PATH:
                M.publish_record(
                    run,
                    name,
                    M._record(M.RECORD_KINDS[name], digest, {}),
                )
            self.assertEqual(tuple(M.read_records(run)), M.PRETRANSFER_ABORT_PATH)
            self.assertEqual(
                M.recovery_decision(run),
                "PRETRANSFER_ABORT_RECONCILED_RETRY_ALLOWED",
            )

    def test_review_lineage_rebinds_current_review_without_losing_history(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            historical = root / "historical.json"
            current = root / "current.json"
            historical.write_bytes(b"{}")
            current.write_bytes(b'{"verdict":"PASS_GO"}')
            historical.chmod(0o600)
            current.chmod(0o600)
            manifest = {
                "qualification": {
                    "review": {
                        "path": "/retired/path.json",
                        "size": 2,
                        "sha256": M.sha256_bytes(b"{}"),
                    }
                }
            }
            with (
                mock.patch.object(R, "HISTORICAL_REVIEW_PATH", historical),
                mock.patch.object(R, "HISTORICAL_REVIEW_SIZE", 2),
                mock.patch.object(
                    R, "HISTORICAL_REVIEW_SHA256", M.sha256_bytes(b"{}")
                ),
                mock.patch.object(R, "CURRENT_REVIEW_PATH", current),
                mock.patch.object(
                    M, "_verify_qualification_inputs"
                ) as verify_current,
            ):
                rebound, digest = R._verify_review_lineage(manifest)
            self.assertEqual(digest, M.sha256_bytes(current.read_bytes()))
            self.assertEqual(rebound["qualification"]["review"]["path"], str(current))
            self.assertEqual(
                rebound["qualification"]["review"]["sha256"], digest
            )
            verify_current.assert_called_once_with(rebound)

    def test_post_record_cleanup_rejects_current_review_drift(self):
        snapshot = {
            "targetEvidenceSha256": "a" * 64,
            "bootId": "01234567-89ab-cdef-0123-456789abcdef",
            "healthy": True,
            "recoveryAvailable": True,
            "recoveryEvidenceSha256": "d" * 64,
            "freshStateObserved": True,
            "freshStateAbsent": True,
            "otherTargetsUntouched": True,
            "version": "0.11.192",
            "build": "phase3-minimal-h24-ufs-auth-native-hud-private-card-root-minimal-debian-dev",
            "receiptSha256": "b" * 64,
        }
        payload = {
            "schema": R.SCHEMA,
            "decision": R.DECISION,
            "candidateRetryPermitted": True,
            "currentReviewSha256": "d" * 64,
            "candidate": {
                "receiptSha256": R.CANDIDATE_RECEIPT_SHA256,
                "durationMs": 1,
                "transferStarted": False,
                "bootWriteStarted": False,
            },
            "rollback": {
                "receiptSha256": R.ROLLBACK_RECEIPT_SHA256,
                "durationMs": 1,
                "transferStarted": False,
                "bootWriteStarted": False,
            },
            "recoveredSnapshot": snapshot,
        }
        R._validate_reconciliation_payload(payload, "d" * 64)
        with self.assertRaisesRegex(M.ContractError, "decision is invalid"):
            R._validate_reconciliation_payload(payload, "e" * 64)

        partial = dict(payload)
        partial["currentReviewSha256"] = "d" * 64
        partial["recoveredSnapshot"] = {
            "healthy": True,
            "freshStateObserved": True,
            "freshStateAbsent": True,
            "otherTargetsUntouched": True,
            "version": "0.11.192",
            "build": "phase3-minimal-h24-ufs-auth-native-hud-private-card-root-minimal-debian-dev",
        }
        with self.assertRaisesRegex(M.ContractError, "fields mismatch"):
            R._validate_reconciliation_payload(partial, "d" * 64)

    def test_review_drift_between_guard_removals_keeps_candidate_guard(self):
        class DriftingLease:
            checks = 0

            def check(self):
                self.checks += 1
                if self.checks == 2:
                    raise M.ContractError("current review lease drifted during cleanup")

            def close(self):
                return None

        lease = DriftingLease()
        with (
            mock.patch.object(M, "_active_guard", return_value=(Path("/active"), b"a")),
            mock.patch.object(M, "_candidate_guard", return_value=(Path("/candidate"), b"c")),
            mock.patch.object(R, "_release_guard_if_present") as release,
            self.assertRaisesRegex(M.ContractError, "drifted during cleanup"),
        ):
            R._cleanup_guards_with_review_lease(
                {"candidate": {}, "qualification": {}},
                lease,
            )
        release.assert_called_once_with(Path("/active"), b"a", "active run guard")

    def test_internally_consistent_foreign_manifest_journal_is_rejected(self):
        records = {
            name: {"manifestSha256": "e" * 64, "payload": {}}
            for name in M.ROLLBACK_PATH
        }
        with self.assertRaisesRegex(M.ContractError, "fixed manifest"):
            R._require_incident_records(
                records,
                {"candidate": {"sha256": "a" * 64}, "rollback": {"sha256": "b" * 64}},
                "d" * 64,
            )

    def test_any_historical_record_payload_mutation_is_rejected(self):
        records = {
            name: {"schema": "record", "name": name, "payload": {"exact": True}}
            for name in M.ROLLBACK_PATH
        }
        expected = {
            name: M.sha256_bytes(M.canonical_json(value))
            for name, value in records.items()
        }
        with mock.patch.object(R, "INCIDENT_RECORD_SHA256", expected):
            R._require_fixed_record_hashes(records)
            records["00-prepared.json"]["payload"] = {}
            with self.assertRaisesRegex(M.ContractError, "00-prepared"):
                R._require_fixed_record_hashes(records)

    def test_guard_loss_during_preflight_prevents_retry_publication(self):
        manifest = {
            "runId": R.RUN_ID,
            "candidate": {
                "path": "/candidate.img",
                "sha256": "a" * 64,
                "version": "candidate",
            },
            "rollback": {
                "path": "/rollback.img",
                "sha256": "b" * 64,
                "version": "rollback",
            },
            "qualification": {
                "recoveryIdentity": {"adbSerialSha256": "c" * 64},
            },
            "timeouts": {"flashSec": 60},
        }
        recovered = M.Snapshot(
            target_evidence_sha256="a" * 64,
            boot_id="01234567-89ab-cdef-0123-456789abcdef",
            version="0.11.192",
            build="phase3-minimal-h24-ufs-auth-native-hud-private-card-root-minimal-debian-dev",
            healthy=True,
            recovery_available=True,
            recovery_evidence_sha256="d" * 64,
            fresh_state_observed=True,
            fresh_state_absent=True,
            other_targets_untouched=True,
            receipt_sha256="e" * 64,
        )

        class Lease:
            def check(self):
                return None

            def close(self):
                return None

        backend = mock.Mock()
        backend.preflight.return_value = recovered
        for lost in ("active", "candidate"):
            active = [None, None]
            candidate = [None, None]
            (active if lost == "active" else candidate)[1] = M.ContractError(
                f"{lost} guard lost"
            )
            with self.subTest(lost=lost), mock.patch.object(
                R, "_load_incident_manifest", return_value=(b"{}", manifest)
            ), mock.patch.object(
                R, "_verify_review_lineage", return_value=(manifest, "d" * 64)
            ), mock.patch.object(
                R, "CurrentReviewLease", return_value=Lease()
            ), mock.patch.object(
                M, "ensure_run_root"
            ), mock.patch.object(
                M, "_require_run_path"
            ), mock.patch.object(
                R, "_require_direct_private_directory"
            ), mock.patch.object(
                M, "read_records", return_value={"40-terminal.json": {}}
            ), mock.patch.object(
                R, "_require_incident_records"
            ), mock.patch.object(
                M, "_require_active_guard", side_effect=active
            ), mock.patch.object(
                M, "_require_candidate_guard", side_effect=candidate
            ), mock.patch.object(
                R, "_read_log", return_value=b""
            ), mock.patch.object(
                R, "bind_effect_receipt", return_value=1
            ), mock.patch.object(
                R, "validate_pretransfer_logs"
            ), mock.patch.object(
                M, "_live_backend", return_value=backend
            ), mock.patch.object(
                M, "_require_start"
            ), mock.patch.object(
                R, "_validate_reconciliation_payload"
            ), mock.patch.object(
                M, "publish_record"
            ) as publish, self.assertRaisesRegex(M.ContractError, "guard lost"):
                R.reconcile()
            publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
