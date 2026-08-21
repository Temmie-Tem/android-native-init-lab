from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "workspace/public/src/scripts/server-distro/a90_boot_only_f1_minimal_v1.py"
)
SPEC = importlib.util.spec_from_file_location("a90_boot_only_f1_minimal_v1", SOURCE)
assert SPEC and SPEC.loader
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


HEX_A = "a" * 64
HEX_B = "b" * 64
HEX_C = "c" * 64


class FakeBackend:
    def __init__(self, start: M.Snapshot, flashes=None, observations=None):
        self.preflights = [start]
        self.flashes = list(flashes or [])
        self.observations = list(observations or [])
        self.flash_calls = []

    def preflight(self, _manifest):
        if len(self.preflights) > 1:
            return self.preflights.pop(0)
        return self.preflights[0]

    def flash(self, artifact, *, rollback, timeout_sec):
        self.flash_calls.append((artifact["sha256"], rollback, timeout_sec))
        result = self.flashes.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    def observe(self, _expected, _fresh_state, *, require_fresh_state, timeout_sec):
        del require_fresh_state, timeout_sec
        result = self.observations.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


class MinimalF1Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.production_run_root = M.RUN_ROOT
        M.RUN_ROOT = self.root / "runs"
        M.RUN_ROOT.mkdir(mode=0o700)
        self.candidate = self.root / "candidate.img"
        self.rollback = self.root / "rollback.img"
        self.candidate.write_bytes(b"candidate")
        self.rollback.write_bytes(b"rollback")
        os.chmod(self.candidate, 0o600)
        os.chmod(self.rollback, 0o600)
        self.production_rollback = (
            M.V2321_ROLLBACK_PATH,
            M.V2321_ROLLBACK_SIZE,
            M.V2321_ROLLBACK_SHA256,
            M.V2321_ROLLBACK_VERSION,
            M.V2321_ROLLBACK_BUILD,
        )
        M.V2321_ROLLBACK_PATH = str(self.rollback)
        M.V2321_ROLLBACK_SIZE = len(b"rollback")
        M.V2321_ROLLBACK_SHA256 = M.sha256_bytes(b"rollback")
        M.V2321_ROLLBACK_VERSION = "old"
        M.V2321_ROLLBACK_BUILD = "old-build"
        recovery = {
            "profile": "A90_ATTENDED_PHYSICAL_RECOVERY_V1",
            "method": "NATIVE_TO_STABLE_ADB_BASELINE_SINGLE_NEW_RECOVERY_ARRIVAL_BOOT_READBACK_V1",
            "demonstrated": True,
        }
        recovery_identity = {"adbSerialSha256": HEX_C}
        hazard = {
            "id": "A90_H27_RKP_CFP_DISABLED_RESIDENT",
            "statementSha256": HEX_B,
            "accepted": True,
        }
        self.review = self.root / "qualification-review.json"
        self.review.write_bytes(M.canonical_json({
            "schema": M.QUALIFICATION_REVIEW_SCHEMA,
            "capability": M.CAPABILITY,
            "verdict": "PASS_GO",
            "scope": M.QUALIFICATION_REVIEW_SCOPE,
            "targetProfile": M.TARGET_PROFILE,
            "executionClosureSha256": M.execution_closure_sha256(),
            "candidateSha256": M.sha256_bytes(b"candidate"),
            "rollbackSha256": M.sha256_bytes(b"rollback"),
            "recovery": recovery,
            "hazard": hazard,
            "freshState": {
                "enablePath": "/cache/a90-auto-handoff-phase3-minimal-h27.enable",
                "latchPath": "/cache/a90-auto-handoff-phase3-minimal-h27.done",
            },
            "findings": {"high": [], "medium": [], "low": []},
            "contacts": {"device": 0, "dev": 0, "usb": 0, "network": 0,
                         "workspacePrivate": 0, "otherTargets": 0, "writes": 0},
            "reviewer": "independent-luna-max",
            "reviewDate": "2026-08-20",
            "liveAuthority": False,
        }))
        os.chmod(self.review, 0o600)
        self.manifest = {
            "schema": M.MANIFEST_SCHEMA,
            "capability": M.CAPABILITY,
            "targetProfile": M.TARGET_PROFILE,
            "partition": "boot",
            "runId": "a90-minimal-001",
            "expectedStart": {"version": "old", "build": "old-build"},
            "candidate": self._artifact(self.candidate, "new", "new-build"),
            "rollback": self._artifact(self.rollback, "old", "old-build"),
            "qualification": {
                "schema": M.QUALIFICATION_SCHEMA,
                "candidateSha256": M.sha256_bytes(b"candidate"),
                "rollbackSha256": M.sha256_bytes(b"rollback"),
                "recovery": recovery,
                "recoveryIdentity": recovery_identity,
                "hazard": hazard,
                "freshState": {
                    "enablePath": "/cache/a90-auto-handoff-phase3-minimal-h27.enable",
                    "latchPath": "/cache/a90-auto-handoff-phase3-minimal-h27.done",
                },
                "review": self._input(self.review),
            },
            "timeouts": {"flashSec": 60, "healthSec": 90},
        }
        self.raw = M.canonical_json(self.manifest)
        self.start = self._snapshot("old", "old-build", receipt=HEX_A)

    def tearDown(self):
        (
            M.V2321_ROLLBACK_PATH,
            M.V2321_ROLLBACK_SIZE,
            M.V2321_ROLLBACK_SHA256,
            M.V2321_ROLLBACK_VERSION,
            M.V2321_ROLLBACK_BUILD,
        ) = self.production_rollback
        M.RUN_ROOT = self.production_run_root
        self.temp.cleanup()

    def _artifact(self, path: Path, version: str, build: str):
        raw = path.read_bytes()
        return {
            "path": str(path),
            "size": len(raw),
            "sha256": M.sha256_bytes(raw),
            "version": version,
            "build": build,
        }

    def _input(self, path: Path):
        raw = path.read_bytes()
        return {"path": str(path), "size": len(raw), "sha256": M.sha256_bytes(raw)}

    def _snapshot(
        self,
        version: str,
        build: str,
        *,
        boot: str = "boot-one",
        receipt: str = HEX_B,
        healthy: bool = True,
        fresh_state_observed: bool = True,
    ):
        return M.Snapshot(
            target_evidence_sha256=HEX_C,
            boot_id=boot,
            version=version,
            build=build,
            healthy=healthy,
            recovery_available=True,
            recovery_evidence_sha256=self.manifest["qualification"]["review"]["sha256"],
            fresh_state_observed=fresh_state_observed,
            fresh_state_absent=fresh_state_observed,
            other_targets_untouched=True,
            receipt_sha256=receipt,
        )

    def _prepare(self, backend=None):
        backend = backend or FakeBackend(self.start)
        run = M.RUN_ROOT / self.manifest["runId"]
        token = M.prepare(self.raw, self.manifest, run, backend)
        return run, token

    def _uncertain_prefix(self, *, result_receipt=HEX_A, pending_receipt=HEX_A):
        run, _token = self._prepare()
        digest = M.sha256_bytes(self.raw)
        for name in (
            "10-approved.json",
            "20-candidate-intent.json",
            "21-candidate-launched.json",
        ):
            M.publish_record(run, name, M._record(M.RECORD_KINDS[name], digest, {}))
        effect = self._effect(
            rc=1,
            completed=False,
            receipt=result_receipt,
            outcome="BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
        )
        M.publish_record(
            run,
            "22-candidate-result.json",
            M._record("CANDIDATE_RESULT", digest, effect.payload()),
        )
        M.publish_record(
            run,
            "23-candidate-return-pending.json",
            M._record(
                "CANDIDATE_RETURN_PENDING",
                digest,
                {
                    "schema": "a90-f1-candidate-return-pending-v1",
                    "terminal": "RECOVERY_REQUIRED",
                    "reason": "CANDIDATE_RETURN_PENDING",
                    "candidateReplay": False,
                    "rollbackIntentPublished": False,
                    "effectOutcome": effect.outcome,
                    "effectReceiptSha256": pending_receipt,
                    "helperQuiescent": effect.quiescent,
                },
            ),
        )
        return run

    @staticmethod
    def _effect(
        *,
        completed=True,
        quiescent=True,
        rc=0,
        receipt=HEX_A,
        outcome="BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED",
    ):
        return M.EffectResult(rc, completed, quiescent, receipt, outcome)

    def test_manifest_accepts_only_exact_boot_contract(self):
        self.assertEqual(M.validate_manifest(self.manifest), self.manifest)
        for field, value in (("partition", "vendor_boot"), ("targetProfile", "OTHER")):
            bad = dict(self.manifest)
            bad[field] = value
            with self.assertRaises(M.ContractError):
                M.validate_manifest(bad)
        bad = json.loads(json.dumps(self.manifest))
        bad["rollback"]["version"] = "other"
        with self.assertRaisesRegex(M.ContractError, "exact V2321"):
            M.validate_manifest(bad)

    def test_manifest_rejects_bool_integer_and_extra_field(self):
        bad = json.loads(json.dumps(self.manifest))
        bad["candidate"]["size"] = True
        with self.assertRaises(M.ContractError):
            M.validate_manifest(bad)

    def test_manifest_rejects_unbound_recovery_or_unaccepted_hazard(self):
        bad = json.loads(json.dumps(self.manifest))
        bad["qualification"]["rollbackSha256"] = HEX_A
        with self.assertRaisesRegex(M.ContractError, "selected artifacts"):
            M.validate_manifest(bad)
        bad = json.loads(json.dumps(self.manifest))
        bad["qualification"]["hazard"]["accepted"] = False
        with self.assertRaisesRegex(M.ContractError, "hazard"):
            M.validate_manifest(bad)
        bad = json.loads(json.dumps(self.manifest))
        bad["qualification"]["recoveryIdentity"]["adbSerialSha256"] = "bad"
        with self.assertRaisesRegex(M.ContractError, "recovery serial"):
            M.validate_manifest(bad)
        for enable, latch in (
            (
                "/cache/a90-auto-handoff-phase3-minimal-h27.done",
                "/cache/a90-auto-handoff-phase3-minimal-h27.enable",
            ),
            (
                "/cache/a90-auto-handoff-phase3-minimal-h27.enable",
                "/cache/a90-auto-handoff-phase3-minimal-h28.done",
            ),
        ):
            bad = json.loads(json.dumps(self.manifest))
            bad["qualification"]["freshState"] = {
                "enablePath": enable, "latchPath": latch,
            }
            with self.assertRaisesRegex(M.ContractError, "enable/latch generation"):
                M.validate_manifest(bad)
        bad = dict(self.manifest, command="flash")
        with self.assertRaises(M.ContractError):
            M.validate_manifest(bad)

    def test_canonical_parser_rejects_duplicate_and_trailing_newline(self):
        with self.assertRaises(M.ContractError):
            M.parse_canonical(b'{"a":1,"a":1}', "duplicate")
        with self.assertRaises(M.ContractError):
            M.parse_canonical(b'{"a":1}\n', "newline")

    def test_artifact_binding_rejects_symlink(self):
        link = self.root / "link.img"
        link.symlink_to(self.candidate)
        value = self._artifact(self.candidate, "new", "new-build")
        value["path"] = str(link)
        with self.assertRaises(M.ContractError):
            M.BoundArtifact.open(value, "candidate")

    def test_artifact_binding_rejects_fifo_before_open(self):
        fifo = self.root / "artifact.fifo"
        os.mkfifo(fifo, 0o600)
        value = {
            "path": str(fifo), "size": 1, "sha256": HEX_A,
            "version": "x", "build": "y",
        }
        for role in ("candidate", "rollback"):
            with self.subTest(role=role), self.assertRaisesRegex(
                M.ContractError, "path identity"
            ):
                M.BoundArtifact.open(value, role)

    def test_checkpoint_rejects_size_drift_before_hash(self):
        bound = M.BoundArtifact.open(self.manifest["candidate"], "candidate")
        try:
            with self.candidate.open("ab") as stream:
                stream.write(b"extended")
            with mock.patch.object(
                M, "_hash_fd", side_effect=AssertionError("must not hash")
            ):
                with self.assertRaisesRegex(M.ContractError, "size changed"):
                    bound.checkpoint()
        finally:
            bound.close()

    def test_prepare_binds_target_artifacts_and_approval(self):
        run, token = self._prepare()
        records = M.read_records(run)
        prepared = records["00-prepared.json"]["payload"]
        self.assertEqual(prepared["candidate"]["sha256"], self.manifest["candidate"]["sha256"])
        self.assertEqual(prepared["snapshot"]["bootId"], "boot-one")
        self.assertTrue(token.startswith(M.APPROVAL_PREFIX))
        self.assertEqual(M.recovery_decision(run), "PRE_EFFECT_NO_DEVICE_EFFECT")
        self.assertTrue((M.RUN_ROOT / "active-run.guard").is_file())

    def test_prepare_preflight_failure_leaves_no_journal_directory(self):
        run = M.RUN_ROOT / self.manifest["runId"]
        with self.assertRaisesRegex(M.ContractError, "not exact"):
            M.prepare(
                self.raw,
                self.manifest,
                run,
                FakeBackend(self._snapshot("wrong", "wrong", healthy=False)),
            )
        self.assertFalse(run.exists())
        self.assertFalse((M.RUN_ROOT / "active-run.guard").exists())

    def test_journal_growth_between_lstat_and_open_is_rejected(self):
        run, _token = self._prepare()
        record = run / "00-prepared.json"
        original_open = M.os.open
        changed = False

        def grow_before_open(path, flags, *args):
            nonlocal changed
            if Path(path) == record and not changed:
                changed = True
                with record.open("ab") as stream:
                    stream.write(b"x")
            return original_open(path, flags, *args)

        with mock.patch.object(M.os, "open", side_effect=grow_before_open):
            with self.assertRaisesRegex(M.ContractError, "changed before read"):
                M.read_records(run)

    def test_dangling_allowlisted_journal_entry_is_not_treated_absent(self):
        run, _token = self._prepare()
        (run / "10-approved.json").symlink_to(run / "missing-target")
        with self.assertRaisesRegex(M.ContractError, "path identity"):
            M.read_records(run)

    def test_same_candidate_cannot_be_prepared_in_second_run(self):
        self._prepare()
        changed = json.loads(json.dumps(self.manifest))
        changed["runId"] = "a90-minimal-002"
        with self.assertRaisesRegex(M.ContractError, "transaction is active"):
            M.prepare(
                M.canonical_json(changed),
                changed,
                M.RUN_ROOT / changed["runId"],
                FakeBackend(self.start),
            )
        self.assertFalse((M.RUN_ROOT / changed["runId"]).exists())

    def test_different_candidate_cannot_overlap_active_run(self):
        self._prepare()
        other = json.loads(json.dumps(self.manifest))
        other["candidate"]["sha256"] = HEX_A
        other["qualification"]["candidateSha256"] = HEX_A
        with self.assertRaisesRegex(M.ContractError, "transaction is active"):
            M._publish_active_guard(other)

    def test_prepare_acquires_active_before_consuming_candidate(self):
        order = []
        run = M.RUN_ROOT / self.manifest["runId"]
        with mock.patch.object(
            M, "_publish_active_guard", side_effect=lambda _manifest: order.append("active")
        ), mock.patch.object(
            M, "_publish_candidate_guard", side_effect=lambda _manifest: order.append("candidate")
        ):
            M.prepare(self.raw, self.manifest, run, FakeBackend(self.start))
        self.assertEqual(order, ["active", "candidate"])

    def test_pre_effect_candidate_guard_failure_releases_new_active_guard(self):
        run = M.RUN_ROOT / self.manifest["runId"]
        with mock.patch.object(
            M,
            "_publish_candidate_guard",
            side_effect=M.ContractError("candidate guard rejected"),
        ):
            with self.assertRaisesRegex(M.ContractError, "candidate guard rejected"):
                M.prepare(self.raw, self.manifest, run, FakeBackend(self.start))
        self.assertFalse((M.RUN_ROOT / "active-run.guard").exists())

    def test_manifest_bytes_cannot_authorize_a_different_object(self):
        changed = json.loads(json.dumps(self.manifest))
        changed["candidate"]["version"] = "substituted"
        with self.assertRaisesRegex(M.ContractError, "execution object differ"):
            M.prepare(
                self.raw,
                changed,
                M.RUN_ROOT / changed["runId"],
                FakeBackend(self.start),
            )

    def test_success_flashes_candidate_once_and_accepts_fresh_receipt(self):
        run, token = self._prepare()
        backend = FakeBackend(
            self._snapshot("old", "old-build", receipt=HEX_B),
            flashes=[self._effect()],
            observations=[self._snapshot("new", "new-build")],
        )
        result = M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(result["terminal"], "PASS_A90_RESIDENT_INSTALLED")
        self.assertTrue(result["qualification"]["hazardAccepted"])
        self.assertEqual(
            result["qualification"]["recoveryEvidenceSha256"],
            self.manifest["qualification"]["review"]["sha256"],
        )
        self.assertEqual(len(backend.flash_calls), 1)
        self.assertFalse(backend.flash_calls[0][1])
        self.assertEqual(M.recovery_decision(run), "TERMINAL_COMPLETE")
        self.assertFalse((M.RUN_ROOT / "active-run.guard").exists())

    def test_exact_system_return_uncertainty_parks_before_rollback(self):
        run, token = self._prepare()
        backend = FakeBackend(
            self.start,
            flashes=[
                self._effect(
                    rc=1,
                    completed=False,
                    outcome="BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
                )
            ],
        )
        result = M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(result["reason"], "CANDIDATE_RETURN_PENDING")
        self.assertEqual(len(backend.flash_calls), 1)
        self.assertFalse(backend.flash_calls[0][1])
        self.assertEqual(
            M.recovery_decision(run), "CANDIDATE_RETURN_PENDING"
        )
        self.assertIn("23-candidate-return-pending.json", M.read_records(run))
        self.assertNotIn("30-rollback-intent.json", M.read_records(run))
        self.assertTrue((M.RUN_ROOT / "active-run.guard").is_file())

    def test_healthy_candidate_without_confirmed_effect_receipt_never_passes(self):
        run, token = self._prepare()
        backend = FakeBackend(
            self.start,
            flashes=[
                self._effect(outcome="UNCLASSIFIED"),
                self._effect(
                    outcome="BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_CONFIRMED"
                ),
            ],
            observations=[
                self._snapshot("new", "new-build"),
                self._snapshot("old", "old-build"),
            ],
        )
        result = M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(result["terminal"], "NO_PROOF_ROLLED_BACK")
        self.assertEqual([call[1] for call in backend.flash_calls], [False, True])

    def test_healthy_rollback_without_confirmed_effect_receipt_stays_recovery_required(self):
        run, token = self._prepare()
        backend = FakeBackend(
            self.start,
            flashes=[
                self._effect(rc=1, completed=False, outcome="UNCLASSIFIED"),
                self._effect(outcome="UNCLASSIFIED"),
            ],
            observations=[
                self._snapshot("old", "old-build", healthy=False),
                self._snapshot("old", "old-build"),
            ],
        )
        result = M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertEqual([call[1] for call in backend.flash_calls], [False, True])

    def test_wrong_approval_causes_no_effect(self):
        run, _token = self._prepare()
        backend = FakeBackend(self.start)
        with self.assertRaises(M.ContractError):
            M.execute(self.raw, self.manifest, run, "wrong", backend)
        self.assertEqual(backend.flash_calls, [])
        self.assertEqual(set(M.read_records(run)), {"00-prepared.json"})

    def test_changed_boot_causes_no_effect(self):
        run, token = self._prepare()
        backend = FakeBackend(self._snapshot("old", "old-build", boot="boot-two"))
        with self.assertRaises(M.ContractError):
            M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(backend.flash_calls, [])

    def test_changed_candidate_causes_no_effect(self):
        run, token = self._prepare()
        self.candidate.write_bytes(b"substitute")
        with self.assertRaises(M.ContractError):
            M.execute(self.raw, self.manifest, run, token, FakeBackend(self.start))

    def test_changed_qualification_input_causes_no_effect(self):
        run, token = self._prepare()
        self.review.write_bytes(b'{"verdict":"PASS_GO"}')
        with self.assertRaisesRegex(M.ContractError, "qualification review"):
            M.execute(self.raw, self.manifest, run, token, FakeBackend(self.start))

    def test_review_changed_during_preflight_is_rejected_before_effect(self):
        run, token = self._prepare()
        review = self.review

        class MutatingBackend(FakeBackend):
            def preflight(inner_self, manifest):
                review.write_bytes(b'{"verdict":"substituted"}')
                return super().preflight(manifest)

        backend = MutatingBackend(self.start)
        with self.assertRaisesRegex(M.ContractError, "qualification review"):
            M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(backend.flash_calls, [])

    def test_candidate_guard_lost_during_preflight_stops_before_intent(self):
        run, token = self._prepare()
        guard, _ = M._candidate_guard(self.manifest)

        class MutatingBackend(FakeBackend):
            def preflight(inner_self, manifest):
                guard.unlink()
                return super().preflight(manifest)

        backend = MutatingBackend(self.start)
        with self.assertRaises(M.ContractError):
            M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(backend.flash_calls, [])
        self.assertNotIn("20-candidate-intent.json", M.read_records(run))
        self.assertTrue((M.RUN_ROOT / "active-run.guard").is_file())

    def test_candidate_guard_lost_after_launch_record_stops_before_flash(self):
        run, token = self._prepare()
        guard, _ = M._candidate_guard(self.manifest)
        backend = FakeBackend(self.start)
        publish = M.publish_record

        def mutate_after_launch(directory, name, value):
            publish(directory, name, value)
            if name == "21-candidate-launched.json":
                guard.unlink()

        with mock.patch.object(M, "publish_record", side_effect=mutate_after_launch):
            with self.assertRaises(M.ContractError):
                M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(backend.flash_calls, [])
        self.assertIn("21-candidate-launched.json", M.read_records(run))
        self.assertTrue((M.RUN_ROOT / "active-run.guard").is_file())

    def test_candidate_guard_lost_during_health_blocks_active_release(self):
        run, token = self._prepare()
        guard, _ = M._candidate_guard(self.manifest)

        class MutatingBackend(FakeBackend):
            def observe(inner_self, *args, **kwargs):
                guard.unlink()
                return super().observe(*args, **kwargs)

        backend = MutatingBackend(
            self.start,
            flashes=[self._effect()],
            observations=[self._snapshot("new", "new-build")],
        )
        with self.assertRaises(M.ContractError):
            M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(len(backend.flash_calls), 1)
        self.assertNotIn("40-terminal.json", M.read_records(run))
        self.assertTrue((M.RUN_ROOT / "active-run.guard").is_file())

    def test_active_guard_lost_during_candidate_health_stops_before_rollback(self):
        run, token = self._prepare()
        active, _ = M._active_guard(self.manifest)

        class MutatingBackend(FakeBackend):
            def observe(inner_self, *args, **kwargs):
                active.unlink()
                return super().observe(*args, **kwargs)

        backend = MutatingBackend(
            self.start,
            flashes=[self._effect(rc=1, completed=False)],
            observations=[self._snapshot("old", "old-build", healthy=False)],
        )
        with self.assertRaises(M.ContractError):
            M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(len(backend.flash_calls), 1)
        self.assertNotIn("30-rollback-intent.json", M.read_records(run))

    def test_active_guard_lost_after_rollback_launch_stops_before_dispatch(self):
        run, token = self._prepare()
        active, _ = M._active_guard(self.manifest)
        backend = FakeBackend(
            self.start,
            flashes=[
                self._effect(rc=1, completed=False),
                self._effect(),
            ],
            observations=[self._snapshot("old", "old-build", healthy=False)],
        )
        publish = M.publish_record

        def mutate_after_rollback_launch(directory, name, value):
            publish(directory, name, value)
            if name == "31-rollback-launched.json":
                active.unlink()

        with mock.patch.object(
            M, "publish_record", side_effect=mutate_after_rollback_launch
        ):
            with self.assertRaises(M.ContractError):
                M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(len(backend.flash_calls), 1)
        self.assertIn("31-rollback-launched.json", M.read_records(run))

    def test_active_guard_lost_during_candidate_effect_blocks_recovery_terminal(self):
        run, token = self._prepare()
        active, _ = M._active_guard(self.manifest)

        class MutatingBackend(FakeBackend):
            def flash(inner_self, *args, **kwargs):
                result = super().flash(*args, **kwargs)
                active.unlink()
                return result

        backend = MutatingBackend(
            self.start, flashes=[self._effect(quiescent=False)]
        )
        with self.assertRaises(M.ContractError):
            M.execute(self.raw, self.manifest, run, token, backend)
        self.assertNotIn("40-terminal.json", M.read_records(run))

    def test_active_guard_lost_during_rollback_effect_blocks_recovery_terminal(self):
        run, token = self._prepare()
        active, _ = M._active_guard(self.manifest)

        class MutatingBackend(FakeBackend):
            def flash(inner_self, *args, **kwargs):
                result = super().flash(*args, **kwargs)
                if len(inner_self.flash_calls) == 2:
                    active.unlink()
                return result

        backend = MutatingBackend(
            self.start,
            flashes=[
                self._effect(rc=1, completed=False),
                self._effect(quiescent=False),
            ],
            observations=[self._snapshot("old", "old-build", healthy=False)],
        )
        with self.assertRaises(M.ContractError):
            M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(len(backend.flash_calls), 2)
        self.assertNotIn("40-terminal.json", M.read_records(run))

    def test_active_guard_lost_during_final_health_blocks_healthy_terminal(self):
        run, token = self._prepare()
        active, _ = M._active_guard(self.manifest)

        class MutatingBackend(FakeBackend):
            def observe(inner_self, *args, **kwargs):
                result = super().observe(*args, **kwargs)
                if not inner_self.observations:
                    active.unlink()
                return result

        backend = MutatingBackend(
            self.start,
            flashes=[self._effect(rc=1, completed=False), self._effect()],
            observations=[
                self._snapshot("old", "old-build", healthy=False),
                self._snapshot("old", "old-build", fresh_state_observed=False),
            ],
        )
        with self.assertRaises(M.ContractError):
            M.execute(self.raw, self.manifest, run, token, backend)
        self.assertNotIn("40-terminal.json", M.read_records(run))

    def test_fabricated_or_no_go_review_is_rejected_before_prepared(self):
        for value in ({"verdict": "PASS_GO"}, {
            **M.parse_canonical(self.review.read_bytes(), "review"),
            "verdict": "NO_GO",
        }):
            with self.subTest(value=value):
                self.review.write_bytes(M.canonical_json(value))
                changed = json.loads(json.dumps(self.manifest))
                changed["qualification"]["review"] = self._input(self.review)
                with self.assertRaises(M.ContractError):
                    M.prepare(
                        M.canonical_json(changed),
                        changed,
                        M.RUN_ROOT / changed["runId"],
                        FakeBackend(self.start),
                    )

    def test_review_scope_is_candidate_neutral_and_legacy_h27_is_exact_only(self):
        self.assertTrue(M._review_scope_is_allowed(
            {"scope": M.QUALIFICATION_REVIEW_SCOPE}, self.manifest
        ))
        self.assertFalse(M._review_scope_is_allowed(
            {"scope": M.LEGACY_H27_REVIEW_SCOPE}, self.manifest
        ))

        legacy = json.loads(json.dumps(self.manifest))
        legacy["candidate"]["sha256"] = M.LEGACY_H27_CANDIDATE_SHA256
        legacy["qualification"]["hazard"] = dict(M.LEGACY_H27_HAZARD)
        legacy["qualification"]["freshState"] = dict(M.LEGACY_H27_FRESH_STATE)
        self.assertTrue(M._review_scope_is_allowed(
            {"scope": M.LEGACY_H27_REVIEW_SCOPE}, legacy
        ))
        for mutation in ("candidate", "hazard", "fresh-state"):
            changed = json.loads(json.dumps(legacy))
            if mutation == "candidate":
                changed["candidate"]["sha256"] = HEX_A
            elif mutation == "hazard":
                changed["qualification"]["hazard"]["id"] = "substituted"
            else:
                changed["qualification"]["freshState"]["enablePath"] = (
                    "/cache/a90-auto-handoff-phase3-minimal-h28.enable"
                )
            with self.subTest(mutation=mutation):
                self.assertFalse(M._review_scope_is_allowed(
                    {"scope": M.LEGACY_H27_REVIEW_SCOPE}, changed
                ))

    def test_review_cannot_substitute_fresh_state_generation(self):
        value = M.parse_canonical(self.review.read_bytes(), "review")
        value["freshState"]["latchPath"] = (
            "/cache/a90-auto-handoff-phase3-minimal-h28.done"
        )
        self.review.write_bytes(M.canonical_json(value))
        changed = json.loads(json.dumps(self.manifest))
        changed["qualification"]["review"] = self._input(self.review)
        with self.assertRaisesRegex(M.ContractError, "bind fresh state"):
            M.prepare(
                M.canonical_json(changed),
                changed,
                M.RUN_ROOT / changed["runId"],
                FakeBackend(self.start),
            )

    def test_fifo_review_is_rejected_before_open_or_read(self):
        fifo = self.root / "review.fifo"
        os.mkfifo(fifo, 0o600)
        changed = json.loads(json.dumps(self.manifest))
        changed["qualification"]["review"] = {
            "path": str(fifo), "size": 1, "sha256": HEX_A,
        }
        with self.assertRaisesRegex(M.ContractError, "path identity"):
            M.prepare(
                M.canonical_json(changed),
                changed,
                M.RUN_ROOT / changed["runId"],
                FakeBackend(self.start),
            )

    def test_unhealthy_candidate_rolls_back_once(self):
        run, token = self._prepare()
        backend = FakeBackend(
            self.start,
            flashes=[self._effect(rc=1, completed=False), self._effect()],
            observations=[
                self._snapshot("old", "old-build", healthy=False),
                self._snapshot("old", "old-build", fresh_state_observed=False),
            ],
        )
        result = M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(result["terminal"], "NO_PROOF_ROLLED_BACK")
        self.assertEqual([call[1] for call in backend.flash_calls], [False, True])
        self.assertFalse((M.RUN_ROOT / "active-run.guard").exists())

    def test_observer_failure_rolls_back_instead_of_claiming_success(self):
        run, token = self._prepare()
        backend = FakeBackend(
            self.start,
            flashes=[self._effect(), self._effect()],
            observations=[
                RuntimeError("observer lost"),
                self._snapshot("old", "old-build", fresh_state_observed=False),
            ],
        )
        result = M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(result["terminal"], "NO_PROOF_ROLLED_BACK")
        self.assertEqual([call[1] for call in backend.flash_calls], [False, True])

    def test_unproved_rollback_requires_recovery(self):
        run, token = self._prepare()
        backend = FakeBackend(
            self.start,
            flashes=[self._effect(rc=1, completed=False), self._effect(rc=1, completed=False)],
            observations=[
                self._snapshot("old", "old-build", healthy=False),
                self._snapshot(
                    "old", "old-build", healthy=False, fresh_state_observed=False
                ),
            ],
        )
        result = M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertTrue((M.RUN_ROOT / "active-run.guard").is_file())

    def test_nonquiescent_candidate_does_not_overlap_rollback(self):
        run, token = self._prepare()
        backend = FakeBackend(self.start, flashes=[self._effect(quiescent=False)])
        result = M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertEqual(len(backend.flash_calls), 1)
        self.assertTrue((M.RUN_ROOT / "active-run.guard").is_file())

    def test_second_execute_cannot_replay_candidate(self):
        run, token = self._prepare()
        backend = FakeBackend(
            self.start,
            flashes=[self._effect()],
            observations=[self._snapshot("new", "new-build")],
        )
        M.execute(self.raw, self.manifest, run, token, backend)
        with self.assertRaises(M.ContractError):
            M.execute(self.raw, self.manifest, run, token, backend)

    def test_flash_exception_leaves_candidate_consumed(self):
        run, token = self._prepare()
        backend = FakeBackend(self.start, flashes=[RuntimeError("transport lost")])
        with self.assertRaises(RuntimeError):
            M.execute(self.raw, self.manifest, run, token, backend)
        self.assertEqual(M.recovery_decision(run), "CANDIDATE_CONSUMED_ROLLBACK_ONLY")

    def test_recovery_decisions_cover_rollback_prefixes(self):
        run, _token = self._prepare()
        digest = M.sha256_bytes(self.raw)
        for name in (
            "10-approved.json",
            "20-candidate-intent.json",
            "21-candidate-launched.json",
            "22-candidate-result.json",
            "30-rollback-intent.json",
        ):
            M.publish_record(run, name, M._record(M.RECORD_KINDS[name], digest, {}))
        self.assertEqual(M.recovery_decision(run), "SAME_ROLLBACK_MAY_LAUNCH_ONCE")
        M.publish_record(
            run,
            "31-rollback-launched.json",
            M._record("ROLLBACK_LAUNCHED", digest, {}),
        )
        self.assertEqual(M.recovery_decision(run), "PARK_ROLLBACK_NO_REPLAY")

    def test_crash_after_exact_uncertain_result_before_pending_record_never_allows_rollback(self):
        run, _token = self._prepare()
        digest = M.sha256_bytes(self.raw)
        for name in (
            "10-approved.json",
            "20-candidate-intent.json",
            "21-candidate-launched.json",
        ):
            M.publish_record(run, name, M._record(M.RECORD_KINDS[name], digest, {}))
        effect = self._effect(
            rc=1,
            completed=False,
            outcome="BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
        )
        M.publish_record(
            run,
            "22-candidate-result.json",
            M._record("CANDIDATE_RESULT", digest, effect.payload()),
        )
        self.assertEqual(
            M.recovery_decision(run),
            "CANDIDATE_RETURN_PENDING_RECORD_MISSING_NO_ROLLBACK",
        )
        self.assertNotIn("30-rollback-intent.json", M.read_records(run))

    def test_substituted_or_malformed_result_is_not_upgraded_to_pending(self):
        for mutation in ("outcome", "missing"):
            with self.subTest(mutation=mutation):
                run = M.RUN_ROOT / self.manifest["runId"]
                try:
                    run, _token = self._prepare()
                    digest = M.sha256_bytes(self.raw)
                    for name in (
                        "10-approved.json",
                        "20-candidate-intent.json",
                        "21-candidate-launched.json",
                    ):
                        M.publish_record(
                            run, name, M._record(M.RECORD_KINDS[name], digest, {})
                        )
                    payload = self._effect(
                        rc=1,
                        completed=False,
                        outcome="BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
                    ).payload()
                    if mutation == "outcome":
                        payload["outcome"] = "UNCLASSIFIED"
                    else:
                        del payload["receiptSha256"]
                    M.publish_record(
                        run,
                        "22-candidate-result.json",
                        M._record("CANDIDATE_RESULT", digest, payload),
                    )
                    self.assertEqual(
                        M.recovery_decision(run), "CANDIDATE_CONSUMED_ROLLBACK_ONLY"
                    )
                finally:
                    active, _ = M._active_guard(self.manifest)
                    candidate, _ = M._candidate_guard(self.manifest)
                    if active.exists():
                        M._release_active_guard(self.manifest)
                    if candidate.exists():
                        candidate.unlink()
                    if run.exists():
                        for entry in run.iterdir():
                            entry.unlink()
                        run.rmdir()

    def test_exact_result_with_malformed_pending_record_stays_no_rollback(self):
        run, _token = self._prepare()
        digest = M.sha256_bytes(self.raw)
        for name in (
            "10-approved.json",
            "20-candidate-intent.json",
            "21-candidate-launched.json",
        ):
            M.publish_record(run, name, M._record(M.RECORD_KINDS[name], digest, {}))
        effect = self._effect(
            rc=1,
            completed=False,
            outcome="BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
        )
        M.publish_record(
            run,
            "22-candidate-result.json",
            M._record("CANDIDATE_RESULT", digest, effect.payload()),
        )
        M.publish_record(
            run,
            "23-candidate-return-pending.json",
            M._record(
                "CANDIDATE_RETURN_PENDING",
                digest,
                {"reason": "malformed"},
            ),
        )
        self.assertEqual(
            M.recovery_decision(run),
            "CANDIDATE_RETURN_PENDING_RECORD_INVALID_NO_ROLLBACK",
        )
        self.assertNotIn("30-rollback-intent.json", M.read_records(run))

    def test_pending_receipt_mismatch_with_candidate_result_is_invalid_no_rollback(self):
        run = self._uncertain_prefix(result_receipt=HEX_A, pending_receipt=HEX_B)
        self.assertEqual(
            M.recovery_decision(run),
            "CANDIDATE_RETURN_PENDING_RECORD_INVALID_NO_ROLLBACK",
        )
        self.assertNotIn("30-rollback-intent.json", M.read_records(run))

    def test_candidate_result_receipt_mutation_after_pending_is_invalid_no_rollback(self):
        run = self._uncertain_prefix(result_receipt=HEX_A, pending_receipt=HEX_A)
        self.assertEqual(M.recovery_decision(run), "CANDIDATE_RETURN_PENDING")
        result_path = run / "22-candidate-result.json"
        result = M.parse_canonical(result_path.read_bytes(), "candidate result")
        result["payload"]["receiptSha256"] = HEX_B
        result_path.unlink()
        M.publish_record(run, "22-candidate-result.json", result)
        self.assertEqual(
            M.recovery_decision(run),
            "CANDIDATE_RETURN_PENDING_RECORD_INVALID_NO_ROLLBACK",
        )
        self.assertNotIn("30-rollback-intent.json", M.read_records(run))

    def test_journal_rejects_gap_wrong_kind_and_mixed_manifest(self):
        digest = M.sha256_bytes(self.raw)
        for mutation in ("gap", "kind", "manifest"):
            run = self.root / mutation
            run.mkdir(mode=0o700)
            M.publish_record(run, "00-prepared.json", M._record("PREPARED", digest, {}))
            if mutation == "gap":
                M.publish_record(run, "20-candidate-intent.json", M._record("CANDIDATE_INTENT", digest, {}))
            else:
                kind = "WRONG" if mutation == "kind" else "APPROVED"
                sha = HEX_A if mutation == "manifest" else digest
                M.publish_record(run, "10-approved.json", M._record(kind, sha, {}))
            with self.assertRaises(M.ContractError, msg=mutation):
                M.read_records(run)

    def test_live_cli_has_only_derived_prepare_and_approved_execute(self):
        self.assertTrue(M.LIVE_EXECUTION_ENABLED)
        prepared = M.parser().parse_args(["prepare", "/tmp/manifest.json"])
        self.assertEqual(prepared.action, "prepare")
        with self.assertRaises(SystemExit):
            M.parser().parse_args(["execute", "/tmp/manifest.json"])
        executed = M.parser().parse_args(
            ["execute", "/tmp/manifest.json", "--approval", "exact"]
        )
        self.assertEqual(executed.approval, "exact")

    def test_live_backend_preserves_old_logs_and_uses_next_ordinal(self):
        first = M._live_backend(self.manifest, "execute")
        second = M._live_backend(self.manifest, "execute")
        self.assertNotEqual(first.runner.log_directory, second.runner.log_directory)
        self.assertEqual(first.runner.log_directory.name, "a90-minimal-001-execute-1-logs")
        self.assertEqual(second.runner.log_directory.name, "a90-minimal-001-execute-2-logs")

    def test_live_backend_adapter_import_does_not_depend_on_sys_path(self):
        adapter_name = "a90_boot_only_f1_adapter_v1"
        old_adapter = sys.modules.pop(adapter_name, None)
        module_dir = str(SOURCE.parent)
        old_path = list(sys.path)
        sys.path[:] = [entry for entry in sys.path if entry != module_dir]
        try:
            backend = M._live_backend(self.manifest, "prepare")
            self.assertEqual(
                backend.runner.log_directory.name,
                "a90-minimal-001-prepare-1-logs",
            )
        finally:
            sys.path[:] = old_path
            sys.modules.pop(adapter_name, None)
            if old_adapter is not None:
                sys.modules[adapter_name] = old_adapter

    def test_live_backend_rejects_foreign_module_aliases(self):
        adapter_name = "a90_boot_only_f1_adapter_v1"
        old_adapter = sys.modules.get(adapter_name)
        sys.modules[adapter_name] = types.SimpleNamespace(__file__="/tmp/foreign.py")
        try:
            with self.assertRaisesRegex(M.ContractError, "adapter identity"):
                M._live_backend(self.manifest, "execute")
        finally:
            if old_adapter is None:
                sys.modules.pop(adapter_name, None)
            else:
                sys.modules[adapter_name] = old_adapter

        canonical = "a90_boot_only_f1_minimal_v1"
        old_minimal = sys.modules[canonical]
        sys.modules[canonical] = types.SimpleNamespace(__file__="/tmp/stale.py")
        try:
            with self.assertRaisesRegex(M.ContractError, "module identity"):
                M._live_backend(self.manifest, "execute")
        finally:
            sys.modules[canonical] = old_minimal


