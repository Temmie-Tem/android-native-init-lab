"""Host-only tests for the one-ordinal unattended A90 resident D1 runner."""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = REPO_ROOT / "workspace/public/src/scripts/server-distro"
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
import sys

for path in (SERVER_DIR, REVAL_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import a90_transition_d1_session_v1 as attended  # noqa: E402
import a90_transition_engine_v2 as engine  # noqa: E402
import a90_unattended_resident_d1_v1 as unattended  # noqa: E402
from a90_transition_contract_v2 import (  # noqa: E402
    AttendedSessionBinding,
    ContractError as EngineContractError,
    DISPLAY_SUCCESSOR,
    RiskTier,
    SessionAction,
    SessionPreflight,
    Workflow,
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_private(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, bytes):
        path.write_bytes(value)
    else:
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def bound(path: Path) -> attended.BoundFile:
    return attended.BoundFile(path.resolve(), path.stat().st_size, digest(path))


class A90UnattendedResidentD1V1Tests(unittest.TestCase):
    def base_spec(self, root: Path) -> attended.SessionSpec:
        files = {
            role: bound(path)
            for role, path in attended.SOURCE_PATHS.items()
        }
        material: dict[str, Path] = {}
        for name in (
            "base-manifest.json",
            "resident-manifest.json",
            "resident-terminal.json",
            "candidate.img",
            "rollback.img",
            "rootfs.img",
            "observer-key",
        ):
            path = root / "base" / name
            write_private(path, name.encode())
            material[name] = path
        return attended.SessionSpec(
            manifest_path=material["base-manifest.json"],
            manifest_sha256=digest(material["base-manifest.json"]),
            run_id="a90-d1-attended-20260803-01",
            resident_run_id="a90-v3406-debian-display-f1-20260802-01",
            resident_manifest=bound(material["resident-manifest.json"]),
            resident_journal=(bound(material["resident-terminal.json"]),),
            candidate=bound(material["candidate.img"]),
            rollback=bound(material["rollback.img"]),
            rootfs=bound(material["rootfs.img"]),
            candidate_version="0.11.161",
            candidate_build="phase2-display-v1-native-handoff",
            remote_final="/mnt/sdext/a90/runtime/rootfs.img",
            remote_work=attended.WORK_PATH,
            bridge_device="/dev/serial/by-id/usb-A90-LNX_TEST-if00",
            bridge_realpath="/dev/ttyACM0",
            recovery_serial_sha256="2" * 64,
            observer_key=material["observer-key"],
            observer_public_key_sha256="3" * 64,
            observer_device="192.0.2.2",
            observer_port=2222,
            observer_host_ncm_profile="a90-test-ncm",
            handoff_command=(
                attended.base.HANDOFF_COMMAND,
                attended.base.HANDOFF_TOKEN,
                "/mnt/sdext/a90/runtime/rootfs.img",
                digest(material["rootfs.img"]),
            ),
            handoff_timeout=1200,
            ssh_marker_timeout=120,
            candidate_return_timeout=240,
            source_closure=files,
            transaction_dir=root / "unused-attended-transaction",
            session_lock_path=root / "unused-attended.lock",
            session_duration_sec=3600,
            max_actions=4,
            recovery_profile="attended physical recovery",
        )

    def qualification_fixture(
        self,
        root: Path,
        base: attended.SessionSpec,
    ) -> Path:
        transaction = root / "qualification" / attended.SESSION_DIR_NAME
        action_dir = transaction / "action-001"
        old_manifest = {
            "schema": attended.SCHEMA,
            "resident": {
                "candidate": {"sha256": base.candidate.sha256},
                "rollback": {"sha256": base.rollback.sha256},
                "rootfs": {"sha256": base.rootfs.sha256},
            },
            "target": {"profile": attended.staging.TARGET_PROFILE},
        }
        manifest_path = transaction.parent / "manifest.json"
        write_private(manifest_path, old_manifest)
        intent = {
            "schema": attended.RESULT_SCHEMA,
            "ordinal": 1,
            "handoff_dispatch_count_max": 1,
            "journal_fsync_completed_before_dispatch": True,
        }
        observation = {
            "native_release_proven": True,
            "debian_pid1_proven": True,
            "dropbear_proven": True,
            "display_mechanical_proof": True,
            "bounded_display_failure": False,
            "ssh": {"proof": True},
        }
        action_result = {
            "schema": attended.RESULT_SCHEMA,
            "ordinal": 1,
            "handoff_dispatch_count": 1,
            "resident_healthy": True,
            "observation": observation,
            "cleanup": {
                "rc": 0,
                "text": "A90D1_WORK_CLEANUP exact=1 work_absent=1",
            },
            "final_health": {
                "exact_bridge": True,
                "selected_realpath": base.bridge_realpath,
                "version": {
                    "text": f"version: {base.candidate_version} build={base.candidate_build}"
                },
                "selftest": {"text": "selftest: pass=12 warn=1 fail=0"},
            },
            "final_source": {
                "rc": 0,
                "text": "A90F1_SOURCE_PRECHECK exact=1 work_absent=1",
            },
            "payload_transfer": False,
            "partition_write": False,
            "flash": False,
        }
        outcome = {
            "schema": attended.OUTCOME_SCHEMA,
            "ordinal": 1,
            "action": SessionAction.SWITCHROOT_EXPERIMENT.value,
            "status": engine.SessionActionStatus.EXPERIMENT_BLOCKED.value,
            "action_started": True,
            "failure_class": "POSTFLIGHT_EXPERIMENT_BLOCKED",
            "postflight": {
                "operator_attended": True,
                "target_identity_matches": True,
                "resident_identity_matches": True,
                "rollback_ready": True,
                "recovery_available": True,
            },
            "independent_safety_check": False,
        }
        write_private(action_dir / "handoff-intent.json", intent)
        write_private(action_dir / "observation.json", observation)
        write_private(action_dir / "result.json", action_result)
        write_private(action_dir / "engine-outcome.json", outcome)
        visible = {
            "schema": "a90_operator_display_observation_v1",
            "ordinal": 1,
            "action": SessionAction.SWITCHROOT_EXPERIMENT.value,
            "source": "attended-operator-chat",
            "display_visible": True,
            "display_owner_text_observed": "DISPLAY OWNER DEBIAN",
            "handoff_intent_sha256": digest(action_dir / "handoff-intent.json"),
            "observation_sha256": digest(action_dir / "observation.json"),
        }
        write_private(action_dir / "operator-display-observation.json", visible)
        outcome_evidence = bound(action_dir / "engine-outcome.json")
        journal = {
            "schema": attended.JOURNAL_SCHEMA,
            "sequence": 2,
            "action": "action-001-result",
            "manifest_sha256": digest(manifest_path),
            "outcome": {
                "ordinal": 1,
                "action": SessionAction.SWITCHROOT_EXPERIMENT.value,
                "status": engine.SessionActionStatus.EXPERIMENT_BLOCKED.value,
                "failure_class": "POSTFLIGHT_EXPERIMENT_BLOCKED",
            },
            "outcome_evidence": unattended._as_dict(outcome_evidence),
            "snapshot": {"device_safety_state": "RESIDENT_HEALTHY"},
        }
        write_private(
            transaction / "journal/0002-action-001-result.json",
            journal,
        )
        return transaction

    def review_receipt(self, root: Path) -> Path:
        sources = unattended._source_closure()
        path = root / "review.json"
        path.write_text(
            json.dumps(
                {
                    "schema": unattended.REVIEW_SCHEMA,
                    "status": unattended.REVIEW_STATUS,
                    "reviewed_source_closure": {
                        role: unattended._as_dict(item)
                        for role, item in sorted(sources.items())
                    },
                    "independent_review_completed": True,
                    "unresolved_findings": [],
                    "permanent_boundaries_unchanged": True,
                    "device_contact": False,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return path

    def direct_spec(self, root: Path) -> unattended.UnattendedSpec:
        base = self.base_spec(root)
        manifest = root / "manifest.json"
        review = root / "review.json"
        qualification_file = root / "qualification.json"
        for path, value in (
            (manifest, b"manifest"),
            (review, b"review"),
            (qualification_file, b"qualification"),
        ):
            write_private(path, value)
        qualification = unattended.Qualification(
            transaction_dir=root / "qualification",
            evidence={"qualification": bound(qualification_file)},
            binding_sha256="4" * 64,
        )
        return unattended.UnattendedSpec(
            manifest_path=manifest,
            manifest_sha256=digest(manifest),
            run_id="a90-d1-unattended-20260803-01",
            base_manifest=bound(base.manifest_path),
            base=base,
            qualification=qualification,
            review_receipt=bound(review),
            source_closure={},
            transaction_dir=root / unattended.TRANSACTION_DIR_NAME,
            lock_path=root / unattended.LOCK_NAME,
        )

    def test_presence_proof_does_not_bypass_attended_engine(self) -> None:
        unattended_preflight = SessionPreflight(
            False,
            True,
            True,
            True,
            True,
            unattended_resident_d1_qualified=True,
        )
        unattended_preflight.validate()
        with self.assertRaisesRegex(
            EngineContractError,
            "requires operator attendance",
        ):
            engine.open_attended_session(
                engine.AttendedSessionContract(
                    binding=AttendedSessionBinding(
                        approval_id="attended-test",
                        workflow=Workflow.ATTENDED_SESSION_D1,
                        risk_tier=RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL,
                        target_profile="A90_TEST",
                        manifest_sha256="1" * 64,
                        resident_boot_sha256="2" * 64,
                        rollback_boot_sha256="3" * 64,
                        recovery_profile="A90_RECOVERY",
                        device_effect_runner_sha256="4" * 64,
                        observer_sha256="5" * 64,
                        return_health_profile="A90_HEALTH",
                        action_allowlist=(SessionAction.SWITCHROOT_EXPERIMENT,),
                        not_before_epoch_sec=100,
                        expires_at_epoch_sec=200,
                        max_actions=1,
                    ),
                    successors=(DISPLAY_SUCCESSOR,),
                ),
                engine.ScriptedSessionEffects(()),
                now_epoch_sec=101,
                preflight=unattended_preflight,
            )
        with self.assertRaisesRegex(
            EngineContractError,
            "not safe to continue",
        ):
            SessionPreflight(True, True, True, True, True, True).validate()

    def test_live_effect_presence_is_explicit_and_has_no_session_window(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.direct_spec(root)
            effects = attended.LiveSessionEffects(
                spec.base,
                spec.transaction_dir,
                binding=spec.binding,  # type: ignore[arg-type]
                opening_preflight_evidence={},
                visible_confirmed="unavailable",
                presence_mode=unattended.WORKFLOW,
                enforce_session_window=False,
            )
            proof = effects._healthy_postflight()
            self.assertFalse(proof.operator_attended)
            self.assertTrue(proof.unattended_resident_d1_qualified)
            self.assertIsNone(
                effects._expired_before_dispatch(
                    root,
                    1,
                    spec.binding,  # type: ignore[arg-type]
                )
            )
            with self.assertRaisesRegex(
                attended.ContractError,
                "cannot inherit a session window",
            ):
                attended.LiveSessionEffects(
                    spec.base,
                    spec.transaction_dir,
                    binding=spec.binding,  # type: ignore[arg-type]
                    opening_preflight_evidence={},
                    visible_confirmed="unavailable",
                    presence_mode=unattended.WORKFLOW,
                    enforce_session_window=True,
                )

    def test_transitive_drift_before_dispatch_sends_zero_handoffs(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.direct_spec(root)
            transaction = spec.transaction_dir
            transaction.mkdir()
            changed = dict(spec.base.source_closure)
            original = changed["f1_orchestrator"]
            changed["f1_orchestrator"] = attended.BoundFile(
                original.path,
                original.size,
                "f" * 64 if original.sha256 != "f" * 64 else "e" * 64,
            )
            changed_base = replace(spec.base, source_closure=changed)

            def revalidate() -> None:
                unattended._validate_attended_base_source_closure(
                    changed_base,
                    unattended._source_closure(),
                )

            effects = attended.LiveSessionEffects(
                spec.base,
                transaction,
                binding=spec.binding,  # type: ignore[arg-type]
                opening_preflight_evidence={
                    "resident_health": {"exact": True},
                    "source_preflight": {"exact": True},
                    "rollback_sha256": spec.base.rollback.sha256,
                    "recovery_profile": spec.base.recovery_profile,
                },
                visible_confirmed="unavailable",
                presence_mode=unattended.WORKFLOW,
                enforce_session_window=False,
                pre_dispatch_revalidate=revalidate,
            )
            ok = {"exact": True}
            guard = object()
            with mock.patch.object(
                attended.base,
                "rebind_host_ncm_after_reenumeration",
                return_value=ok,
            ), mock.patch.object(
                attended.base,
                "require_clean_pstore_before_handoff",
                return_value=ok,
            ), mock.patch.object(
                attended.base,
                "settle_observation_channel",
                return_value=ok,
            ), mock.patch.object(
                attended.base,
                "capture_bridge_serial_epoch",
                return_value=ok,
            ), mock.patch.object(
                attended.base,
                "arm_candidate_return_modemmanager_guard",
                return_value=guard,
            ), mock.patch.object(
                attended.base,
                "observe_attended_after_handoff",
            ) as handoff, mock.patch.object(
                attended.base,
                "release_candidate_return_modemmanager_guard",
            ) as release:
                outcome = effects.invoke_action(
                    spec.binding,  # type: ignore[arg-type]
                    1,
                    SessionAction.SWITCHROOT_EXPERIMENT,
                    spec.binding.observer_sha256,
                )
            self.assertEqual(
                outcome.failure_class,
                "PRE_DISPATCH_INTEGRITY_BLOCKED",
            )
            handoff.assert_not_called()
            release.assert_called_once_with(guard, transaction / "action-001")
            with mock.patch.object(unattended, "PRIVATE_ROOT", root.resolve()):
                _, result_evidence, _, dispatch_count = (
                    unattended._validate_persisted_action_evidence(
                        transaction / "action-001",
                        outcome,
                    )
                )
            self.assertIsNone(result_evidence)
            self.assertEqual(dispatch_count, 0)

    def test_persisted_action_evidence_matches_and_counts_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            preflight = SessionPreflight(
                False,
                True,
                True,
                True,
                True,
                unattended_resident_d1_qualified=True,
            )
            proved = engine.SessionActionResult(
                engine.SessionActionStatus.PROVED,
                True,
                postflight=preflight,
            )
            detail = {
                "schema": attended.RESULT_SCHEMA,
                "ordinal": 1,
                "handoff_dispatch_count": 1,
                "resident_healthy": True,
                "proof_terminal": (
                    "PASS_SWITCHROOT_RETURN_NO_PROOF_DISPLAY_VISIBILITY"
                ),
                "candidate_return_observed": True,
                "observation": {
                    "proof": True,
                    "display_mechanical_proof": True,
                    "bounded_display_failure": False,
                },
                "final_health": {"exact": True},
                "payload_transfer": False,
                "partition_write": False,
                "flash": False,
            }
            exact = root / "exact"
            exact.mkdir()
            write_private(
                exact / "engine-outcome.json",
                attended._action_outcome_value(1, proved),
            )
            write_private(exact / "result.json", detail)

            mismatch = root / "mismatch"
            mismatch.mkdir()
            attended_preflight = SessionPreflight(True, True, True, True, True)
            write_private(
                mismatch / "engine-outcome.json",
                attended._action_outcome_value(
                    1,
                    engine.SessionActionResult(
                        engine.SessionActionStatus.PROVED,
                        True,
                        postflight=attended_preflight,
                    ),
                ),
            )
            write_private(mismatch / "result.json", detail)

            malformed = root / "malformed"
            malformed.mkdir()
            write_private(
                malformed / "engine-outcome.json",
                attended._action_outcome_value(1, proved),
            )
            contradictory_detail = dict(detail)
            contradictory_detail["proof_terminal"] = (
                "REFUTED_DISPLAY_ACQUISITION"
            )
            write_private(malformed / "result.json", contradictory_detail)

            pre_dispatch = root / "pre-dispatch"
            pre_dispatch.mkdir()
            blocked = engine.SessionActionResult(
                engine.SessionActionStatus.EXPERIMENT_BLOCKED,
                True,
                failure_class="PRE_DISPATCH_INTEGRITY_BLOCKED",
                postflight=preflight,
            )
            write_private(
                pre_dispatch / "engine-outcome.json",
                attended._action_outcome_value(1, blocked),
            )

            uncertain = root / "uncertain"
            uncertain.mkdir()
            safety_failure = engine.SessionActionResult(
                engine.SessionActionStatus.DEVICE_SAFETY_FAILURE,
                True,
                failure_class="POSTFLIGHT_DEVICE_SAFETY_FAILURE",
            )
            write_private(
                uncertain / "engine-outcome.json",
                attended._action_outcome_value(1, safety_failure),
            )

            with mock.patch.object(unattended, "PRIVATE_ROOT", root.resolve()):
                _, result_evidence, result, dispatch_count = (
                    unattended._validate_persisted_action_evidence(exact, proved)
                )
                self.assertIsNotNone(result_evidence)
                self.assertEqual(result, detail)
                self.assertEqual(dispatch_count, 1)
                with self.assertRaisesRegex(
                    unattended.ContractError,
                    "differs from returned outcome",
                ):
                    unattended._validate_persisted_action_evidence(
                        mismatch,
                        proved,
                    )
                with self.assertRaisesRegex(
                    unattended.ContractError,
                    "durable action result is not exact",
                ):
                    unattended._validate_persisted_action_evidence(
                        malformed,
                        proved,
                    )
                _, pre_result, _, pre_count = (
                    unattended._validate_persisted_action_evidence(
                        pre_dispatch,
                        blocked,
                    )
                )
                self.assertIsNone(pre_result)
                self.assertEqual(pre_count, 0)
                _, unsafe_result, _, unsafe_count = (
                    unattended._validate_persisted_action_evidence(
                        uncertain,
                        safety_failure,
                    )
                )
                self.assertIsNone(unsafe_result)
                self.assertIsNone(unsafe_count)

    def test_manifest_binds_review_and_qualified_prior_return(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            private = root / "private"
            run_base = private / "runs/server-distro"
            base = self.base_spec(private)
            qualification = self.qualification_fixture(private, base)
            review = self.review_receipt(root)
            run_id = "a90-d1-unattended-20260803-01"
            output = run_base / run_id / "manifest.json"
            with mock.patch.object(unattended, "PRIVATE_ROOT", private.resolve()), mock.patch.object(
                unattended,
                "PRIVATE_RUN_BASE",
                run_base.resolve(),
            ), mock.patch.object(
                unattended,
                "REVIEW_RECEIPT_PATH",
                review.resolve(),
            ), mock.patch.object(attended, "load_spec", return_value=base), mock.patch.object(
                attended,
                "_classify_return_observation",
                return_value=(True, {"retained_pmsg": "observer warning"}),
            ):
                value = unattended.build_manifest(
                    base_manifest_path=base.manifest_path,
                    base_manifest_sha256=base.manifest_sha256,
                    qualification_transaction_dir=qualification,
                    review_receipt_path=review,
                    run_id=run_id,
                )
                write_private(output, value)
                spec = unattended.load_spec(output, digest(output))
                inspected = unattended.inspect(spec)
            self.assertEqual(value["workflow"], unattended.WORKFLOW)
            self.assertNotIn("session_duration_sec", json.dumps(value))
            self.assertNotIn("max_actions", json.dumps(value))
            self.assertNotIn("approval_token", json.dumps(value))
            self.assertFalse(value["authority"]["operator_attendance_required"])
            self.assertTrue(value["qualification"]["automatic_native_return_proved"])
            self.assertTrue(inspected["ready_for_fresh_exact_d0"])
            self.assertFalse(inspected["live_authority"])

    def test_capability_pass_go_is_reused_across_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            private = root / "private"
            run_base = private / "runs/server-distro"
            base = self.base_spec(private)
            qualification = self.qualification_fixture(private, base)
            review = self.review_receipt(root)
            with mock.patch.object(
                unattended,
                "PRIVATE_ROOT",
                private.resolve(),
            ), mock.patch.object(
                unattended,
                "PRIVATE_RUN_BASE",
                run_base.resolve(),
            ), mock.patch.object(
                unattended,
                "REVIEW_RECEIPT_PATH",
                review.resolve(),
            ), mock.patch.object(
                attended,
                "load_spec",
                return_value=base,
            ), mock.patch.object(
                attended,
                "_classify_return_observation",
                return_value=(True, {"retained_pmsg": "observer warning"}),
            ):
                first = unattended.build_manifest(
                    base_manifest_path=base.manifest_path,
                    base_manifest_sha256=base.manifest_sha256,
                    qualification_transaction_dir=qualification,
                    review_receipt_path=review,
                    run_id="a90-d1-unattended-20260803-01",
                )
                second = unattended.build_manifest(
                    base_manifest_path=base.manifest_path,
                    base_manifest_sha256=base.manifest_sha256,
                    qualification_transaction_dir=qualification,
                    review_receipt_path=review,
                    run_id="a90-d1-unattended-20260803-02",
                )
            receipt = json.loads(review.read_text(encoding="utf-8"))
            self.assertEqual(first["review_receipt"], second["review_receipt"])
            self.assertEqual(first["source_closure"], second["source_closure"])
            self.assertNotEqual(first["run_id"], second["run_id"])
            self.assertNotEqual(
                first["transaction"]["directory"],
                second["transaction"]["directory"],
            )
            self.assertNotIn("run_id", receipt)
            self.assertNotIn("manifest_sha256", receipt)
            self.assertNotIn("qualification", receipt)
            self.assertNotIn("campaign", receipt)

    def test_transitive_attended_source_change_is_rejected_per_role(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            private = root / "private"
            base = self.base_spec(private)
            capability_sources = unattended._source_closure()
            unattended._validate_attended_base_source_closure(
                base,
                capability_sources,
            )
            transitive_roles = {
                "bridge_selector",
                "cdc_acm_guard",
                "cmdv1_shell_adapter",
                "display_observer",
                "f1_orchestrator",
                "framed_transport",
                "observation_pipeline",
                "serial_lock",
                "serial_tcp_bridge",
                "staging_contract",
                "workspace_bootstrap",
            }
            self.assertTrue(
                transitive_roles.issubset(unattended.ATTENDED_SOURCE_ROLE_MAP)
            )
            for attended_role in sorted(transitive_roles):
                with self.subTest(role=attended_role):
                    changed = dict(base.source_closure)
                    original = changed[attended_role]
                    replacement_sha = (
                        "f" * 64
                        if original.sha256 != "f" * 64
                        else "e" * 64
                    )
                    changed[attended_role] = attended.BoundFile(
                        original.path,
                        original.size,
                        replacement_sha,
                    )
                    changed_base = replace(base, source_closure=changed)
                    with self.assertRaisesRegex(
                        unattended.ContractError,
                        f"base attended source closure differs: {attended_role}",
                    ):
                        unattended._validate_attended_base_source_closure(
                            changed_base,
                            capability_sources,
                        )

    def test_manifest_load_rejects_each_transitive_base_source_change(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            private = root / "private"
            run_base = private / "runs/server-distro"
            base = self.base_spec(private)
            qualification = self.qualification_fixture(private, base)
            review = self.review_receipt(root)
            run_id = "a90-d1-unattended-20260803-01"
            output = run_base / run_id / "manifest.json"
            common_patches = (
                mock.patch.object(unattended, "PRIVATE_ROOT", private.resolve()),
                mock.patch.object(
                    unattended,
                    "PRIVATE_RUN_BASE",
                    run_base.resolve(),
                ),
                mock.patch.object(
                    unattended,
                    "REVIEW_RECEIPT_PATH",
                    review.resolve(),
                ),
                mock.patch.object(
                    attended,
                    "_classify_return_observation",
                    return_value=(True, {"retained_pmsg": "observer warning"}),
                ),
            )
            with (
                common_patches[0],
                common_patches[1],
                common_patches[2],
                common_patches[3],
                mock.patch.object(
                    attended,
                    "load_spec",
                    return_value=base,
                ),
            ):
                value = unattended.build_manifest(
                    base_manifest_path=base.manifest_path,
                    base_manifest_sha256=base.manifest_sha256,
                    qualification_transaction_dir=qualification,
                    review_receipt_path=review,
                    run_id=run_id,
                )
                write_private(output, value)
            transitive_roles = sorted(
                set(attended.SOURCE_PATHS)
                - {"runner", "transition_contract", "transition_engine"}
            )
            for attended_role in transitive_roles:
                with self.subTest(role=attended_role):
                    changed = dict(base.source_closure)
                    original = changed[attended_role]
                    changed[attended_role] = attended.BoundFile(
                        original.path,
                        original.size,
                        "f" * 64 if original.sha256 != "f" * 64 else "e" * 64,
                    )
                    changed_base = replace(base, source_closure=changed)
                    with mock.patch.object(
                        unattended,
                        "PRIVATE_ROOT",
                        private.resolve(),
                    ), mock.patch.object(
                        unattended,
                        "PRIVATE_RUN_BASE",
                        run_base.resolve(),
                    ), mock.patch.object(
                        unattended,
                        "REVIEW_RECEIPT_PATH",
                        review.resolve(),
                    ), mock.patch.object(
                        attended,
                        "load_spec",
                        return_value=changed_base,
                    ), self.assertRaisesRegex(
                        unattended.ContractError,
                        f"base attended source closure differs: {attended_role}",
                    ):
                        unattended.load_spec(output, digest(output))

    def test_execute_writes_intent_before_one_effect_and_refuses_replay(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.direct_spec(root)
            preflight = SessionPreflight(
                False,
                True,
                True,
                True,
                True,
                unattended_resident_d1_qualified=True,
            )
            evidence = {
                "resident_health": {"exact": True},
                "source_preflight": {"exact": True},
                "rollback_sha256": spec.base.rollback.sha256,
                "recovery_profile": spec.base.recovery_profile,
            }
            calls: list[str] = []

            class FakeEffects:
                def __init__(self, *_args, **kwargs):
                    self.transaction = _args[1]
                    self.presence = kwargs["presence_mode"]
                    self.window = kwargs["enforce_session_window"]
                    self.revalidate = kwargs["pre_dispatch_revalidate"]

                def invoke_action(self, binding, ordinal, action, observer):
                    self.assertions(binding, ordinal, action, observer)
                    self.revalidate()
                    calls.append("invoke")
                    action_dir = self.transaction / "action-001"
                    action_dir.mkdir()
                    result = engine.SessionActionResult(
                        engine.SessionActionStatus.PROVED,
                        True,
                        postflight=preflight,
                    )
                    attended.write_private_json_exclusive(
                        action_dir / "engine-outcome.json",
                        attended._action_outcome_value(1, result),
                    )
                    attended.write_private_json_exclusive(
                        action_dir / "result.json",
                        {
                            "schema": attended.RESULT_SCHEMA,
                            "ordinal": 1,
                            "handoff_dispatch_count": 1,
                            "resident_healthy": True,
                            "proof_terminal": (
                                "PASS_SWITCHROOT_RETURN_NO_PROOF_DISPLAY_VISIBILITY"
                            ),
                            "candidate_return_observed": True,
                            "observation": {
                                "proof": True,
                                "display_mechanical_proof": True,
                                "bounded_display_failure": False,
                            },
                            "final_health": {"exact": True},
                            "payload_transfer": False,
                            "partition_write": False,
                            "flash": False,
                        },
                    )
                    return result

                def assertions(self, binding, ordinal, action, observer):
                    self_test.assertTrue(
                        (
                            self.transaction
                            / "journal/0000-ordinal-001-intent.json"
                        ).is_file()
                    )
                    self_test.assertEqual(binding, spec.binding)
                    self_test.assertEqual(ordinal, 1)
                    self_test.assertIs(action, SessionAction.SWITCHROOT_EXPERIMENT)
                    self_test.assertEqual(observer, binding.observer_sha256)
                    self_test.assertEqual(self.presence, unattended.WORKFLOW)
                    self_test.assertFalse(self.window)

            self_test = self
            with mock.patch.object(unattended, "PRIVATE_ROOT", root.resolve()), mock.patch.object(
                attended,
                "resident_d0_preflight",
                return_value=(preflight, evidence),
            ), mock.patch.object(
                unattended,
                "_revalidate_execution_closure",
            ) as revalidate, mock.patch.object(attended, "LiveSessionEffects", FakeEffects):
                result = unattended.execute(spec)
                with self.assertRaisesRegex(unattended.ContractError, "replay forbidden"):
                    unattended.execute(spec)
            self.assertEqual(calls, ["invoke"])
            self.assertEqual(revalidate.call_count, 2)
            self.assertEqual(result["terminal"], "ORDINAL_CLOSED_RESIDENT_HEALTHY")
            self.assertEqual(result["device_safety_state"], "RESIDENT_HEALTHY")
            self.assertFalse(result["operator_attended"])
            self.assertTrue(result["next_ordinal_permitted"])
            self.assertEqual(result["handoff_dispatch_count"], 1)
            self.assertTrue(result["durable_engine_outcome_validated"])
            self.assertTrue(result["durable_action_result_validated"])
            journal = sorted((spec.transaction_dir / "journal").glob("*.json"))
            self.assertEqual(len(journal), 2)
            joined = "\n".join(path.read_text(encoding="utf-8") for path in journal)
            self.assertNotIn('"operator_attended": true', joined)
            self.assertNotIn("approval_token\": true", joined)

    def test_uncertain_effect_parks_and_never_retries(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.direct_spec(root)
            preflight = SessionPreflight(
                False,
                True,
                True,
                True,
                True,
                unattended_resident_d1_qualified=True,
            )
            evidence = {
                "resident_health": {},
                "source_preflight": {},
                "rollback_sha256": spec.base.rollback.sha256,
                "recovery_profile": spec.base.recovery_profile,
            }

            class RaisingEffects:
                calls = 0

                def __init__(self, *_args, **_kwargs):
                    self.transaction = _args[1]
                    self.revalidate = _kwargs["pre_dispatch_revalidate"]

                def invoke_action(self, *_args):
                    self.revalidate()
                    type(self).calls += 1
                    action_dir = self.transaction / "action-001"
                    action_dir.mkdir()
                    attended.write_private_json_exclusive(
                        action_dir / "handoff-intent.json",
                        {"dispatch_count_max": 1},
                    )
                    raise RuntimeError("uncertain after durable handoff intent")

            with mock.patch.object(unattended, "PRIVATE_ROOT", root.resolve()), mock.patch.object(
                attended,
                "resident_d0_preflight",
                return_value=(preflight, evidence),
            ), mock.patch.object(
                unattended,
                "_revalidate_execution_closure",
            ) as revalidate, mock.patch.object(attended, "LiveSessionEffects", RaisingEffects):
                result = unattended.execute(spec)
                with self.assertRaisesRegex(unattended.ContractError, "replay forbidden"):
                    unattended.execute(spec)
            self.assertEqual(RaisingEffects.calls, 1)
            self.assertEqual(revalidate.call_count, 2)
            self.assertEqual(result["terminal"], "RECOVERY_PENDING_PARKED")
            self.assertFalse(result["next_ordinal_permitted"])
            self.assertTrue(result["handoff_intent_present"])

    def test_failed_fresh_d0_creates_no_transaction_or_effect(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.direct_spec(root)
            with mock.patch.object(unattended, "PRIVATE_ROOT", root.resolve()), mock.patch.object(
                attended,
                "resident_d0_preflight",
                side_effect=attended.ContractError("identity mismatch"),
            ) as preflight, mock.patch.object(
                unattended,
                "_revalidate_execution_closure",
            ) as revalidate, mock.patch.object(
                attended,
                "LiveSessionEffects",
            ) as effects, self.assertRaisesRegex(
                unattended.ContractError,
                "fresh exact unattended D0 failed",
            ):
                unattended.execute(spec)
            preflight.assert_called_once_with(
                spec.base,
                unattended_qualified=True,
            )
            revalidate.assert_not_called()
            effects.assert_not_called()
            self.assertFalse(spec.transaction_dir.exists())

    def test_post_effect_packaging_failure_parks_without_replay(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self.direct_spec(root)
            preflight = SessionPreflight(
                False,
                True,
                True,
                True,
                True,
                unattended_resident_d1_qualified=True,
            )
            evidence = {
                "resident_health": {},
                "source_preflight": {},
                "rollback_sha256": spec.base.rollback.sha256,
                "recovery_profile": spec.base.recovery_profile,
            }

            class InvalidOutcomeEffects:
                calls = 0

                def __init__(self, *_args, **_kwargs):
                    self.transaction = _args[1]

                def invoke_action(self, *_args):
                    type(self).calls += 1
                    (self.transaction / "action-001").mkdir()
                    return object()

            with mock.patch.object(unattended, "PRIVATE_ROOT", root.resolve()), mock.patch.object(
                attended,
                "resident_d0_preflight",
                return_value=(preflight, evidence),
            ), mock.patch.object(
                unattended,
                "_revalidate_execution_closure",
            ), mock.patch.object(
                attended,
                "LiveSessionEffects",
                InvalidOutcomeEffects,
            ):
                result = unattended.execute(spec)
                with self.assertRaisesRegex(unattended.ContractError, "replay forbidden"):
                    unattended.execute(spec)
            self.assertEqual(InvalidOutcomeEffects.calls, 1)
            self.assertEqual(result["terminal"], "RECOVERY_PENDING_PARKED")
            self.assertTrue(result["effect_result_available"])
            self.assertFalse(result["evidence_packaging_complete"])
            self.assertFalse(result["next_ordinal_permitted"])

    def test_qualification_mutation_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            private = root / "private"
            base = self.base_spec(private)
            qualification = self.qualification_fixture(private, base)
            visible_path = (
                qualification
                / "action-001/operator-display-observation.json"
            )
            with mock.patch.object(unattended, "PRIVATE_ROOT", private.resolve()), mock.patch.object(
                attended,
                "_classify_return_observation",
                return_value=(True, {}),
            ):
                first = unattended._validate_qualification(base, qualification)
                value = json.loads(visible_path.read_text(encoding="utf-8"))
                value["display_visible"] = False
                write_private(visible_path, value)
                with self.assertRaisesRegex(
                    unattended.ContractError,
                    "operator visibility",
                ):
                    unattended._validate_qualification(base, qualification)
            self.assertRegex(first.binding_sha256, r"^[0-9a-f]{64}$")

    def test_malformed_nested_qualification_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            private = root / "private"
            base = self.base_spec(private)
            qualification = self.qualification_fixture(private, base)
            manifest_path = qualification.parent / "manifest.json"
            value = json.loads(manifest_path.read_text(encoding="utf-8"))
            value["resident"]["candidate"] = "malformed"
            write_private(manifest_path, value)
            with mock.patch.object(
                unattended,
                "PRIVATE_ROOT",
                private.resolve(),
            ), self.assertRaisesRegex(
                unattended.ContractError,
                "resident binding differs",
            ):
                unattended._validate_qualification(base, qualification)

    def test_cli_has_no_attendance_assertion_or_automatic_loop(self) -> None:
        parser = unattended.build_parser()
        option_strings = {
            option
            for action in parser._actions
            for option in action.option_strings
        }
        self.assertNotIn("--operator-attended", option_strings)
        self.assertNotIn("--resume-session", option_strings)
        self.assertNotIn("--approval", option_strings)
        self.assertNotIn("--max-actions", option_strings)
        self.assertNotIn("--session-duration-sec", option_strings)
        self.assertIn("--execute-switchroot", option_strings)

    def test_runner_has_no_direct_transfer_reboot_or_other_target_path(self) -> None:
        source = Path(unattended.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        self.assertNotIn("subprocess", imported_modules)
        for forbidden in (
            "fastboot",
            "heimdall",
            "SM-S906",
            "S22PLUS",
            "reboot",
        ):
            self.assertNotIn(forbidden, source)

    def test_noncanonical_review_receipt_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            review = self.review_receipt(root)
            with self.assertRaisesRegex(
                unattended.ContractError,
                "path is not canonical",
            ):
                unattended._validate_review_receipt(
                    review,
                    unattended._source_closure(),
                )


if __name__ == "__main__":
    unittest.main()
