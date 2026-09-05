import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workspace/public/src/scripts/revalidation"))
import s22plus_fyg8_p345_stock_process_v2_adapter as adapter

class P345AdapterTests(unittest.TestCase):
    def raw_for(self, run_id):
        parser = adapter._raw_parser()
        payload = parser._observer().encode_stock_payload_v4(parser._base_payload(state="COMPLETE"), None)
        record = parser._carrier_record_from_envelope(parser._envelope_from_payload(payload),
            detail=parser.STOCK_DETAIL_COMPLETE, run_id=run_id)
        return bytes(parser.RAW_SIZE - len(record)) + record

    def test_actual_crc_current_and_predecessors(self):
        current = adapter.classify_observation(self.raw_for(adapter.P345_RUN_ID))
        self.assertEqual(current["exact_record_count"], 1)
        self.assertEqual(current["foreign_count"], 0)
        for run in (adapter.P344_PREDECESSOR_RUN_ID, bytes.fromhex("c343f1e0a90b5e6d7c8a9b0c1d2e3f9b")):
            value = adapter.classify_observation(self.raw_for(run))
            self.assertFalse(value["accepted"])
            self.assertEqual(value["exact_record_count"], 0)
            self.assertGreater(value["foreign_count"], 0)
            self.assertFalse(value["predecessor_raw_relabelled"])

    def test_baseline_not_relabelled(self):
        for run in (adapter.P345_RUN_ID, adapter.P344_PREDECESSOR_RUN_ID):
            with self.assertRaises(adapter.ContractError):
                adapter.classify_clean_baseline(self.raw_for(run))
        self.assertTrue(adapter.classify_clean_baseline(bytes(adapter.RAW_SIZE))["baseline_clean"])

    def test_contract_and_acceptance(self):
        value = adapter.audit()
        adapter.validate_contract(value["contract"])
        self.assertFalse(value["runtime_behavior_unchanged"])
        self.assertFalse(value["catalog_unchanged"])
        self.assertFalse(value["later_action_lease_active"])
        acceptance = adapter.acceptance_fixture()
        adapter.validate_acceptance_item(acceptance)
        for key, stale in (("run_id", adapter.P344_PREDECESSOR_RUN_ID_HEX), ("candidate_success", 0)):
            bad = copy.deepcopy(acceptance); bad[key] = stale
            with self.assertRaises(adapter.ContractError):
                adapter.validate_acceptance_item(bad)

if __name__ == "__main__":
    unittest.main()
