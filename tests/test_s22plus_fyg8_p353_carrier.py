"""Real P353-bound Carrier encoder and decoder; supplemental evidence only."""
import copy
import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'workspace/public/src/scripts/revalidation'))
import s22plus_fyg8_p353_stock_process_v2_adapter as adapter


def full(record):return bytes(adapter.RAW_SIZE-len(record))+record


class CarrierTests(unittest.TestCase):
    def test_all_terminal_states_roundtrip_without_visual_promotion(self):
        parser=adapter._raw_parser()
        for state in ('COMPLETE','INCOMPLETE','AMBIGUOUS'):
            value=adapter.classify_observation(full(adapter.encode_fixture(state=state)))
            self.assertEqual(value['exact_record_count'],1)
            self.assertEqual(value['proof_class'],parser.PROOF_CLASS_BY_STATE[state])
            self.assertFalse(value['candidate_success']);self.assertFalse(value['causal_result_allowed'])
            self.assertEqual(value['p353_stock'][0]['state'],state)

    def test_wrong_run_corrupt_carrier_and_detail_state_are_rejected(self):
        parser=adapter._raw_parser()
        payload=parser._observer().encode_stock_payload_v4(parser._base_payload(state='COMPLETE'),None)
        envelope=parser._envelope_from_payload(payload)
        wrong=parser._carrier_record_from_envelope(envelope,detail=parser.STOCK_DETAIL_COMPLETE,run_id=bytes.fromhex('c352f1e0a90b5e6d7c8a9b0c1d2e3f0f'))
        mismatch=parser._carrier_record_from_envelope(envelope,detail=parser.STOCK_DETAIL_INCOMPLETE,run_id=adapter.P353_RUN_ID)
        corrupt=bytearray(adapter.encode_fixture());corrupt[-2]^=1
        for record in (wrong,mismatch,bytes(corrupt)):
            value=adapter.classify_observation(full(record));self.assertFalse(value['accepted'])
            self.assertFalse(value['candidate_success'])

    def test_baseline_and_contract_remain_separate_from_dispatch(self):
        adapter.validate_acceptance_item(adapter.acceptance_fixture())
        adapter.validate_contract(adapter.audit()['contract'])
        self.assertTrue(adapter.classify_clean_baseline(bytes(adapter.RAW_SIZE))['baseline_clean'])
        with self.assertRaises(adapter.ContractError):adapter.classify_clean_baseline(full(adapter.encode_fixture()))


if __name__=='__main__':unittest.main()
