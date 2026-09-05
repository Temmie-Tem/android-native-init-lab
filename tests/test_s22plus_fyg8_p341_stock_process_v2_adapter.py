from __future__ import annotations

from pathlib import Path
import copy
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
REVALIDATION = ROOT / "workspace/public/src/scripts/revalidation"
if str(REVALIDATION) not in sys.path:
    sys.path.insert(0, str(REVALIDATION))

import s22plus_fyg8_p341_stock_process_v2_adapter as adapter  # noqa: E402


class P341AdapterTests(unittest.TestCase):
    def test_audit_is_fresh_host_first_and_no_live_authority(self) -> None:
        value = adapter.audit()
        self.assertEqual(value["schema"], adapter.SCHEMA)
        self.assertEqual(value["run_id"], adapter.P341_RUN_ID_HEX)
        self.assertEqual(value["predecessor_run_id"], adapter.P340_PREDECESSOR_RUN_ID_HEX)
        self.assertEqual(value["overlay_contract_id"], adapter.OVERLAY_CONTRACT_ID)
        self.assertEqual(value["decoder"], adapter.DECODER_ID)
        self.assertTrue(value["host_first_open"])
        self.assertFalse(value["later_action_lease_active"])
        self.assertFalse(value["device_contact"])
        self.assertFalse(value["live_authorized"])
        self.assertFalse(value["successful_wire_exchange_unchanged"])

    def test_acceptance_round_trip_and_strict_type_rejection(self) -> None:
        value = adapter.acceptance_fixture()
        self.assertEqual(value["run_id"], adapter.P341_RUN_ID_HEX)
        self.assertEqual(value["decoder"], adapter.DECODER_ID)
        self.assertEqual(value["observer_contract_id"], adapter.OBSERVER_CONTRACT_ID)
        self.assertIs(adapter.validate_acceptance_item(value), value)
        changed = copy.deepcopy(value)
        changed["host_first_open"] = 1
        with self.assertRaises(adapter.ContractError):
            adapter.validate_acceptance_item(changed)

    def test_contract_requires_fresh_overlay_and_policy(self) -> None:
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
        }
        self.assertIs(adapter.validate_contract(contract), contract)
        stale = dict(contract)
        stale["userspace_overlay_contract_id"] = "s22plus-fyg8-p340-open-header-capture-v1"
        with self.assertRaises(adapter.ContractError):
            adapter.validate_contract(stale)


if __name__ == "__main__":
    unittest.main()
