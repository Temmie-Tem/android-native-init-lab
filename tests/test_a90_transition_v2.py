from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
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
        self.assertEqual(result["terminal"], "PROMOTED_CLOSED")
        self.assertEqual(result["counts"]["CANDIDATE_FLASH"], 1)
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
