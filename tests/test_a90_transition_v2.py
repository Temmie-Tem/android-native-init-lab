from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
REVAL_DIR = REPO_ROOT / "workspace/public/src/scripts/revalidation"
SERVER_DIR = REPO_ROOT / "workspace/public/src/scripts/server-distro"
for directory in (REVAL_DIR, SERVER_DIR):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

import a90_transition_contract_v2 as contract  # noqa: E402
import a90_transition_engine_v2 as engine  # noqa: E402
import a90_transition_v2 as cli  # noqa: E402


SESSION_START_EPOCH_SEC = 2_000_000_000


def approval(
    workflow: contract.Workflow,
    approval_id: str = "approval-1",
) -> contract.ApprovalBinding:
    tier = (
        contract.RiskTier.F1_BOOT_ONLY_WITH_EXACT_ROLLBACK
        if workflow is contract.Workflow.RESIDENT_INSTALL_F1
        else contract.RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL
    )
    return contract.ApprovalBinding(
        approval_id=approval_id,
        workflow=workflow,
        risk_tier=tier,
        target_profile="A90_TEST_ONLY",
        manifest_sha256="1" * 64,
    )


def run_contract(
    workflow: contract.Workflow,
    **kwargs: object,
) -> engine.RunContract:
    return engine.RunContract(
        approval=approval(workflow),
        successors=(contract.DISPLAY_SUCCESSOR,),
        **kwargs,
    )


def session_binding(**overrides: object) -> contract.AttendedSessionBinding:
    values: dict[str, object] = {
        "approval_id": "session-approval-1",
        "workflow": contract.Workflow.ATTENDED_SESSION_D1,
        "risk_tier": contract.RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL,
        "target_profile": "A90_TEST_ONLY",
        "manifest_sha256": "1" * 64,
        "resident_boot_sha256": "2" * 64,
        "rollback_boot_sha256": "3" * 64,
        "recovery_profile": "A90_TEST_RECOVERY",
        "device_effect_runner_sha256": "4" * 64,
        "observer_sha256": "5" * 64,
        "return_health_profile": "A90_TEST_HEALTH",
        "action_allowlist": (contract.SessionAction.SWITCHROOT_EXPERIMENT,),
        "not_before_epoch_sec": SESSION_START_EPOCH_SEC,
        "expires_at_epoch_sec": (
            SESSION_START_EPOCH_SEC + contract.MAX_ATTENDED_SESSION_DURATION_SEC
        ),
        "max_actions": 3,
    }
    values.update(overrides)
    return contract.AttendedSessionBinding(**values)  # type: ignore[arg-type]


def session_contract(
    *,
    previous_refutations: tuple[contract.ConfirmedRefutation, ...] = (),
    **overrides: object,
) -> engine.AttendedSessionContract:
    return engine.AttendedSessionContract(
        binding=session_binding(**overrides),
        successors=(contract.DISPLAY_SUCCESSOR,),
        previous_refutations=previous_refutations,
    )


def safe_session_preflight() -> contract.SessionPreflight:
    return contract.SessionPreflight(
        operator_attended=True,
        target_identity_matches=True,
        resident_identity_matches=True,
        rollback_ready=True,
        recovery_available=True,
    )


def proved_action() -> engine.SessionActionResult:
    return engine.SessionActionResult(
        engine.SessionActionStatus.PROVED,
        action_started=True,
        postflight=safe_session_preflight(),
    )


def open_session(
    exact: engine.AttendedSessionContract,
    effects: engine.ScriptedSessionEffects,
) -> engine.AttendedSession:
    return engine.open_attended_session(
        exact,
        effects,
        now_epoch_sec=SESSION_START_EPOCH_SEC,
        preflight=safe_session_preflight(),
    )


