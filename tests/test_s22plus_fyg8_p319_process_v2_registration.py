import hashlib
from types import SimpleNamespace
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "workspace/public/src/scripts/revalidation"
sys.path.insert(0, str(SCRIPTS))

import device_action_f1_evidence_v2 as evidence
import device_action_f1_live_v2 as live
import device_action_f1_v2 as core
import s22plus_fyg8_p319_stock_process_v2_adapter as adapter
import s22plus_fyg8_p310_carrier_model as carrier


class P319ProcessV2RegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.acceptance = adapter.acceptance_fixture()
        cls.record_size = carrier.LONG_RECORD_SIZE

    @classmethod
    def full(cls, state="COMPLETE"):
        return bytes(adapter.RAW_SIZE - cls.record_size) + adapter.encode_fixture(
            state=state
        )

    def classify(self, raw):
        return evidence.classify_e1_latest_stage(raw, self.acceptance)

    def test_selector_is_exact_and_not_generic_p318(self):
        selected = evidence._latest_stage_observation_decoder(
            adapter.PARENT_SOURCE_CONTRACT_ID,
            adapter.PROFILE,
            adapter.OVERLAY_CONTRACT_ID,
        )
        self.assertIs(selected, adapter)
        for source, profile, overlay in (
            ("wrong-source", adapter.PROFILE, adapter.OVERLAY_CONTRACT_ID),
            (adapter.PARENT_SOURCE_CONTRACT_ID, "E1B", adapter.OVERLAY_CONTRACT_ID),
            (adapter.PARENT_SOURCE_CONTRACT_ID, adapter.PROFILE, "p318"),
        ):
            with self.assertRaises(evidence.EvidenceError):
                evidence._latest_stage_observation_decoder(source, profile, overlay)

    def test_acceptance_identity_is_strict(self):
        self.assertIs(
            evidence.validate_acceptance(self.acceptance), self.acceptance
        )
        mutations = []
        changed = dict(self.acceptance)
        changed["run_id"] = "0" * 32
        mutations.append(changed)
        changed = dict(self.acceptance)
        changed["forged"] = True
        mutations.append(changed)
        changed = dict(self.acceptance)
        changed["userspace_overlay_contract_id"] = "p318"
        mutations.append(changed)
        for value in mutations:
            with self.assertRaises(evidence.EvidenceError):
                evidence.validate_acceptance(value)

    def test_three_stock_states_keep_distinct_proof_classes(self):
        expected = {
            "COMPLETE": (True, "NONCAUSAL_SUCCESS_PATH"),
            "INCOMPLETE": (False, "NO_PROOF_EXPERIMENT_PRECONDITION"),
            "AMBIGUOUS": (False, "NO_PROOF_OBSERVER"),
        }
        for state, (accepted, proof) in expected.items():
            result = self.classify(self.full(state))
            self.assertIs(result["accepted"], accepted)
            self.assertEqual(result["proof_class"], proof)
            self.assertEqual(result["p319_stock"][0]["stock"]["state"], state)
            self.assertIs(result["causal_result_allowed"], False)
            self.assertIs(result["candidate_success"], False)
            self.assertIs(result["mux_result_claimable"], False)
            self.assertIs(result["host_silent_claimable"], False)
            self.assertIs(result["acm_supplemental"], True)
            self.assertIs(result["acm_required_for_acceptance"], False)

    def test_malformed_foreign_and_multiplicity_are_observer_no_proof(self):
        valid = adapter.encode_fixture()
        duplicate = valid + bytes(adapter.RAW_SIZE - (2 * self.record_size)) + valid
        foreign = (
            carrier.unsat_record(adapter.PROFILE, adapter.STOCK_RUN_ID)
            + bytes(adapter.RAW_SIZE - len(valid) - 24)
            + valid
        )
        malformed = adapter._mutate_terminal_detail(self.full(), 0x6725)
        for raw in (duplicate, foreign, malformed):
            result = self.classify(raw)
            self.assertFalse(result["accepted"])
            self.assertEqual(result["proof_class"], "NO_PROOF_OBSERVER")
            projection = live._p319_terminal_projection(result)
            self.assertEqual(projection["proof_class"], "NO_PROOF_OBSERVER")

    def test_overlay_metadata_does_not_invent_intent(self):
        metadata = {
            "userspace_overlay_contract_id": adapter.OVERLAY_CONTRACT_ID,
            "decoder": adapter.DECODER_ID,
            "policy_id": adapter.POLICY_ID,
            "profile": adapter.PROFILE,
            "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
            "acm_supplemental": True,
        }
        self.assertEqual(
            evidence._validate_userspace_overlay_contract(
                metadata, adapter.OVERLAY_CONTRACT_ID
            ),
            metadata,
        )
        with self.assertRaises(evidence.EvidenceError):
            evidence._validate_userspace_overlay_contract(
                {**metadata, "p318_topology_causal_correlation": True},
                adapter.OVERLAY_CONTRACT_ID,
            )

    def test_source_receipt_override_and_optional_acm(self):
        receipts = core.execution_critical_source_receipts(self.acceptance)
        expected_names = {
            f"p319_adapter_source_{name}" for name in adapter.SOURCE_KEYS
        }
        self.assertEqual(expected_names, expected_names & set(receipts))
        self.assertEqual(
            core._overridden_candidate_sources(adapter.OVERLAY_CONTRACT_ID),
            frozenset({"p310_telemetry_decoder"}),
        )
        core.verify_candidate_observer_binding(self.acceptance, None)
        observer = {"usb_product_id": "wrong"}
        with self.assertRaises(core.F1V2Error):
            core.verify_candidate_observer_binding(self.acceptance, observer)
        closure = live._closure(ROOT)
        self.assertTrue(
            {"p319_stock_adapter", "p319_carrier_model", "p319_telemetry_spec"}
            <= set(closure["sources"])
        )

    def test_source_binding_requires_the_three_adapter_receipts(self):
        receipts = core.execution_critical_source_receipts(self.acceptance)
        selected = core._selected_candidate_source_contract(
            adapter.PARENT_SOURCE_CONTRACT_ID, adapter.PROFILE
        )
        source_data = selected.source_bytes(adapter.ROOT)
        verification = {
            "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
            "userspace_overlay_contract_id": adapter.OVERLAY_CONTRACT_ID,
            "candidate_source_receipts": {
                name: {
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
                for name, data in source_data.items()
            },
            "p319_adapter_source_receipts": {
                name: receipts[f"p319_adapter_source_{name}"]
                for name in adapter.SOURCE_KEYS
            },
        }
        core.verify_candidate_source_binding(self.acceptance, verification, receipts)
        bad = dict(verification)
        bad["p319_adapter_source_receipts"] = dict(
            verification["p319_adapter_source_receipts"]
        )
        bad["p319_adapter_source_receipts"]["stock_process_v2_adapter"] = {
            "size": 1,
            "sha256": "0" * 64,
        }
        with self.assertRaises(core.F1V2Error):
            core.verify_candidate_source_binding(self.acceptance, bad, receipts)

    def test_offline_promotion_stays_blocked_until_p319_static_exists(self):
        with self.assertRaisesRegex(
            evidence.EvidenceError, "P3.19 Process-v2 offline promotion"
        ):
            evidence._verify_e1_latest_stage_offline_contract(
                self.acceptance,
                payloads={},
                receipts={},
                candidate_ap={},
            )

    def test_live_projection_and_terminal_outcomes_are_typed(self):
        expected = {
            "COMPLETE": "p319_noncausal_success_path_rollback_verified",
            "INCOMPLETE": "p319_experiment_precondition_unproved_rollback_verified",
            "AMBIGUOUS": "p319_observer_no_proof_rollback_verified",
        }
        prepared = SimpleNamespace(
            bundle=SimpleNamespace(
                manifest={"observation": {"acceptance": self.acceptance}}
            )
        )
        self.assertTrue(live._p319_bundle(prepared.bundle))
        self.assertFalse(live._p318_bundle(prepared.bundle))
        self.assertFalse(live._p313_bundle(prepared.bundle))
        for state, outcome in expected.items():
            projection = live._p319_terminal_projection(self.classify(self.full(state)))
            self.assertEqual(projection["proof_class"], self.classify(self.full(state))["proof_class"])
            self.assertEqual(
                live.P319_OUTCOME_BY_PROOF_CLASS[projection["proof_class"]], outcome
            )
            with mock.patch.object(
                live,
                "_state",
                return_value={
                    "p319_stock": projection,
                    "p319_proof_class": projection["proof_class"],
                    "final_evidence": {"observer": {"p319_stock": projection}},
                },
            ):
                verdict, actual = live._closed_terminal_classification(prepared)
            self.assertEqual(verdict, "NO_PROOF_F1_V2_CANDIDATE_ROLLED_BACK")
            self.assertEqual(actual, outcome)

            divergent = {
                "p319_stock": projection,
                "p319_proof_class": projection["proof_class"],
                "final_evidence": {
                    "observer": {
                        "p319_stock": {
                            **projection,
                            "proof_class": "NO_PROOF_OBSERVER",
                        }
                    }
                },
            }
            if projection["proof_class"] != "NO_PROOF_OBSERVER":
                with self.assertRaises(live.F1LiveError):
                    live._p319_durable_projection(divergent)


if __name__ == "__main__":
    unittest.main()
