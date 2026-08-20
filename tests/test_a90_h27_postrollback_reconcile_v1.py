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
    if name in sys.modules:
        return sys.modules[name]
    source = MODULE_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, source)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = load("a90_boot_only_f1_minimal_v1")
load("a90_boot_only_f1_adapter_v1")
R = load("a90_h27_postrollback_reconcile_v1")


class DummyLease:
    def __init__(self, _manifest, _sha256):
        self.checks = 0

    def check(self):
        self.checks += 1

    def close(self):
        pass


class ObserveOnlyBackend:
    def __init__(self, snapshot, mutation=None):
        self.snapshot = snapshot
        self.mutation = mutation
        self.observe_calls = 0

    def observe(self, expected, fresh_state, *, require_fresh_state, timeout_sec):
        self.observe_calls += 1
        if expected["version"] != "0.9.285" or require_fresh_state is not False:
            raise AssertionError("postrollback reconciler requested the wrong observation")
        if fresh_state["enablePath"].endswith(".enable") is not True:
            raise AssertionError("fresh-state identity was not propagated")
        if timeout_sec != 300:
            raise AssertionError("health timeout changed")
        if self.mutation is not None:
            self.mutation()
        return self.snapshot

    def flash(self, *_args, **_kwargs):
        raise AssertionError("terminal-only reconciliation attempted an effect")


class PostrollbackReconcileTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "runs"
        self.root.mkdir(mode=0o700)
        self.old_root = M.RUN_ROOT
        M.RUN_ROOT = self.root
        self.addCleanup(setattr, M, "RUN_ROOT", self.old_root)
        self.manifest = {
            "runId": R.RUN_ID,
            "candidate": {"sha256": "a" * 64},
            "rollback": {
                "sha256": "b" * 64,
                "version": "0.9.285",
                "build": "v2321-usb-clean-identity-rodata",
            },
            "qualification": {
                "review": {"path": "/tmp/current.json", "size": 1, "sha256": "c" * 64},
                "freshState": {
                    "enablePath": "/cache/a90-h27.enable",
                    "latchPath": "/cache/a90-h27.done",
                },
            },
            "timeouts": {"healthSec": 300},
        }
        self.raw = M.canonical_json(self.manifest)
        self.manifest_sha256 = M.sha256_bytes(self.raw)
        self.old_manifest_sha256 = R.MANIFEST_SHA256
        R.MANIFEST_SHA256 = self.manifest_sha256
        self.addCleanup(setattr, R, "MANIFEST_SHA256", self.old_manifest_sha256)
        self.run_directory = self.root / R.RUN_ID
        self.run_directory.mkdir(mode=0o700)
        self._write_incident()
        M._publish_active_guard(self.manifest)
        M._publish_candidate_guard(self.manifest)
        self.snapshot = M.Snapshot(
            target_evidence_sha256="d" * 64,
            boot_id="01234567-89ab-cdef-0123-456789abcdef",
            version="0.9.285",
            build="v2321-usb-clean-identity-rodata",
            healthy=True,
            recovery_available=True,
            recovery_evidence_sha256="c" * 64,
            fresh_state_observed=False,
            fresh_state_absent=False,
            other_targets_untouched=True,
            receipt_sha256="e" * 64,
        )

    def _write_incident(self):
        for name in M.ROLLBACK_PATH:
            payload = {}
            if name == "20-candidate-intent.json":
                payload = {"sha256": self.manifest["candidate"]["sha256"]}
            elif name == "30-rollback-intent.json":
                payload = {"sha256": self.manifest["rollback"]["sha256"]}
            elif name == "40-terminal.json":
                payload = {
                    "schema": M.RESULT_SCHEMA,
                    "terminal": "RECOVERY_REQUIRED",
                    "reason": "ROLLBACK_HEALTH_UNPROVED",
                    "snapshot": None,
                    "candidateReplay": False,
                }
            record = M._record(M.RECORD_KINDS[name], self.manifest_sha256, payload)
            M.publish_record(self.run_directory, name, record)
        records = M.read_records(self.run_directory)
        self.old_hashes = R.INCIDENT_RECORD_SHA256
        R.INCIDENT_RECORD_SHA256 = {
            name: M.sha256_bytes(M.canonical_json(record))
            for name, record in records.items()
        }
        self.addCleanup(setattr, R, "INCIDENT_RECORD_SHA256", self.old_hashes)

    def _run(self, snapshot=None, mutation=None):
        backend = ObserveOnlyBackend(
            self.snapshot if snapshot is None else snapshot, mutation=mutation
        )
        patches = (
            mock.patch.object(R, "_load_incident_manifest", return_value=(self.raw, self.manifest)),
            mock.patch.object(R, "_current_manifest", return_value=(self.manifest, "c" * 64)),
            mock.patch.object(R, "CurrentReviewLease", DummyLease),
            mock.patch.object(M, "_live_backend", return_value=backend),
        )
        with patches[0], patches[1], patches[2], patches[3]:
            payload = R.reconcile()
        return payload, backend

    def test_fresh_v2321_health_publishes_once_and_releases_only_active(self):
        candidate_path, candidate_bytes = M._candidate_guard(self.manifest)
        active_path, _active_bytes = M._active_guard(self.manifest)
        payload, backend = self._run()
        self.assertEqual(payload["decision"], R.DECISION)
        self.assertEqual(payload["rollbackOutcome"], "UNPROVED_EXTERNAL_CONTINUATION")
        self.assertFalse(payload["candidateReplay"])
        self.assertFalse(payload["rollbackReplay"])
        self.assertEqual(backend.observe_calls, 1)
        self.assertTrue((self.run_directory / "41-recovery-closed.json").is_file())
        self.assertFalse(active_path.exists())
        self.assertEqual(candidate_path.read_bytes(), candidate_bytes)

        second, second_backend = self._run()
        self.assertEqual(second, payload)
        self.assertEqual(second_backend.observe_calls, 0)
        self.assertEqual(M.recovery_decision(self.run_directory), "POSTROLLBACK_RECOVERY_RECONCILED_NO_REPLAY")

    def test_unhealthy_or_wrong_resident_never_publishes_or_releases(self):
        bad = M.Snapshot(**{**self.snapshot.__dict__, "healthy": False})
        active_path, _ = M._active_guard(self.manifest)
        with self.assertRaisesRegex(M.ContractError, "fresh V2321"):
            self._run(bad)
        self.assertTrue(active_path.is_file())
        self.assertFalse((self.run_directory / "41-recovery-closed.json").exists())

    def test_postpublication_crash_with_active_guard_parks_without_resume(self):
        self._run()
        M._publish_active_guard(self.manifest)
        with self.assertRaisesRegex(M.ContractError, "cleanup was interrupted; park"):
            self._run()
        active_path, _ = M._active_guard(self.manifest)
        self.assertTrue(active_path.is_file())

    def test_missing_active_guard_before_publication_is_not_forgiven(self):
        active_path, _ = M._active_guard(self.manifest)
        active_path.unlink()
        with self.assertRaises(M.ContractError):
            self._run()
        self.assertFalse((self.run_directory / "41-recovery-closed.json").exists())

    def test_guard_loss_during_observation_prevents_publication(self):
        for role in ("active", "candidate"):
            with self.subTest(role=role):
                if role == "active":
                    path, raw = M._active_guard(self.manifest)
                else:
                    path, raw = M._candidate_guard(self.manifest)
                with self.assertRaises(M.ContractError):
                    self._run(mutation=path.unlink)
                self.assertFalse(
                    (self.run_directory / "41-recovery-closed.json").exists()
                )
                path.write_bytes(raw)
                path.chmod(0o600)

    def test_incident_byte_or_terminal_drift_is_rejected(self):
        path = self.run_directory / "40-terminal.json"
        value = M.parse_canonical(path.read_bytes(), "terminal")
        value["payload"]["candidateReplay"] = True
        path.write_bytes(M.canonical_json(value))
        with self.assertRaisesRegex(M.ContractError, "record changed"):
            self._run()

    def test_payload_cannot_relabel_external_rollback_as_proved(self):
        payload = R._payload(self.snapshot, "c" * 64)
        payload["rollbackOutcome"] = "PROVED"
        with self.assertRaisesRegex(M.ContractError, "decision is invalid"):
            R._validate_payload(payload, self.manifest, "c" * 64)

    def test_published_snapshot_drift_is_rejected_by_its_canonical_digest(self):
        payload = R._payload(self.snapshot, "c" * 64)
        payload["recoveredSnapshot"]["bootId"] = (
            "11111111-2222-3333-4444-555555555555"
        )
        with self.assertRaisesRegex(M.ContractError, "snapshot digest mismatch"):
            R._validate_payload(payload, self.manifest, "c" * 64)


if __name__ == "__main__":
    unittest.main()