class MinimalSurfaceTest(unittest.TestCase):
    def test_exact_a90_twrp_bcb_exception_is_narrow_and_bound(self):
        digest = "3c3058563bbe775505fb5c0be8b94ae4a5e44787b5971ca17fd49e599ae7dd07"
        common = (ROOT / "AGENTS.md").read_text()
        target = (ROOT / "docs/operations/targets/A90_TARGET_CONTRACT.md").read_text()
        design = (ROOT / "docs/plans/A90_BOOT_ONLY_F1_MINIMAL_V1_DESIGN_2026-08-20.md").read_text()
        self.assertIn("first 256 bytes of `misc` BCB", common)
        self.assertIn("accepts no caller path, offset, count, command", common)
        for text in (target, design):
            self.assertIn("/system/bin/rebootsystem.sh", text)
            self.assertIn(digest, text)
            self.assertIn("3.7.0_12-0", text)

    def test_minimal_source_and_test_surface_stays_bounded(self):
        design = ROOT / "docs/plans/A90_BOOT_ONLY_F1_MINIMAL_V1_DESIGN_2026-08-20.md"
        self.assertLessEqual(len(SOURCE.read_text().splitlines()), 1560)
        self.assertLessEqual(len(Path(__file__).read_text().splitlines()), 1150)
        self.assertLessEqual(len(design.read_text().splitlines()), 250)

    def test_retired_owner_runtime_is_not_an_active_dependency(self):
        retired = (
            "a90_boot_only_f1_owner_v1.py",
            "a90_boot_only_f1_contract_v1.py",
            "a90_boot_only_f1_runtime_v1.py",
            "a90_boot_only_f1_observer_v1.py",
            "a90_boot_only_f1_source_package_v1.py",
            "a90_boot_only_f1_runtime_qualification_v1.json",
            "a90_boot_only_f1_command_bootstrap.py",
            "a90_boot_only_f1_helper_bootstrap.py",
        )
        active_files = (
            SOURCE,
            ROOT / "docs/plans/A90_BOOT_ONLY_F1_MINIMAL_V1_DESIGN_2026-08-20.md",
        )
        active_text = "\n".join(path.read_text() for path in active_files)
        for name in retired:
            self.assertNotIn(name, active_text)


if __name__ == "__main__":
    unittest.main()
