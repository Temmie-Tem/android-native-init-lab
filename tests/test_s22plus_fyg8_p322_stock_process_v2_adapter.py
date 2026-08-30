from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p322_stock_process_v2_adapter.py"
)
SPEC = importlib.util.spec_from_file_location("p322_stock_adapter", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("P3.22 adapter source cannot be loaded")
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class P322StockProcessAdapterTests(unittest.TestCase):
    def test_lineage_aliases_and_default_run_ids_are_bound(self) -> None:
        self.assertEqual(adapter.RUN_ID, adapter.P322_RUN_ID)
        self.assertEqual(adapter.STOCK_RUN_ID, adapter.P322_RUN_ID)
        self.assertEqual(adapter.P321_RUN_ID.hex(), "c321f1e0a90b5e6d7c8a9b0c1d2e3f4b")
        self.assertEqual(adapter.P320_RUN_ID.hex(), "c320f1e0a90b5e6d7c8a9b0c1d2e3f40")
        self.assertEqual(adapter.P319_RUN_ID.hex(), "b9cc424d0d184f5accbce94a844e817d")
        self.assertEqual(adapter.PREDECESSOR_P321_RUN_ID, adapter.P321_RUN_ID)
        self.assertEqual(
            adapter.classify_observation.__kwdefaults__["expected_run_id"],
            adapter.P322_RUN_ID,
        )
        self.assertEqual(
            adapter.classify_clean_baseline.__kwdefaults__["expected_run_id"],
            adapter.P322_RUN_ID,
        )

    def test_fixture_and_acceptance_bind_p322_with_p321_predecessor(self) -> None:
        record = adapter.encode_fixture()
        decoded = adapter.decode_record(record)
        self.assertEqual(decoded["carrier"]["run_id"], adapter.P322_RUN_ID_HEX)
        self.assertEqual(decoded["schema"], adapter.SCHEMA)

        lineage = adapter.bind_exact_sources()
        self.assertEqual(lineage["run_id"], adapter.P322_RUN_ID_HEX)
        self.assertEqual(
            lineage["predecessor_run_id_rejected"],
            adapter.P321_RUN_ID_HEX,
        )
        self.assertEqual(lineage["overlay_contract_id"], adapter.P322_OVERLAY_CONTRACT_ID)

        acceptance = adapter.validate_acceptance_item(adapter.acceptance_fixture())
        self.assertEqual(acceptance["run_id"], adapter.P322_RUN_ID_HEX)
        self.assertEqual(acceptance["decoder"], adapter.P322_DECODER_ID)
        self.assertEqual(acceptance["policy_id"], adapter.P322_POLICY_ID)
        self.assertEqual(
            acceptance["contract"]["candidate_static"]["path"],
            "p322-stock-observer-v4-fixture",
        )

    def test_all_predecessor_carrier_ids_are_rejected(self) -> None:
        record = adapter.encode_fixture()
        self.assertEqual(
            adapter.decode_record(record)["carrier"]["run_id"],
            adapter.P322_RUN_ID_HEX,
        )
        for old_run_id in (adapter.P319_RUN_ID, adapter.P320_RUN_ID, adapter.P321_RUN_ID):
            with self.subTest(old_run_id=old_run_id.hex()):
                with self.assertRaises(adapter.DecodeError):
                    adapter.decode_record(record, expected_run_id=old_run_id)

    def test_audit_reports_p322_and_p321_predecessor(self) -> None:
        result = adapter.audit()
        self.assertTrue(result["verified"])
        self.assertEqual(result["run_id"], adapter.P322_RUN_ID_HEX)
        self.assertEqual(result["predecessor_run_id"], adapter.P321_RUN_ID_HEX)
        self.assertEqual(result["schema"], "s22plus_fyg8_p322_stock_process_v2_adapter_v1")
        self.assertEqual(result["verdict"], "PASS_P322_STOCK_PROCESS_V2_ADAPTER_H0")
        self.assertEqual(result["decoder"], adapter.P322_DECODER_ID)
        self.assertEqual(result["policy_id"], adapter.P322_POLICY_ID)


if __name__ == "__main__":
    unittest.main()
