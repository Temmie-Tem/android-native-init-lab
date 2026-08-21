"""Host-only tests for the candidate-neutral A90 continuation state machine."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

from tests.test_a90_boot_only_f1_minimal_v1 import FakeBackend, MinimalF1Test, M


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "workspace/public/src/scripts/server-distro/a90_f1_candidate_return_continuation_v1.py"
)
SPEC = importlib.util.spec_from_file_location(
    "a90_f1_candidate_return_continuation_v1", SOURCE
)
assert SPEC and SPEC.loader
C = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = C
SPEC.loader.exec_module(C)


class ReturnBackend:
    def __init__(self, *, inspect=None, after=None, flashes=None, observations=None):
        self.inspect_value = inspect
        self.after_value = after
        self.flashes = list(flashes or [])
        self.observations = list(observations or [])
        self.calls = []

    def inspect_pending(self, _manifest):
        self.calls.append("inspect")
        if isinstance(self.inspect_value, BaseException):
            raise self.inspect_value
        return self.inspect_value

    def observe_after_continuation(self, _manifest, *, physical_action_confirmed):
        self.calls.append(("observe-after", physical_action_confirmed))
        if isinstance(self.after_value, BaseException):
            raise self.after_value
        return self.after_value

    def flash(self, artifact, *, rollback, timeout_sec):
        self.calls.append(("flash", artifact["sha256"], rollback, timeout_sec))
        result = self.flashes.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result

    def observe(self, _expected, _fresh_state, *, require_fresh_state, timeout_sec):
        self.calls.append(("observe", require_fresh_state, timeout_sec))
        result = self.observations.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


class CandidateReturnContinuationTest(MinimalF1Test):
    def setUp(self):
        super().setUp()
        self.manifest_path = self.root / "manifest.json"
        self.manifest_path.write_bytes(self.raw)
        os.chmod(self.manifest_path, 0o600)
        self.review_path = self.root / "continuation-review.json"
        self._old_review_path = C.CONTINUATION_REVIEW_PATH
        C.CONTINUATION_REVIEW_PATH = self.review_path
        self.review_path.write_bytes(
            M.canonical_json(
                {
                    "schema": C.REVIEW_SCHEMA,
                    "capability": C.CAPABILITY,
                    "verdict": "PASS_GO",
                    "scope": C.REVIEW_SCOPE,
                    "targetProfile": M.TARGET_PROFILE,
                    "executionClosureSha256": C.execution_closure_sha256(),
                    "findings": {"high": [], "medium": [], "low": []},
                    "contacts": {
                        "device": 0,
                        "dev": 0,
                        "usb": 0,
                        "network": 0,
                        "workspacePrivate": 0,
                        "otherTargets": 0,
                        "writes": 0,
                    },
                    "reviewer": "independent-luna-max",
                    "reviewDate": "2026-08-21",
                    "liveAuthority": False,
                }
            )
        )
        os.chmod(self.review_path, 0o600)

    def tearDown(self):
        C.CONTINUATION_REVIEW_PATH = self._old_review_path
        super().tearDown()

    def _snapshot_payload(self, version="new", build="new-build"):
        return self._snapshot(version, build).payload()

    def _uncertain_run(self, *, remove_pending=False):
        run, token = self._prepare(
            FakeBackend(
                self.start,
                flashes=[
                    self._effect(
                        rc=1,
                        completed=False,
                        outcome="BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
                    )
                ],
            )
        )
        result = M.execute(
            self.raw,
            self.manifest,
            run,
            token,
            FakeBackend(
                self.start,
                flashes=[
                    self._effect(
                        rc=1,
                        completed=False,
                        outcome="BOOT_WRITTEN_READBACK_EXACT_SYSTEM_RETURN_UNCERTAIN",
                    )
                ],
            ),
        )
        self.assertEqual(result["reason"], "CANDIDATE_RETURN_PENDING")
        if remove_pending:
            (run / "23-candidate-return-pending.json").unlink()
        return run

    def _prepare_continuation(self, *, remove_pending=False):
        self._uncertain_run(remove_pending=remove_pending)
        token = C.prepare(self.manifest_path)
        return M.RUN_ROOT / self.manifest["runId"], token

    def _activated_backend_with_resume_intent(self):
        run, token = self._prepare_continuation()
        ctx = C._load_context(self.manifest_path)
        C._publish_checked(
            ctx,
            "24-candidate-return-intent.json",
            "CANDIDATE_RETURN_INTENT",
            {
                "schema": C.INTENT_SCHEMA,
                "capability": C.CAPABILITY,
                "approvalSha256": M.sha256_bytes(token.encode("ascii")),
                "pendingReceiptSha256": ctx.pending_receipt_sha256,
                "candidateReplay": False,
                "physicalSystemReturnAllowed": True,
                "qualificationReviewSha256": ctx.qualification_review_sha256,
            },
        )
        ctx = C._load_context(self.manifest_path)
        activation = C._make_backend_activation(
            ctx, token, phase="resume", single_samsung_inventory_sha256=None
        )
        runner = mock.Mock()
        backend = C.backend_module.CandidateReturnBackend(
            activation=activation, runner=runner
        )
        backend.bind_manifest(ctx.manifest)
        return run, ctx, backend, runner

    def test_review_gate_rejects_absent_symlink_malformed_wrong_and_stale_reviews(self):
        self.assertTrue(C.review_gate_present())
        self.review_path.unlink()
        self.assertFalse(C.review_gate_present())

        target = self.review_path.with_name("review-target.json")
        target.write_bytes(
            M.canonical_json(
                {
                    "schema": C.REVIEW_SCHEMA,
                    "capability": C.CAPABILITY,
                    "verdict": "PASS_GO",
                    "scope": C.REVIEW_SCOPE,
                    "targetProfile": M.TARGET_PROFILE,
                    "executionClosureSha256": C.execution_closure_sha256(),
                    "findings": {"high": [], "medium": [], "low": []},
                    "contacts": {key: 0 for key in C.CONTINUATION_REVIEW_CONTACT_KEYS},
                    "reviewer": "independent-luna-max",
                    "reviewDate": "2026-08-21",
                    "liveAuthority": False,
                }
            )
        )
        self.review_path.symlink_to(target)
        self.assertFalse(C.review_gate_present())
        self.review_path.unlink()
        self.review_path.write_bytes(b"not-json")
        self.assertFalse(C.review_gate_present())
        self.review_path.write_bytes(M.canonical_json({"verdict": "NO_GO"}))
        self.assertFalse(C.review_gate_present())
        self.review_path.write_bytes(
            M.canonical_json(
                {
                    "schema": C.REVIEW_SCHEMA,
                    "capability": C.CAPABILITY,
                    "verdict": "PASS_GO",
                    "scope": C.REVIEW_SCOPE,
                    "targetProfile": M.TARGET_PROFILE,
                    "executionClosureSha256": "f" * 64,
                    "findings": {"high": [], "medium": [], "low": []},
                    "contacts": {key: 0 for key in C.CONTINUATION_REVIEW_CONTACT_KEYS},
                    "reviewer": "independent-luna-max",
                    "reviewDate": "2026-08-21",
                    "liveAuthority": False,
                }
            )
        )
        self.assertFalse(C.review_gate_present())

    def test_missing_review_blocks_backend_creation_without_contact(self):
        self._uncertain_run()
        ctx = C._load_context(self.manifest_path)
        self.review_path.unlink()
        with mock.patch.object(C.backend_module, "create") as create:
            with self.assertRaises(C.ContractError):
                C._live_backend("resume", ctx, "A90-F1-CANDIDATE-RETURN-V1-APPROVE:" + "a" * 64)
        create.assert_not_called()

    def test_activation_rejects_current_22_receipt_substitution_before_runner(self):
        run, ctx, backend, runner = self._activated_backend_with_resume_intent()
        path = run / "22-candidate-result.json"
        record = M.parse_canonical(path.read_bytes(), path.name)
        record["payload"]["receiptSha256"] = "f" * 64
        path.write_bytes(M.canonical_json(record))
        with self.assertRaises(C.ContractError):
            backend.inspect_pending(ctx.manifest)
        runner.run.assert_not_called()

    def test_activation_rejects_current_23_receipt_substitution_before_runner(self):
        run, ctx, backend, runner = self._activated_backend_with_resume_intent()
        path = run / "23-candidate-return-pending.json"
        record = M.parse_canonical(path.read_bytes(), path.name)
        record["payload"]["effectReceiptSha256"] = "f" * 64
        path.write_bytes(M.canonical_json(record))
        with self.assertRaises(C.ContractError):
            backend.inspect_pending(ctx.manifest)
        runner.run.assert_not_called()

    def test_activation_rejects_joined_new_22_23_receipt_before_runner(self):
        run, ctx, backend, runner = self._activated_backend_with_resume_intent()
        result_path = run / "22-candidate-result.json"
        result = M.parse_canonical(result_path.read_bytes(), result_path.name)
        pending_path = run / "23-candidate-return-pending.json"
        pending = M.parse_canonical(pending_path.read_bytes(), pending_path.name)
        replacement = "f" * 64
        result["payload"]["receiptSha256"] = replacement
        pending["payload"]["effectReceiptSha256"] = replacement
        result_path.write_bytes(M.canonical_json(result))
        pending_path.write_bytes(M.canonical_json(pending))
        with self.assertRaises(C.ReviewLeaseDrift):
            backend.inspect_pending(ctx.manifest)
        runner.run.assert_not_called()

    def test_activation_rejects_manifest_envelope_drift_and_cross_manifest_prefix(self):
        run, ctx, backend, runner = self._activated_backend_with_resume_intent()
        originals = {
            path.name: path.read_bytes()
            for path in run.iterdir()
            if path.is_file() and path.name.endswith(".json")
        }
        for name, raw in originals.items():
            path = run / name
            record = M.parse_canonical(raw, name)
            record["manifestSha256"] = "f" * 64
            path.write_bytes(M.canonical_json(record))
            with self.subTest(name=name), self.assertRaises(C.ContractError):
                backend.inspect_pending(ctx.manifest)
            path.write_bytes(raw)

        for name, raw in originals.items():
            path = run / name
            record = M.parse_canonical(raw, name)
            record["manifestSha256"] = "f" * 64
            path.write_bytes(M.canonical_json(record))
        try:
            with self.assertRaises(C.ReviewLeaseDrift):
                backend.inspect_pending(ctx.manifest)
        finally:
            for name, raw in originals.items():
                (run / name).write_bytes(raw)
        runner.run.assert_not_called()

    @staticmethod
    def _native_visible(snapshot):
        return {
            "state": C.STATE_NATIVE_VISIBLE,
            "otherTargetsUntouched": True,
            "singleSamsungInventorySha256": "a" * 64,
            "candidateSnapshot": snapshot,
            "twrpIdentity": None,
            "attribution": None,
        }

    @staticmethod
    def _twrp_present():
        return {
            "state": C.STATE_TWRP_PRESENT,
            "otherTargetsUntouched": True,
            "singleSamsungInventorySha256": "a" * 64,
            "candidateSnapshot": None,
            "twrpIdentity": dict(C.TWRP_IDENTITY),
            "attribution": None,
        }

    @staticmethod
    def _failure(code):
        return {
            "state": C.STATE_ATTRIBUTABLE_FAILURE,
            "otherTargetsUntouched": True,
            "singleSamsungInventorySha256": "a" * 64,
            "candidateSnapshot": None,
            "twrpIdentity": None,
            "attribution": code,
        }

    def test_prepare_is_host_only_and_missing_23_is_reconstructible(self):
        run, token = self._prepare_continuation(remove_pending=True)
        self.assertTrue(token.startswith(C.APPROVAL_PREFIX))
        self.assertNotIn("24-candidate-return-intent.json", M.read_records(run))
        backend = ReturnBackend(inspect=self._native_visible(self._snapshot_payload()))
        result = C.resume(
            self.manifest_path,
            token,
            backend,
            operator_attended=True,
        )
        self.assertEqual(result["terminal"], "CANDIDATE_NATIVE_VISIBLE_FINALIZE_REQUIRED")
        self.assertEqual(backend.calls, ["inspect"])

    def test_intent_precedes_contact_and_native_finalize_consumes_candidate_guard(self):
        run, token = self._prepare_continuation()
        backend = ReturnBackend(inspect=self._native_visible(self._snapshot_payload()))
        original = backend.inspect_pending

        def inspected(manifest):
            self.assertIn("24-candidate-return-intent.json", M.read_records(run))
            return original(manifest)

        backend.inspect_pending = inspected
        resumed = C.resume(self.manifest_path, token, backend, operator_attended=True)
        self.assertFalse(resumed["physicalActionRequired"])
        final = C.finalize(
            self.manifest_path,
            token,
            ReturnBackend(after=self._native_visible(self._snapshot_payload())),
            operator_attended=True,
            physical_action_confirmed=False,
        )
        self.assertEqual(final["terminal"], "PASS_A90_RESIDENT_INSTALLED")
        self.assertFalse((M.RUN_ROOT / "active-run.guard").exists())
        candidate_guard, _ = M._candidate_guard(self.manifest)
        self.assertTrue(candidate_guard.exists())

    def test_pass_consumed_candidate_guard_rejects_same_sha_reprepare(self):
        run, token = self._prepare_continuation()
        C.resume(
            self.manifest_path,
            token,
            ReturnBackend(inspect=self._native_visible(self._snapshot_payload())),
            operator_attended=True,
        )
        C.finalize(
            self.manifest_path,
            token,
            ReturnBackend(after=self._native_visible(self._snapshot_payload())),
            operator_attended=True,
            physical_action_confirmed=False,
        )
        reused_manifest = json.loads(self.raw)
        reused_manifest["runId"] = "a90-minimal-reused"
        reused_raw = M.canonical_json(reused_manifest)
        reused_run = M.RUN_ROOT / reused_manifest["runId"]
        with self.assertRaisesRegex(M.ContractError, "reserved or consumed"):
            M.prepare(reused_raw, reused_manifest, reused_run, FakeBackend(self.start))
        self.assertFalse(reused_run.exists())
        self.assertFalse((M.RUN_ROOT / "active-run.guard").exists())

    def test_twrp_branch_instructs_once_and_requires_explicit_physical_confirmation(self):
        run, token = self._prepare_continuation()
        backend = ReturnBackend(inspect=self._twrp_present())
        result = C.resume(self.manifest_path, token, backend, operator_attended=True)
        self.assertEqual(result["physicalInstruction"], "Reboot -> System")
        self.assertEqual(backend.calls, ["inspect"])
        with self.assertRaises(C.ContractError):
            C.resume(self.manifest_path, token, backend, operator_attended=True)
        with self.assertRaises(C.ContractError):
            C.finalize(
                self.manifest_path,
                token,
                ReturnBackend(after=self._native_visible(self._snapshot_payload())),
                operator_attended=True,
                physical_action_confirmed=False,
            )
        self.assertNotIn("25-candidate-observation-intent.json", M.read_records(run))

    def test_wrong_twrp_identity_parks_without_physical_instruction(self):
        run, token = self._prepare_continuation()
        wrong = self._twrp_present()
        wrong["twrpIdentity"]["scriptSha256"] = "f" * 64
        result = C.resume(
            self.manifest_path,
            token,
            ReturnBackend(inspect=wrong),
            operator_attended=True,
        )
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertNotIn("physicalInstruction", result)
        self.assertNotIn("30-rollback-intent.json", M.read_records(run))

    def test_twrp_identity_requires_exact_keys_and_types(self):
        for key, expected in C.TWRP_IDENTITY.items():
            if type(expected) is not int:
                continue
            for replacement in (True, float(expected), str(expected)):
                wrong = self._twrp_present()
                wrong["twrpIdentity"][key] = replacement
                with self.subTest(key=key, replacement=type(replacement).__name__):
                    with self.assertRaises(C.ContractError):
                        C._validate_observation(
                            wrong,
                            self.manifest,
                            after_physical=False,
                        )
        extra = self._twrp_present()
        extra["twrpIdentity"]["extra"] = 1
        with self.assertRaises(C.ContractError):
            C._validate_observation(extra, self.manifest, after_physical=False)
        missing = self._twrp_present()
        del missing["twrpIdentity"]["scriptNlink"]
        with self.assertRaises(C.ContractError):
            C._validate_observation(missing, self.manifest, after_physical=False)

    def test_physical_finalize_observes_once_then_passes_without_host_reboot(self):
        run, token = self._prepare_continuation()
        C.resume(
            self.manifest_path,
            token,
            ReturnBackend(inspect=self._twrp_present()),
            operator_attended=True,
        )
        backend = ReturnBackend(after=self._native_visible(self._snapshot_payload()))
        result = C.finalize(
            self.manifest_path,
            token,
            backend,
            operator_attended=True,
            physical_action_confirmed=True,
        )
        self.assertEqual(result["terminal"], "PASS_A90_RESIDENT_INSTALLED")
        self.assertEqual(backend.calls, [("observe-after", True)])
        source = SOURCE.read_text()
        self.assertNotIn("adb reboot", source)
        self.assertNotIn("twrp reboot", source)
        self.assertIn("24-candidate-return-observed.json", M.read_records(run))

    def test_finalize_rejects_tampered_return_intent_before_observation(self):
        run, token = self._prepare_continuation()
        C.resume(
            self.manifest_path,
            token,
            ReturnBackend(inspect=self._native_visible(self._snapshot_payload())),
            operator_attended=True,
        )
        path = run / "24-candidate-return-intent.json"
        intent = M.parse_canonical(path.read_bytes(), "return intent")
        intent["payload"]["pendingReceiptSha256"] = "f" * 64
        path.write_bytes(M.canonical_json(intent))
        backend = ReturnBackend(after=self._native_visible(self._snapshot_payload()))
        with self.assertRaises(C.ContractError):
            C.finalize(
                self.manifest_path,
                token,
                backend,
                operator_attended=True,
                physical_action_confirmed=False,
            )
        self.assertEqual(backend.calls, [])
        self.assertNotIn("25-candidate-observation-intent.json", M.read_records(run))

    def test_candidate_valid_but_mismatched_recovery_evidence_never_passes(self):
        run, token = self._prepare_continuation()
        bad_snapshot = dict(self._snapshot_payload())
        bad_snapshot["recoveryEvidenceSha256"] = "a" * 64
        result = C.resume(
            self.manifest_path,
            token,
            ReturnBackend(inspect=self._native_visible(bad_snapshot)),
            operator_attended=True,
        )
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertEqual(result["reason"], "CANDIDATE_RETURN_OBSERVER_UNPROVED")
        self.assertIn("40-terminal.json", M.read_records(run))
        self.assertNotIn("30-rollback-intent.json", M.read_records(run))
        self.assertTrue((M.RUN_ROOT / "active-run.guard").exists())

    def test_rollback_valid_but_mismatched_recovery_evidence_never_closes(self):
        run, token = self._prepare_continuation()
        bad_snapshot = replace(
            self._snapshot("old", "old-build"),
            recovery_evidence_sha256="a" * 64,
        )
        backend = ReturnBackend(
            inspect=self._failure("EXPLICIT_CANDIDATE_HEALTH_CONTRADICTION"),
            flashes=[self._effect()],
            observations=[bad_snapshot],
        )
        result = C.resume(
            self.manifest_path,
            token,
            backend,
            operator_attended=True,
        )
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertEqual(result["reason"], "ROLLBACK_RECOVERY_EVIDENCE_MISMATCH")
        self.assertNotIn("NO_PROOF_ROLLED_BACK", result["terminal"])
        self.assertTrue((M.RUN_ROOT / "active-run.guard").exists())

    def _assert_rollback_stops_when_guard_removed_after_launch(self, guard_kind):
        run, token = self._prepare_continuation()
        backend = ReturnBackend(
            inspect=self._failure("EXPLICIT_CANDIDATE_HEALTH_CONTRADICTION"),
            flashes=[self._effect()],
            observations=[self._snapshot("old", "old-build")],
        )
        original_publish = M.publish_record

        def publish_and_remove_guard(run_directory, name, value):
            original_publish(run_directory, name, value)
            if name == "31-rollback-launched.json":
                if guard_kind == "active":
                    path, _expected = M._active_guard(self.manifest)
                else:
                    path, _expected = M._candidate_guard(self.manifest)
                path.unlink()

        with mock.patch.object(M, "publish_record", side_effect=publish_and_remove_guard):
            with self.assertRaises(M.ContractError):
                C.resume(
                    self.manifest_path,
                    token,
                    backend,
                    operator_attended=True,
                )
        self.assertEqual(
            [call for call in backend.calls if isinstance(call, tuple)], []
        )
        records = M.read_records(run)
        self.assertIn("31-rollback-launched.json", records)
        self.assertNotIn("32-rollback-result.json", records)
        self.assertEqual(M.recovery_decision(run), "PARK_ROLLBACK_NO_REPLAY")

    def test_rollback_guard_revalidation_blocks_flash_if_active_removed(self):
        self._assert_rollback_stops_when_guard_removed_after_launch("active")

    def test_rollback_guard_revalidation_blocks_flash_if_candidate_removed(self):
        self._assert_rollback_stops_when_guard_removed_after_launch("candidate")

    def test_observation_intent_is_consumed_without_replay(self):
        run, token = self._prepare_continuation()
        C.resume(
            self.manifest_path,
            token,
            ReturnBackend(inspect=self._native_visible(self._snapshot_payload())),
            operator_attended=True,
        )
        M.publish_record(
            run,
            "25-candidate-observation-intent.json",
            M._record(
                "CANDIDATE_OBSERVATION_INTENT",
                M.sha256_bytes(self.raw),
                {
                    "schema": C.OBSERVATION_INTENT_SCHEMA,
                    "capability": C.CAPABILITY,
                    "approvalSha256": M.sha256_bytes(token.encode("ascii")),
                    "physicalActionConfirmed": False,
                    "candidateReplay": False,
                    "qualificationReviewSha256": self.manifest["qualification"]["review"]["sha256"],
                },
            ),
        )
        backend = ReturnBackend(after=self._native_visible(self._snapshot_payload()))
        with self.assertRaises(C.ContractError):
            C.finalize(
                self.manifest_path,
                token,
                backend,
                operator_attended=True,
                physical_action_confirmed=False,
            )
        self.assertEqual(backend.calls, [])

    def test_finalize_observer_loss_consumes_observation_without_rollback(self):
        run, token = self._prepare_continuation()
        C.resume(
            self.manifest_path,
            token,
            ReturnBackend(inspect=self._native_visible(self._snapshot_payload())),
            operator_attended=True,
        )
        result = C.finalize(
            self.manifest_path,
            token,
            ReturnBackend(after=RuntimeError("transport lost")),
            operator_attended=True,
            physical_action_confirmed=False,
        )
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        records = M.read_records(run)
        self.assertIn("25-candidate-observation-intent.json", records)
        self.assertNotIn("30-rollback-intent.json", records)

    def test_ambiguous_or_observer_failure_parks_without_rollback(self):
        run, token = self._prepare_continuation()
        ambiguous = {
            "state": C.STATE_AMBIGUOUS,
            "otherTargetsUntouched": False,
            "singleSamsungInventorySha256": None,
            "candidateSnapshot": None,
            "twrpIdentity": None,
            "attribution": None,
        }
        result = C.resume(
            self.manifest_path,
            token,
            ReturnBackend(inspect=ambiguous),
            operator_attended=True,
        )
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertNotIn("30-rollback-intent.json", M.read_records(run))

    def test_attribution_with_foreign_inventory_never_rolls_back(self):
        run, token = self._prepare_continuation()
        foreign_failure = self._failure("EXPLICIT_CANDIDATE_HEALTH_CONTRADICTION")
        foreign_failure["otherTargetsUntouched"] = False
        result = C.resume(
            self.manifest_path,
            token,
            ReturnBackend(inspect=foreign_failure),
            operator_attended=True,
        )
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertNotIn("30-rollback-intent.json", M.read_records(run))

    def test_attributable_failure_is_the_only_resume_rollback_path(self):
        run, token = self._prepare_continuation()
        backend = ReturnBackend(
            inspect=self._failure("EXPLICIT_CANDIDATE_HEALTH_CONTRADICTION"),
            flashes=[self._effect()],
            observations=[self._snapshot("old", "old-build")],
        )
        result = C.resume(
            self.manifest_path, token, backend, operator_attended=True
        )
        self.assertEqual(result["terminal"], "NO_PROOF_ROLLED_BACK")
        effect_calls = [call for call in backend.calls if isinstance(call, tuple)]
        self.assertEqual([call[0] for call in effect_calls], ["flash", "observe"])
        self.assertEqual(effect_calls[0][1], self.manifest["rollback"]["sha256"])
        self.assertIs(effect_calls[0][2], True)

    def test_rollback_health_without_confirmed_effect_receipt_stays_recovery_required(self):
        run, token = self._prepare_continuation()
        backend = ReturnBackend(
            inspect=self._failure("EXPLICIT_CANDIDATE_HEALTH_CONTRADICTION"),
            flashes=[self._effect(outcome="UNCLASSIFIED")],
            observations=[self._snapshot("old", "old-build")],
        )
        result = C.resume(
            self.manifest_path, token, backend, operator_attended=True
        )
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertIn("32-rollback-result.json", M.read_records(run))

    def test_review_drift_and_physical_confirmation_mismatch_are_rejected(self):
        _run, token = self._prepare_continuation()
        review = M.parse_canonical(self.review_path.read_bytes(), "review")
        review["reviewer"] = "substituted"
        self.review_path.write_bytes(M.canonical_json(review))
        with self.assertRaises(C.ContractError):
            C.resume(
                self.manifest_path,
                token,
                ReturnBackend(inspect=self._twrp_present()),
                operator_attended=True,
            )

    def _drift_continuation_review(self):
        review = M.parse_canonical(self.review_path.read_bytes(), "review")
        review["reviewer"] = "drifted-review"
        self.review_path.write_bytes(M.canonical_json(review))

    def _drift_qualification_review(self):
        review = M.parse_canonical(self.review.read_bytes(), "qualification review")
        review["reviewer"] = "drifted-qualification-review"
        self.review.write_bytes(M.canonical_json(review))

    def _swap_qualification_review_same_bytes(self):
        replacement = self.root / "qualification-review-replacement.json"
        replacement.write_bytes(self.review.read_bytes())
        os.chmod(replacement, 0o600)
        os.replace(replacement, self.review)

    def test_same_bytes_review_swap_is_not_the_bound_lease(self):
        _run, token = self._prepare_continuation()
        replacement = self.root / "review-replacement.json"
        replacement.write_bytes(self.review_path.read_bytes())
        os.chmod(replacement, 0o600)
        os.replace(replacement, self.review_path)
        backend = ReturnBackend(inspect=self._native_visible(self._snapshot_payload()))
        with self.assertRaises(C.ContractError):
            C.resume(
                self.manifest_path,
                token,
                backend,
                operator_attended=True,
            )
        self.assertEqual(backend.calls, [])

    def test_review_drift_after_resume_intent_blocks_contact(self):
        run, token = self._prepare_continuation()
        publish = M.publish_record

        def drift_after_intent(directory, name, value):
            publish(directory, name, value)
            if name == "24-candidate-return-intent.json":
                self._drift_continuation_review()

        backend = ReturnBackend(inspect=self._native_visible(self._snapshot_payload()))
        with mock.patch.object(M, "publish_record", side_effect=drift_after_intent):
            with self.assertRaises(C.ReviewLeaseDrift):
                C.resume(
                    self.manifest_path,
                    token,
                    backend,
                    operator_attended=True,
                )
        self.assertEqual(backend.calls, [])
        self.assertIn("24-candidate-return-intent.json", M.read_records(run))

    def test_review_drift_after_finalize_observation_return_blocks_terminal(self):
        run, token = self._prepare_continuation()
        C.resume(
            self.manifest_path,
            token,
            ReturnBackend(inspect=self._native_visible(self._snapshot_payload())),
            operator_attended=True,
        )

        class DriftAfterObservation(ReturnBackend):
            def observe_after_continuation(inner_self, manifest, *, physical_action_confirmed):
                result = super().observe_after_continuation(
                    manifest, physical_action_confirmed=physical_action_confirmed
                )
                self._drift_continuation_review()
                return result

        backend = DriftAfterObservation(after=self._native_visible(self._snapshot_payload()))
        with self.assertRaises(C.ReviewLeaseDrift):
            C.finalize(
                self.manifest_path,
                token,
                backend,
                operator_attended=True,
                physical_action_confirmed=False,
            )
        self.assertIn("25-candidate-observation-intent.json", M.read_records(run))
        self.assertNotIn("40-terminal.json", M.read_records(run))
        self.assertTrue((M.RUN_ROOT / "active-run.guard").exists())

    def test_review_drift_after_rollback_launch_blocks_preflash(self):
        run, token = self._prepare_continuation()
        publish = M.publish_record

        def drift_after_launch(directory, name, value):
            publish(directory, name, value)
            if name == "31-rollback-launched.json":
                self._drift_continuation_review()

        backend = ReturnBackend(
            inspect=self._failure("EXPLICIT_CANDIDATE_HEALTH_CONTRADICTION"),
            flashes=[self._effect()],
            observations=[self._snapshot("old", "old-build")],
        )
        with mock.patch.object(M, "publish_record", side_effect=drift_after_launch):
            with self.assertRaises(C.ReviewLeaseDrift):
                C.resume(
                    self.manifest_path,
                    token,
                    backend,
                    operator_attended=True,
                )
        self.assertEqual(
            [call for call in backend.calls if isinstance(call, tuple)], []
        )
        self.assertIn("31-rollback-launched.json", M.read_records(run))

    def test_review_drift_after_rollback_return_blocks_result_publication(self):
        run, token = self._prepare_continuation()

        class DriftAfterRollbackFlash(ReturnBackend):
            def flash(inner_self, artifact, *, rollback, timeout_sec):
                result = super().flash(
                    artifact, rollback=rollback, timeout_sec=timeout_sec
                )
                if rollback:
                    self._drift_continuation_review()
                return result

        backend = DriftAfterRollbackFlash(
            inspect=self._failure("EXPLICIT_CANDIDATE_HEALTH_CONTRADICTION"),
            flashes=[self._effect()],
            observations=[self._snapshot("old", "old-build")],
        )
        with self.assertRaises(C.ReviewLeaseDrift):
            C.resume(
                self.manifest_path,
                token,
                backend,
                operator_attended=True,
            )
        self.assertNotIn("32-rollback-result.json", M.read_records(run))

    def test_qualification_review_drift_after_rollback_launch_blocks_preflash(self):
        run, token = self._prepare_continuation()
        publish = M.publish_record

        def drift_after_launch(directory, name, value):
            publish(directory, name, value)
            if name == "31-rollback-launched.json":
                self._drift_qualification_review()

        backend = ReturnBackend(
            inspect=self._failure("EXPLICIT_CANDIDATE_HEALTH_CONTRADICTION"),
            flashes=[self._effect()],
            observations=[self._snapshot("old", "old-build")],
        )
        with mock.patch.object(M, "publish_record", side_effect=drift_after_launch):
            with self.assertRaises(C.ReviewLeaseDrift):
                C.resume(
                    self.manifest_path,
                    token,
                    backend,
                    operator_attended=True,
                )
        self.assertEqual(
            [call for call in backend.calls if isinstance(call, tuple)], []
        )
        self.assertIn("31-rollback-launched.json", M.read_records(run))

    def test_qualification_review_same_bytes_swap_after_rollback_launch_blocks_preflash(self):
        run, token = self._prepare_continuation()
        publish = M.publish_record

        def swap_after_launch(directory, name, value):
            publish(directory, name, value)
            if name == "31-rollback-launched.json":
                self._swap_qualification_review_same_bytes()

        backend = ReturnBackend(
            inspect=self._failure("EXPLICIT_CANDIDATE_HEALTH_CONTRADICTION"),
            flashes=[self._effect()],
            observations=[self._snapshot("old", "old-build")],
        )
        with mock.patch.object(M, "publish_record", side_effect=swap_after_launch):
            with self.assertRaises(C.ReviewLeaseDrift):
                C.resume(
                    self.manifest_path,
                    token,
                    backend,
                    operator_attended=True,
                )
        self.assertEqual(
            [call for call in backend.calls if isinstance(call, tuple)], []
        )

    def test_qualification_review_drift_after_observation_return_blocks_terminal(self):
        run, token = self._prepare_continuation()
        C.resume(
            self.manifest_path,
            token,
            ReturnBackend(inspect=self._native_visible(self._snapshot_payload())),
            operator_attended=True,
        )

        class DriftAfterQualificationObservation(ReturnBackend):
            def observe_after_continuation(inner_self, manifest, *, physical_action_confirmed):
                result = super().observe_after_continuation(
                    manifest, physical_action_confirmed=physical_action_confirmed
                )
                self._drift_qualification_review()
                return result

        backend = DriftAfterQualificationObservation(
            after=self._native_visible(self._snapshot_payload())
        )
        with self.assertRaises(C.ReviewLeaseDrift):
            C.finalize(
                self.manifest_path,
                token,
                backend,
                operator_attended=True,
                physical_action_confirmed=False,
            )
        self.assertNotIn("40-terminal.json", M.read_records(run))

    def test_qualification_review_same_bytes_swap_after_terminal_readback_blocks_release(self):
        run, token = self._prepare_continuation()
        C.resume(
            self.manifest_path,
            token,
            ReturnBackend(inspect=self._native_visible(self._snapshot_payload())),
            operator_attended=True,
        )
        original_readback = M._readback_published_record

        def swap_after_readback(directory, name, expected_raw, manifest_sha256):
            result = original_readback(directory, name, expected_raw, manifest_sha256)
            if name == "40-terminal.json":
                self._swap_qualification_review_same_bytes()
            return result

        backend = ReturnBackend(after=self._native_visible(self._snapshot_payload()))
        with mock.patch.object(
            M, "_readback_published_record", side_effect=swap_after_readback
        ):
            with self.assertRaises(C.ReviewLeaseDrift):
                C.finalize(
                    self.manifest_path,
                    token,
                    backend,
                    operator_attended=True,
                    physical_action_confirmed=False,
                )
        self.assertIn("40-terminal.json", M.read_records(run))
        self.assertTrue((M.RUN_ROOT / "active-run.guard").exists())

    def test_review_drift_after_terminal_readback_blocks_active_release(self):
        run, token = self._prepare_continuation()
        C.resume(
            self.manifest_path,
            token,
            ReturnBackend(inspect=self._native_visible(self._snapshot_payload())),
            operator_attended=True,
        )
        publish = M.publish_record

        def drift_after_terminal(directory, name, value):
            publish(directory, name, value)
            if name == "40-terminal.json":
                self._drift_continuation_review()

        backend = ReturnBackend(after=self._native_visible(self._snapshot_payload()))
        with mock.patch.object(M, "publish_record", side_effect=drift_after_terminal):
            with self.assertRaises(C.ReviewLeaseDrift):
                C.finalize(
                    self.manifest_path,
                    token,
                    backend,
                    operator_attended=True,
                    physical_action_confirmed=False,
                )
        self.assertIn("40-terminal.json", M.read_records(run))
        self.assertTrue((M.RUN_ROOT / "active-run.guard").exists())


if __name__ == "__main__":
    unittest.main()
