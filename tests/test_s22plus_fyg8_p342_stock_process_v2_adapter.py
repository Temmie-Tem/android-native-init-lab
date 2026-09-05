from __future__ import annotations

from pathlib import Path
import copy
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p342_stock_process_v2_adapter as adapter  # noqa: E402


class P342AdapterTests(unittest.TestCase):
    def test_actual_carrier_run_matching_precedes_public_projection(self):
        parser = adapter._raw_parser()
        def raw_for(run_id):
            payload = parser._observer().encode_stock_payload_v4(parser._base_payload(state='COMPLETE'), None)
            record = parser._carrier_record_from_envelope(parser._envelope_from_payload(payload),
                detail=parser.STOCK_DETAIL_COMPLETE, run_id=run_id)
            return bytes(parser.RAW_SIZE - len(record)) + record
        current = raw_for(adapter.P342_RUN_ID)
        value = adapter.classify_observation(current)
        self.assertEqual(value['exact_record_count'], 1)
        self.assertEqual(value['foreign_count'], 0)
        self.assertEqual(value['run_id'], adapter.P342_RUN_ID_HEX)
        self.assertEqual(value['proof_class'], 'NONCAUSAL_SUCCESS_PATH')
        # Explicit IDs are supplied before CRC generation; no raw-byte rewrite
        # or mutation of shared parser globals/defaults is used.
        previous = raw_for(adapter.P341_PREDECESSOR_RUN_ID)
        rejected = adapter.classify_observation(previous)
        self.assertEqual(rejected['exact_record_count'], 0)
        self.assertGreater(rejected['foreign_count'], 0)
        self.assertFalse(rejected['accepted'])
        for payload in (current, previous):
            with self.assertRaises(adapter.AdapterIdentityError):
                adapter.classify_clean_baseline(payload)
        self.assertTrue(adapter.classify_clean_baseline(bytes(parser.RAW_SIZE))['baseline_clean'])

    def test_audit_is_fresh_idle_reuse_and_no_live_authority(self) -> None:
        value = adapter.audit()
        self.assertEqual(value["schema"], adapter.SCHEMA)
        self.assertEqual(value["run_id"], adapter.P342_RUN_ID_HEX)
        self.assertEqual(value["predecessor_run_id"], adapter.P341_PREDECESSOR_RUN_ID_HEX)
        self.assertEqual(value["overlay_contract_id"], adapter.OVERLAY_CONTRACT_ID)
        self.assertEqual(value["decoder"], adapter.DECODER_ID)
        self.assertEqual(value["same_fd_session_count"], 3)
        self.assertEqual(value["idle_seconds"], 120)
        self.assertEqual(value["total_sessions"], 4)
        self.assertEqual(value["total_commands"], 12)
        self.assertTrue(value["runtime_behavior_unchanged"])
        self.assertFalse(value["later_action_lease_active"])
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])

    def test_acceptance_round_trip_and_strict_type_rejection(self) -> None:
        value = adapter.acceptance_fixture()
        self.assertEqual(value["run_id"], adapter.P342_RUN_ID_HEX)
        self.assertEqual(value["decoder"], adapter.DECODER_ID)
        self.assertEqual(value["observer_contract_id"], adapter.OBSERVER_CONTRACT_ID)
        self.assertEqual(value["initial_session_count"], 4)
        self.assertEqual(value["same_fd_session_count"], 3)
        self.assertEqual(value["idle_seconds"], 120)
        self.assertEqual(value["total_commands"], 12)
        self.assertIs(adapter.validate_acceptance_item(value), value)
        changed = copy.deepcopy(value)
        changed["idle_seconds"] = True
        with self.assertRaises(adapter.ContractError):
            adapter.validate_acceptance_item(changed)

    def test_contract_requires_fresh_overlay_policy_and_idle_geometry(self) -> None:
        contract = {
            "userspace_overlay_contract_id": adapter.OVERLAY_CONTRACT_ID,
            "decoder": adapter.DECODER_ID,
            "policy_id": adapter.POLICY_ID,
            "profile": adapter.PROFILE,
            "source_contract_id": adapter.PARENT_SOURCE_CONTRACT_ID,
            "observer_contract_id": adapter.OBSERVER_CONTRACT_ID,
            "payload_abi": 4,
            "observer_receipt_size": 15,
            "causal_result_allowed": False,
            "candidate_success": False,
            "runtime_behavior_unchanged": True,
            "same_fd_session_count": 3,
            "idle_seconds": 120,
            "total_session_count": 4,
            "total_command_count": 12,
        }
        self.assertIs(adapter.validate_contract(contract), contract)
        stale = dict(contract)
        stale["userspace_overlay_contract_id"] = "s22plus-fyg8-p341-host-first-open-v1"
        with self.assertRaises(adapter.ContractError):
            adapter.validate_contract(stale)


if __name__ == "__main__":
    unittest.main()