class A90TransitionV2Tests(unittest.TestCase):
    def test_risk_and_legacy_stage_names_are_unambiguous(self) -> None:
        self.assertEqual(
            contract.RiskTier.TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL.value,
            "TIER_D1_TRANSIENT_NO_PAYLOAD_CONTROL",
        )
        self.assertEqual(
            contract.LegacyStage.STAGE_D1_CHROOT_MVP.value,
            "STAGE_D1_CHROOT_MVP",
        )
        bad = contract.ApprovalBinding(
            approval_id="bad-tier",
            workflow=contract.Workflow.SWITCHROOT_EXPERIMENT_D1,
            risk_tier=contract.RiskTier.F1_BOOT_ONLY_WITH_EXACT_ROLLBACK,
            target_profile="A90_TEST_ONLY",
            manifest_sha256="1" * 64,
        )
        with self.assertRaisesRegex(contract.ContractError, "not namespaced"):
            bad.validate()

    def test_successor_gate_requires_release_and_acquisition(self) -> None:
        contract.validate_successor_contracts((contract.DISPLAY_SUCCESSOR,))
        missing = contract.SuccessorContract(
            domain="display",
            predecessor_owner="native_init",
            predecessor_release_proof="native_release",
            successor_owner="debian_presenter",
            successor_acquisition_proofs=(),
        )
        with self.assertRaisesRegex(contract.ContractError, "lacks release"):
            contract.validate_successor_contracts((missing,))
        with self.assertRaisesRegex(contract.ContractError, "duplicated"):
            contract.validate_successor_contracts(
                (contract.DISPLAY_SUCCESSOR, contract.DISPLAY_SUCCESSOR)
            )

    def test_resident_success_uses_one_candidate_and_no_rollback(self) -> None:
        effects = engine.ScriptedEffects({})
        result = engine.execute_workflow(
            run_contract(contract.Workflow.RESIDENT_INSTALL_F1),
            effects,
        )
        self.assertEqual(result["terminal"], "PASS_A90_RESIDENT_INSTALLED")
        self.assertEqual(result["counts"]["CANDIDATE_FLASH"], 1)
        self.assertNotIn("RESIDENT_REBOOT", result["counts"])
        self.assertEqual(result["device_safety_state"], "RESIDENT_HEALTHY")
        self.assertNotIn("ROLLBACK_FLASH", result["counts"])
        self.assertFalse(result["candidate_replay"])
        self.assertTrue(effects.events[0].startswith("APPROVAL_CONSUME:"))
        for index in range(1, len(effects.events), 2):
            self.assertTrue(effects.events[index].startswith("INTENT:"))
            self.assertTrue(effects.events[index + 1].startswith("EFFECT:"))

    def test_post_candidate_failure_rolls_back_once_without_replay(self) -> None:
        effects = engine.ScriptedEffects(
            {
                "CANDIDATE_HEALTH": engine.EffectResult(
                    engine.EffectStatus.FAIL,
                    effect_started=True,
                    failure_class="CANDIDATE_HEALTH_FAILED",
                )
            }
        )
        result = engine.execute_workflow(
            run_contract(contract.Workflow.RESIDENT_INSTALL_F1),
            effects,
        )
        self.assertEqual(result["terminal"], "ROLLED_BACK_CLOSED")
        self.assertEqual(result["counts"]["CANDIDATE_FLASH"], 1)
        self.assertEqual(result["counts"]["ROLLBACK_FLASH"], 1)
        self.assertEqual(result["counts"]["ROLLBACK_HEALTH"], 1)

    def test_candidate_pass_cannot_hide_started_effect_from_rollback(self) -> None:
        effects = engine.ScriptedEffects(
            {
                "CANDIDATE_FLASH": engine.EffectResult(
                    engine.EffectStatus.PASS,
                    effect_started=False,
                ),
                "CANDIDATE_HEALTH": engine.EffectResult(
                    engine.EffectStatus.FAIL,
                    effect_started=False,
                    failure_class="CANDIDATE_HEALTH_FAILED",
                ),
            }
        )
        result = engine.execute_workflow(
            run_contract(contract.Workflow.RESIDENT_INSTALL_F1),
            effects,
        )
        self.assertEqual(result["terminal"], "ROLLED_BACK_CLOSED")
        self.assertEqual(result["counts"]["ROLLBACK_FLASH"], 1)

    def test_ambiguous_started_flash_also_uses_only_rollback(self) -> None:
        effects = engine.ScriptedEffects(
            {
                "CANDIDATE_FLASH": engine.EffectResult(
                    engine.EffectStatus.AMBIGUOUS,
                    effect_started=True,
                    failure_class="CANDIDATE_TRANSFER_AMBIGUOUS",
                )
            }
        )
        result = engine.execute_workflow(
            run_contract(contract.Workflow.RESIDENT_INSTALL_F1),
            effects,
        )
        self.assertEqual(result["terminal"], "ROLLED_BACK_CLOSED")
        self.assertIn("STOP_AMBIGUOUS", result["history"])
        self.assertEqual(result["counts"]["CANDIDATE_FLASH"], 1)
        self.assertEqual(result["counts"]["ROLLBACK_FLASH"], 1)

    def test_candidate_effect_exception_is_ambiguous_and_rolls_back(self) -> None:
        class RaisingEffects(engine.ScriptedEffects):
            def invoke(
                self,
                workflow: contract.Workflow,
                phase: str,
            ) -> engine.EffectResult:
                if phase == "CANDIDATE_FLASH":
                    raise RuntimeError("transport result unavailable")
                return super().invoke(workflow, phase)

        effects = RaisingEffects({})
        result = engine.execute_workflow(
            run_contract(contract.Workflow.RESIDENT_INSTALL_F1),
            effects,
        )
        self.assertEqual(result["terminal"], "ROLLED_BACK_CLOSED")
        self.assertEqual(
            result["failure_signature"]["failure_class"],
            "EFFECT_EXCEPTION_AMBIGUOUS",
        )
        self.assertEqual(result["counts"]["ROLLBACK_FLASH"], 1)

    def test_malformed_candidate_result_cannot_suppress_rollback(self) -> None:
        effects = engine.ScriptedEffects(
            {
                "CANDIDATE_FLASH": engine.EffectResult(
                    engine.EffectStatus.PASS,
                    effect_started=False,
                    failure_class="CONTRADICTORY_PASS",
                )
            }
        )
        result = engine.execute_workflow(
            run_contract(contract.Workflow.RESIDENT_INSTALL_F1),
            effects,
        )
        self.assertEqual(result["terminal"], "ROLLED_BACK_CLOSED")
        self.assertEqual(result["counts"]["ROLLBACK_FLASH"], 1)
        self.assertEqual(
            result["failure_signature"]["failure_class"],
            "EFFECT_EXCEPTION_AMBIGUOUS",
        )

    def test_intent_failure_never_invokes_effect_and_recovers_after_candidate(
        self,
    ) -> None:
        class IntentFailureEffects(engine.ScriptedEffects):
            def record_intent(
                self,
                workflow: contract.Workflow,
                phase: str,
            ) -> None:
                if phase == "CANDIDATE_HEALTH":
                    raise OSError("journal unavailable")
                super().record_intent(workflow, phase)

        effects = IntentFailureEffects({})
        result = engine.execute_workflow(
            run_contract(contract.Workflow.RESIDENT_INSTALL_F1),
            effects,
        )
        self.assertEqual(result["terminal"], "ROLLED_BACK_CLOSED")
        self.assertEqual(result["counts"]["CANDIDATE_FLASH"], 1)
        self.assertEqual(result["counts"]["ROLLBACK_FLASH"], 1)
        self.assertEqual(result["counts"]["CANDIDATE_HEALTH_INTENT_FAILURE"], 1)
        self.assertFalse(
            any(event.endswith(":CANDIDATE_HEALTH") for event in effects.events)
        )

    def test_rollback_intent_failure_is_recovery_required(self) -> None:
        class RollbackIntentFailureEffects(engine.ScriptedEffects):
            def record_intent(
                self,
                workflow: contract.Workflow,
                phase: str,
            ) -> None:
                if phase == "ROLLBACK_FLASH":
                    raise OSError("journal unavailable")
                super().record_intent(workflow, phase)

        effects = RollbackIntentFailureEffects(
            {
                "CANDIDATE_HEALTH": engine.EffectResult(
                    engine.EffectStatus.FAIL,
                    effect_started=True,
                    failure_class="CANDIDATE_HEALTH_FAILED",
                )
            }
        )
        result = engine.execute_workflow(
            run_contract(contract.Workflow.RESIDENT_INSTALL_F1),
            effects,
        )
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertNotIn("ROLLBACK_FLASH", result["counts"])
        self.assertEqual(result["counts"]["ROLLBACK_FLASH_INTENT_FAILURE"], 1)

    def test_pre_candidate_nonstarted_failure_never_rolls_back(self) -> None:
        effects = engine.ScriptedEffects(
            {
                "CANDIDATE_FLASH": engine.EffectResult(
                    engine.EffectStatus.FAIL,
                    effect_started=False,
                    failure_class="LOCAL_PARSE_REJECTED",
                )
            }
        )
        result = engine.execute_workflow(
            run_contract(contract.Workflow.RESIDENT_INSTALL_F1),
            effects,
        )
        self.assertEqual(result["terminal"], "ABORTED_BEFORE_CANDIDATE")
        self.assertNotIn("ROLLBACK_FLASH", result["counts"])

    def test_d1_has_no_payload_effect_and_preserves_visibility_boundary(self) -> None:
        visible = cli.simulate("d1-visible")
        unattended = cli.simulate("d1-unattended")
        self.assertEqual(
            visible["result"]["terminal"],
            "PASS_SWITCHROOT_RETURN_VISIBLE",
        )
        self.assertEqual(
            unattended["result"]["terminal"],
            "PASS_SWITCHROOT_RETURN_NO_PROOF_DISPLAY_VISIBILITY",
        )
        forbidden = {"CANDIDATE_FLASH", "ROLLBACK_FLASH", "RESIDENT_REBOOT"}
        self.assertTrue(forbidden.isdisjoint(visible["result"]["counts"]))

    def test_display_proof_and_ambiguity_are_separate_failures(self) -> None:
        display = cli.simulate("d1-display-failure")["result"]
        ambiguous = cli.simulate("d1-return-ambiguous")["result"]
        self.assertEqual(display["terminal"], "STOPPED_NO_RETRY")
        self.assertEqual(
            display["failure_signature"]["failure_class"],
            "MODESET_COMMITTED_REFUTED",
        )
        self.assertEqual(display["counts"]["NATIVE_RETURN"], 1)
        self.assertEqual(display["counts"]["WORK_CLEANUP"], 1)
        self.assertEqual(display["counts"]["FINAL_HEALTH"], 1)
        self.assertEqual(ambiguous["terminal"], "STOP_AMBIGUOUS")
        self.assertEqual(
            ambiguous["failure_signature"]["failure_class"],
            "RETURN_CHANNEL_AMBIGUOUS",
        )

    def test_ambiguous_status_is_canonicalized_for_prepare_gate(self) -> None:
        effects = engine.ScriptedEffects(
            {
                "HANDOFF": engine.EffectResult(
                    engine.EffectStatus.AMBIGUOUS,
                    effect_started=True,
                    failure_class="RETURN_UNCERTAIN",
                )
            }
        )
        result = engine.execute_workflow(
            run_contract(contract.Workflow.SWITCHROOT_EXPERIMENT_D1),
            effects,
        )
        self.assertEqual(result["terminal"], "STOP_AMBIGUOUS")
        signature = contract.FailureSignature(**result["failure_signature"])
        self.assertEqual(
            signature.failure_class,
            "EFFECT_EXCEPTION_AMBIGUOUS",
        )
        self.assertEqual(
            contract.repeated_failure_gate((signature,)),
            "STOP_AMBIGUOUS_FAILURE_SIGNATURE",
        )

    def test_malformed_observation_recovers_return_cleanup_and_health(self) -> None:
        effects = engine.ScriptedEffects(
            {
                "DEBIAN_OBSERVATION": engine.EffectResult(
                    engine.EffectStatus.PASS,
                    effect_started=False,
                    evidence={"native_release": "PROVEN"},
                )
            }
        )
        result = engine.execute_workflow(
            run_contract(contract.Workflow.SWITCHROOT_EXPERIMENT_D1),
            effects,
        )
        self.assertEqual(result["terminal"], "STOP_AMBIGUOUS")
        self.assertEqual(
            result["failure_signature"]["failure_class"],
            "OBSERVATION_EVIDENCE_AMBIGUOUS",
        )
        self.assertEqual(
            result["failure_signature"]["last_proven_boundary"],
            "DEBIAN_OBSERVATION_CAPTURED",
        )
        self.assertEqual(result["counts"]["NATIVE_RETURN"], 1)
        self.assertEqual(result["counts"]["WORK_CLEANUP"], 1)
        self.assertEqual(result["counts"]["FINAL_HEALTH"], 1)

    def test_incoherent_visibility_source_is_canonical_ambiguity(self) -> None:
        evidence = cli._display_evidence(contract.ProofState.UNAVAILABLE)
        evidence["visibility_source"] = "operator"
        effects = engine.ScriptedEffects(
            {
                "DEBIAN_OBSERVATION": engine.EffectResult(
                    engine.EffectStatus.PASS,
                    effect_started=False,
                    evidence=evidence,
                )
            }
        )
        result = engine.execute_workflow(
            run_contract(contract.Workflow.SWITCHROOT_EXPERIMENT_D1),
            effects,
        )
        self.assertEqual(result["terminal"], "STOP_AMBIGUOUS")
        self.assertEqual(
            result["failure_signature"]["failure_class"],
            "OBSERVATION_EVIDENCE_AMBIGUOUS",
        )
        self.assertEqual(result["counts"]["FINAL_HEALTH"], 1)

    def test_deferred_ambiguity_survives_later_return_failure(self) -> None:
        effects = engine.ScriptedEffects(
            {
                "DEBIAN_OBSERVATION": engine.EffectResult(
                    engine.EffectStatus.PASS,
                    effect_started=False,
                    evidence={"native_release": "PROVEN"},
                ),
                "NATIVE_RETURN": engine.EffectResult(
                    engine.EffectStatus.FAIL,
                    effect_started=False,
                    failure_class="RETURN_FAILED",
                ),
            }
        )
        result = engine.execute_workflow(
            run_contract(contract.Workflow.SWITCHROOT_EXPERIMENT_D1),
            effects,
        )
        self.assertEqual(result["terminal"], "STOP_AMBIGUOUS")
        self.assertEqual(
            result["failure_signature"]["failure_class"],
            "OBSERVATION_EVIDENCE_AMBIGUOUS",
        )
        self.assertEqual(
            result["secondary_failure_signatures"][0]["failure_class"],
            "RETURN_FAILED",
        )
        signature = contract.FailureSignature(**result["failure_signature"])
        self.assertEqual(
            contract.repeated_failure_gate((signature,)),
            "STOP_AMBIGUOUS_FAILURE_SIGNATURE",
        )

    def test_started_ambiguous_handoff_still_attempts_bounded_return(self) -> None:
        effects = engine.ScriptedEffects(
            {
                "HANDOFF": engine.EffectResult(
                    engine.EffectStatus.AMBIGUOUS,
                    effect_started=True,
                    failure_class="HANDOFF_RESULT_AMBIGUOUS",
                ),
                "DEBIAN_OBSERVATION": engine.EffectResult(
                    engine.EffectStatus.FAIL,
                    effect_started=False,
                    failure_class="DEBIAN_NOT_OBSERVED",
                ),
            }
        )
        result = engine.execute_workflow(
            run_contract(contract.Workflow.SWITCHROOT_EXPERIMENT_D1),
            effects,
        )
        self.assertEqual(result["terminal"], "STOP_AMBIGUOUS")
        self.assertEqual(
            result["failure_signature"]["failure_class"],
            "HANDOFF_RESULT_AMBIGUOUS",
        )
        self.assertEqual(result["counts"]["NATIVE_RETURN"], 1)
        self.assertEqual(result["counts"]["WORK_CLEANUP"], 1)
        self.assertEqual(result["counts"]["FINAL_HEALTH"], 1)

    def test_non_enum_ambiguous_status_cannot_bypass_prepare_stop(self) -> None:
        malformed = engine.EffectResult(
            "AMBIGUOUS",  # type: ignore[arg-type]
            effect_started=True,
            failure_class="RETURN_UNCERTAIN",
        )
        effects = engine.ScriptedEffects({"HANDOFF": malformed})
        result = engine.execute_workflow(
            run_contract(contract.Workflow.SWITCHROOT_EXPERIMENT_D1),
            effects,
        )
        self.assertEqual(result["terminal"], "STOP_AMBIGUOUS")
        signature = contract.FailureSignature(**result["failure_signature"])
        self.assertEqual(
            signature.failure_class,
            "EFFECT_EXCEPTION_AMBIGUOUS",
        )
        self.assertEqual(
            contract.repeated_failure_gate((signature,)),
            "STOP_AMBIGUOUS_FAILURE_SIGNATURE",
        )

    def test_d1_approval_is_fresh_and_repeat_gate_stops_after_two(self) -> None:
        with self.assertRaisesRegex(contract.ContractError, "not fresh"):
            engine.execute_workflow(
                run_contract(
                    contract.Workflow.SWITCHROOT_EXPERIMENT_D1,
                    consumed_approval_ids=frozenset({"approval-1"}),
                ),
                engine.ScriptedEffects({}),
            )

        exact = run_contract(contract.Workflow.SWITCHROOT_EXPERIMENT_D1)
        evidence = cli._display_evidence(contract.ProofState.UNAVAILABLE)
        effects = engine.ScriptedEffects(
            {
                "DEBIAN_OBSERVATION": engine.EffectResult(
                    engine.EffectStatus.PASS,
                    effect_started=False,
                    evidence=evidence,
                )
            }
        )
        first = engine.execute_workflow(exact, effects)
        self.assertEqual(
            first["terminal"],
            "PASS_SWITCHROOT_RETURN_NO_PROOF_DISPLAY_VISIBILITY",
        )
        with self.assertRaisesRegex(contract.ContractError, "already consumed"):
            engine.execute_workflow(exact, effects)
        self.assertEqual(first["counts"]["HANDOFF"], 1)
        self.assertEqual(
            sum(event.endswith(":HANDOFF") for event in effects.events),
            2,
        )
        signature = contract.FailureSignature(
            workflow=contract.Workflow.SWITCHROOT_EXPERIMENT_D1.value,
            phase="NATIVE_RETURN",
            failure_class="RETURN_TIMEOUT",
            effect_started=True,
            last_proven_boundary="DEBIAN_OBSERVATION_PROVEN",
        )
        self.assertEqual(
            contract.repeated_failure_gate((signature, signature)),
            "STOP_REPEATED_FAILURE_SIGNATURE",
        )
        with self.assertRaisesRegex(
            contract.ContractError,
            "STOP_REPEATED_FAILURE_SIGNATURE",
        ):
            engine.execute_workflow(
                run_contract(
                    contract.Workflow.SWITCHROOT_EXPERIMENT_D1,
                    previous_failure_signatures=(signature, signature),
                ),
                engine.ScriptedEffects({}),
            )
        ambiguous = contract.FailureSignature(
            workflow=contract.Workflow.SWITCHROOT_EXPERIMENT_D1.value,
            phase="NATIVE_RETURN",
            failure_class="RETURN_CHANNEL_AMBIGUOUS",
            effect_started=False,
            last_proven_boundary="DEBIAN_OBSERVATION_PROVEN",
        )
        self.assertEqual(
            contract.repeated_failure_gate((ambiguous,)),
            "STOP_AMBIGUOUS_FAILURE_SIGNATURE",
        )
        with self.assertRaisesRegex(
            contract.ContractError,
            "STOP_AMBIGUOUS_FAILURE_SIGNATURE",
        ):
            engine.execute_workflow(
                run_contract(
                    contract.Workflow.SWITCHROOT_EXPERIMENT_D1,
                    previous_failure_signatures=(ambiguous,),
                ),
                engine.ScriptedEffects({}),
            )

    def test_attended_session_binding_is_exact_and_bounded(self) -> None:
        binding = session_binding()
        self.assertIs(
            contract.validate_attended_session_binding(binding),
            binding,
        )
        for bad, message in (
            (
                replace(
                    binding,
                    expires_at_epoch_sec=(
                        binding.not_before_epoch_sec
                        + contract.MAX_ATTENDED_SESSION_DURATION_SEC
                        + 1
                    ),
                ),
                "eight-hour",
            ),
            (
                replace(
                    binding,
                    max_actions=contract.MAX_ATTENDED_SESSION_ACTIONS + 1,
                ),
                "32-action",
            ),
            (replace(binding, action_allowlist=()), "allowlist"),
            (
                replace(
                    binding,
                    action_allowlist=(
                        contract.SessionAction.SWITCHROOT_EXPERIMENT,
                        contract.SessionAction.SWITCHROOT_EXPERIMENT,
                    ),
                ),
                "allowlist",
            ),
            (
                replace(binding, workflow=contract.Workflow.RESIDENT_INSTALL_F1),
                "workflow",
            ),
            (replace(binding, rollback_boot_sha256="bad"), "rollback boot"),
            (replace(binding, observer_sha256="bad"), "observer"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(contract.ContractError, message):
                    contract.validate_attended_session_binding(bad)

    def test_attended_session_consumes_one_approval_for_multiple_actions(self) -> None:
        effects = engine.ScriptedSessionEffects(
            (
                proved_action(),
                engine.SessionActionResult(
                    engine.SessionActionStatus.REFUTED,
                    action_started=True,
                    failure_class="DISPLAY_VISIBILITY_REFUTED",
                    postflight=safe_session_preflight(),
                ),
            )
        )
        session = open_session(session_contract(), effects)
        first = session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=safe_session_preflight(),
        )
        second = session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 2,
            preflight=safe_session_preflight(),
        )
        self.assertEqual(first["terminal"], "SESSION_ACTIVE")
        self.assertEqual(second["terminal"], "SESSION_ACTIVE")
        self.assertEqual(second["actions_used"], 2)
        self.assertEqual(second["actions_remaining"], 1)
        self.assertFalse(second["candidate_transfer"])
        self.assertFalse(second["rollback_transfer"])
        self.assertFalse(second["payload_transfer"])
        self.assertEqual(effects.invoke_count, 2)
        self.assertEqual(
            sum(event.startswith("SESSION_APPROVAL_CONSUME:") for event in effects.events),
            1,
        )

    def test_observer_no_proof_keeps_session_without_action_resend(self) -> None:
        effects = engine.ScriptedSessionEffects(
            (
                engine.SessionActionResult(
                    engine.SessionActionStatus.NO_PROOF_OBSERVER,
                    action_started=True,
                    failure_class="RETURN_FRAME_OBSERVER",
                    postflight=safe_session_preflight(),
                    independent_safety_check=True,
                ),
            )
        )
        session = open_session(session_contract(), effects)
        result = session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=safe_session_preflight(),
        )
        self.assertEqual(
            result["terminal"],
            "SESSION_PAUSED_OBSERVER_REPAIR_REQUIRED",
        )
        self.assertFalse(result["session_active"])
        self.assertTrue(result["session_open"])
        self.assertTrue(result["observer_repair_required"])
        self.assertEqual(
            result["action_results"][0]["status"],
            "NO_PROOF_OBSERVER",
        )
        self.assertEqual(effects.invoke_count, 1)
        self.assertEqual(
            sum(event.startswith("SESSION_EFFECT:") for event in effects.events),
            1,
        )
        with self.assertRaisesRegex(contract.ContractError, "observer repair"):
            session.run_action(
                contract.SessionAction.SWITCHROOT_EXPERIMENT,
                now_epoch_sec=SESSION_START_EPOCH_SEC + 2,
                preflight=safe_session_preflight(),
            )
        self.assertEqual(effects.invoke_count, 1)

    def test_validated_observer_repair_resumes_without_replaying_action(self) -> None:
        no_proof = engine.SessionActionResult(
            engine.SessionActionStatus.NO_PROOF_OBSERVER,
            action_started=True,
            failure_class="RETURN_FRAME_OBSERVER",
            postflight=safe_session_preflight(),
            independent_safety_check=True,
        )
        effects = engine.ScriptedSessionEffects((no_proof, proved_action()))
        session = open_session(session_contract(), effects)
        session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=safe_session_preflight(),
        )
        resumed = session.resume_after_observer_repair(
            contract.ObserverRepair(
                previous_sha256="5" * 64,
                repaired_sha256="6" * 64,
                focused_tests_passed=True,
                host_only=True,
            ),
            now_epoch_sec=SESSION_START_EPOCH_SEC + 2,
            preflight=safe_session_preflight(),
        )
        result = session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 3,
            preflight=safe_session_preflight(),
        )
        self.assertEqual(resumed["terminal"], "SESSION_ACTIVE")
        self.assertFalse(resumed["observer_repair_required"])
        self.assertEqual(resumed["active_observer_sha256"], "6" * 64)
        self.assertEqual(result["actions_used"], 2)
        self.assertEqual(effects.invoke_count, 2)
        self.assertEqual(
            sum(event.startswith("SESSION_EFFECT:") for event in effects.events),
            2,
        )
        action_events = [
            event for event in effects.events if event.startswith("SESSION_EFFECT:")
        ]
        self.assertTrue(action_events[0].endswith(":" + "5" * 64))
        self.assertTrue(action_events[1].endswith(":" + "6" * 64))

    def test_observer_repair_rejects_same_bytes_failed_tests_and_unsafe_state(self) -> None:
        no_proof = engine.SessionActionResult(
            engine.SessionActionStatus.NO_PROOF_OBSERVER,
            action_started=True,
            failure_class="RETURN_FRAME_OBSERVER",
            postflight=safe_session_preflight(),
            independent_safety_check=True,
        )
        for label, repair, preflight, message in (
            (
                "same-bytes",
                contract.ObserverRepair("5" * 64, "5" * 64, True, True),
                safe_session_preflight(),
                "identity",
            ),
            (
                "tests-failed",
                contract.ObserverRepair("5" * 64, "6" * 64, False, True),
                safe_session_preflight(),
                "focused validation",
            ),
            (
                "unsafe",
                contract.ObserverRepair("5" * 64, "6" * 64, True, True),
                replace(
                    safe_session_preflight(),
                    resident_identity_matches=False,
                ),
                "safe to continue",
            ),
        ):
            with self.subTest(label=label):
                effects = engine.ScriptedSessionEffects((no_proof,))
                session = open_session(session_contract(), effects)
                session.run_action(
                    contract.SessionAction.SWITCHROOT_EXPERIMENT,
                    now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
                    preflight=safe_session_preflight(),
                )
                with self.assertRaisesRegex(contract.ContractError, message):
                    session.resume_after_observer_repair(
                        repair,
                        now_epoch_sec=SESSION_START_EPOCH_SEC + 2,
                        preflight=preflight,
                    )
                self.assertTrue(session.observer_repair_required)
                self.assertEqual(effects.invoke_count, 1)
                self.assertFalse(
                    any(
                        event.startswith("SESSION_OBSERVER_REPAIR:")
                        for event in effects.events
                    )
                )

    def test_observer_no_proof_at_last_budget_closes_without_resume(self) -> None:
        no_proof = engine.SessionActionResult(
            engine.SessionActionStatus.NO_PROOF_OBSERVER,
            action_started=True,
            failure_class="RETURN_FRAME_OBSERVER",
            postflight=safe_session_preflight(),
            independent_safety_check=True,
        )
        effects = engine.ScriptedSessionEffects((no_proof,))
        session = open_session(session_contract(max_actions=1), effects)
        result = session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=safe_session_preflight(),
        )
        self.assertEqual(result["terminal"], "SESSION_CLOSED_BUDGET_EXHAUSTED")
        self.assertFalse(result["observer_repair_required"])
        self.assertFalse(result["session_open"])

    def test_observer_no_proof_without_safe_postflight_requires_recovery(self) -> None:
        malformed = engine.SessionActionResult(
            engine.SessionActionStatus.NO_PROOF_OBSERVER,
            action_started=True,
            failure_class="RETURN_FRAME_OBSERVER",
        )
        effects = engine.ScriptedSessionEffects((malformed,))
        session = open_session(session_contract(), effects)
        result = session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=safe_session_preflight(),
        )
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertFalse(result["session_active"])
        self.assertEqual(effects.invoke_count, 1)

    def test_control_ambiguity_ends_session_for_recovery(self) -> None:
        effects = engine.ScriptedSessionEffects(
            (
                engine.SessionActionResult(
                    engine.SessionActionStatus.CONTROL_AMBIGUOUS,
                    action_started=True,
                    failure_class="RETURN_CONTROL_AMBIGUOUS",
                ),
            )
        )
        session = open_session(session_contract(), effects)
        result = session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=safe_session_preflight(),
        )
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertEqual(result["actions_used"], 1)

    def test_session_preflight_expiry_and_unallowlisted_stop_before_effect(self) -> None:
        unsafe = replace(safe_session_preflight(), operator_attended=False)
        for label, elapsed, action, preflight, terminal in (
            (
                "unsafe",
                SESSION_START_EPOCH_SEC + 1,
                contract.SessionAction.SWITCHROOT_EXPERIMENT,
                unsafe,
                "SESSION_CLOSED_OPERATOR_ABSENT",
            ),
            (
                "expired",
                SESSION_START_EPOCH_SEC + contract.MAX_ATTENDED_SESSION_DURATION_SEC,
                contract.SessionAction.SWITCHROOT_EXPERIMENT,
                safe_session_preflight(),
                "SESSION_CLOSED_EXPIRED",
            ),
            (
                "unallowlisted",
                SESSION_START_EPOCH_SEC + 1,
                "NATIVE_UI_HIDE",
                safe_session_preflight(),
                "SESSION_CLOSED_UNALLOWLISTED_ACTION",
            ),
        ):
            with self.subTest(label=label):
                effects = engine.ScriptedSessionEffects((proved_action(),))
                session = open_session(session_contract(), effects)
                result = session.run_action(
                    action,  # type: ignore[arg-type]
                    now_epoch_sec=elapsed,
                    preflight=preflight,
                )
                self.assertEqual(result["terminal"], terminal)
                self.assertEqual(effects.invoke_count, 0)
                self.assertEqual(result["actions_used"], 0)

    def test_session_opening_checks_window_and_health_before_approval(self) -> None:
        for label, now, preflight, message in (
            (
                "too-early",
                SESSION_START_EPOCH_SEC - 1,
                safe_session_preflight(),
                "window",
            ),
            (
                "expired",
                SESSION_START_EPOCH_SEC
                + contract.MAX_ATTENDED_SESSION_DURATION_SEC,
                safe_session_preflight(),
                "window",
            ),
            (
                "unsafe",
                SESSION_START_EPOCH_SEC,
                replace(safe_session_preflight(), rollback_ready=False),
                "safe to continue",
            ),
        ):
            with self.subTest(label=label):
                effects = engine.ScriptedSessionEffects((proved_action(),))
                with self.assertRaisesRegex(contract.ContractError, message):
                    engine.open_attended_session(
                        session_contract(),
                        effects,
                        now_epoch_sec=now,
                        preflight=preflight,
                    )
                self.assertEqual(effects.events, [])

    def test_session_identity_loss_before_action_requires_recovery(self) -> None:
        effects = engine.ScriptedSessionEffects((proved_action(),))
        session = open_session(session_contract(), effects)
        result = session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=replace(
                safe_session_preflight(),
                resident_identity_matches=False,
            ),
        )
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertEqual(result["device_safety_state"], "RECOVERY_REQUIRED")
        self.assertEqual(result["actions_used"], 0)
        self.assertEqual(effects.invoke_count, 0)

    def test_session_budget_closes_after_exact_last_action(self) -> None:
        effects = engine.ScriptedSessionEffects((proved_action(), proved_action()))
        session = engine.open_attended_session(
            session_contract(max_actions=2),
            effects,
            now_epoch_sec=SESSION_START_EPOCH_SEC,
            preflight=safe_session_preflight(),
        )
        session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=safe_session_preflight(),
        )
        result = session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 2,
            preflight=safe_session_preflight(),
        )
        self.assertEqual(result["terminal"], "SESSION_CLOSED_BUDGET_EXHAUSTED")
        self.assertEqual(result["actions_used"], 2)
        self.assertEqual(result["actions_remaining"], 0)
        with self.assertRaisesRegex(contract.ContractError, "already closed"):
            session.run_action(
                contract.SessionAction.SWITCHROOT_EXPERIMENT,
                now_epoch_sec=SESSION_START_EPOCH_SEC + 3,
                preflight=safe_session_preflight(),
            )

    def test_repeated_confirmed_refutation_stops_without_rollback(self) -> None:
        refuted = engine.SessionActionResult(
            engine.SessionActionStatus.REFUTED,
            action_started=True,
            failure_class="DISPLAY_VISIBILITY_REFUTED",
            postflight=safe_session_preflight(),
        )
        effects = engine.ScriptedSessionEffects((refuted, refuted))
        session = open_session(session_contract(), effects)
        first = session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=safe_session_preflight(),
        )
        second = session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 2,
            preflight=safe_session_preflight(),
        )
        self.assertEqual(first["terminal"], "SESSION_ACTIVE")
        self.assertEqual(second["terminal"], "SESSION_CLOSED_REPEATED_REFUTATION")
        self.assertEqual(second["device_safety_state"], "RESIDENT_HEALTHY")
        self.assertFalse(second["rollback_transfer"])
        self.assertEqual(effects.invoke_count, 2)

    def test_prior_session_refutation_counts_toward_live_line_stop(self) -> None:
        signature = contract.ConfirmedRefutation(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            "DISPLAY_VISIBILITY_REFUTED",
        )
        refuted = engine.SessionActionResult(
            engine.SessionActionStatus.REFUTED,
            action_started=True,
            failure_class=signature.failure_class,
            postflight=safe_session_preflight(),
        )
        effects = engine.ScriptedSessionEffects((refuted,))
        session = open_session(
            session_contract(previous_refutations=(signature,)),
            effects,
        )
        result = session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=safe_session_preflight(),
        )
        self.assertEqual(result["terminal"], "SESSION_CLOSED_REPEATED_REFUTATION")
        self.assertEqual(result["device_safety_state"], "RESIDENT_HEALTHY")
        self.assertEqual(effects.invoke_count, 1)

    def test_two_prior_refutations_stop_before_approval_consumption(self) -> None:
        signature = contract.ConfirmedRefutation(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            "DISPLAY_VISIBILITY_REFUTED",
        )
        effects = engine.ScriptedSessionEffects((proved_action(),))
        with self.assertRaisesRegex(contract.ContractError, "stops the live line"):
            open_session(
                session_contract(previous_refutations=(signature, signature)),
                effects,
            )
        self.assertEqual(effects.events, [])

    def test_session_intent_failure_never_invokes_action(self) -> None:
        class IntentFailureEffects(engine.ScriptedSessionEffects):
            def record_action_intent(
                self,
                binding: contract.AttendedSessionBinding,
                ordinal: int,
                action: contract.SessionAction,
                observer_sha256: str,
            ) -> None:
                raise OSError("journal unavailable")

        effects = IntentFailureEffects((proved_action(),))
        session = open_session(session_contract(), effects)
        result = session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=safe_session_preflight(),
        )
        self.assertEqual(result["terminal"], "SESSION_CLOSED_INTENT_FAILED")
        self.assertEqual(result["actions_used"], 0)
        self.assertEqual(effects.invoke_count, 0)

    def test_session_action_exception_is_not_retried(self) -> None:
        effects = engine.ScriptedSessionEffects(())
        session = open_session(session_contract(), effects)
        result = session.run_action(
            contract.SessionAction.SWITCHROOT_EXPERIMENT,
            now_epoch_sec=SESSION_START_EPOCH_SEC + 1,
            preflight=safe_session_preflight(),
        )
        self.assertEqual(result["terminal"], "RECOVERY_REQUIRED")
        self.assertEqual(result["actions_used"], 1)
        self.assertEqual(effects.invoke_count, 1)

    def test_session_approval_cannot_be_consumed_twice(self) -> None:
        effects = engine.ScriptedSessionEffects((proved_action(),))
        exact = session_contract()
        open_session(exact, effects)
        with self.assertRaisesRegex(contract.ContractError, "already consumed"):
            open_session(exact, effects)

    def test_session_cli_scenarios_are_host_only_and_bounded(self) -> None:
        two = cli.simulate("session-two-actions")
        no_proof = cli.simulate("session-observer-no-proof")
        ambiguous = cli.simulate("session-control-ambiguous")
        expired = cli.simulate("session-expired")
        unallowlisted = cli.simulate("session-unallowlisted")
        self.assertEqual(two["result"]["terminal"], "SESSION_ACTIVE")
        self.assertEqual(two["result"]["actions_used"], 2)
        self.assertEqual(
            no_proof["result"]["action_results"][0]["status"],
            "NO_PROOF_OBSERVER",
        )
        self.assertEqual(
            no_proof["result"]["terminal"],
            "SESSION_PAUSED_OBSERVER_REPAIR_REQUIRED",
        )
        self.assertEqual(ambiguous["result"]["terminal"], "RECOVERY_REQUIRED")
        self.assertEqual(expired["result"]["actions_used"], 0)
        self.assertEqual(unallowlisted["result"]["actions_used"], 0)
        for result in (two, no_proof, ambiguous, expired, unallowlisted):
            self.assertTrue(result["host_only"])
            self.assertFalse(result["device_action"])
            self.assertFalse(result["live_backend_present"])

    def test_imports_have_no_write_surface_in_disposable_namespace(self) -> None:
        if shutil.which("bwrap") is None:
            self.skipTest("bubblewrap is unavailable")
        with tempfile.TemporaryDirectory(prefix="a90-transition-import-") as raw:
            root = Path(raw)
            reval = root / "workspace/public/src/scripts/revalidation"
            server = root / "workspace/public/src/scripts/server-distro"
            reval.mkdir(parents=True)
            server.mkdir(parents=True)
            for source, target in (
                (REVAL_DIR / "a90_transition_contract_v2.py", reval),
                (SERVER_DIR / "a90_transition_engine_v2.py", server),
                (SERVER_DIR / "a90_transition_v2.py", server),
            ):
                shutil.copy2(source, target / source.name)
            self.assertFalse((root / "workspace/private").exists())
            code = (
                "import sys;"
                "sys.path[:0]=['/repo/workspace/public/src/scripts/revalidation',"
                "'/repo/workspace/public/src/scripts/server-distro'];"
                "import a90_transition_contract_v2;"
                "import a90_transition_engine_v2;"
                "import a90_transition_v2"
            )
            completed = subprocess.run(
                [
                    "bwrap",
                    "--ro-bind", "/usr", "/usr",
                    "--ro-bind", "/lib", "/lib",
                    "--ro-bind", "/lib64", "/lib64",
                    "--ro-bind", str(root), "/repo",
                    "--proc", "/proc",
                    "--dev", "/dev",
                    "--tmpfs", "/tmp",
                    "/usr/bin/python3", "-I", "-c", code,
                ],
                check=False,
                capture_output=True,
                text=True,
                env={"PYTHONDONTWRITEBYTECODE": "1"},
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
