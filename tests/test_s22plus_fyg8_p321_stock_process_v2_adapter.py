from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "workspace/public/src/scripts/revalidation/"
    "s22plus_fyg8_p321_stock_process_v2_adapter.py"
)
SPEC = importlib.util.spec_from_file_location("p321_stock_adapter", SOURCE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("P3.21 adapter source cannot be loaded")
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)


class P321StockProcessAdapterTests(unittest.TestCase):
    def test_all_current_run_aliases_bind_fresh_p321(self) -> None:
        self.assertEqual(adapter.RUN_ID, adapter.P321_RUN_ID)
        self.assertEqual(adapter.STOCK_RUN_ID, adapter.P321_RUN_ID)
        self.assertEqual(adapter.P320_RUN_ID, adapter.P321_RUN_ID)
        self.assertEqual(adapter.P320_STOCK_RUN_ID, adapter.P321_RUN_ID)
        self.assertEqual(
            adapter.PREDECESSOR_P320_RUN_ID,
            bytes.fromhex("c320f1e0a90b5e6d7c8a9b0c1d2e3f40"),
        )

    def test_lineage_and_acceptance_bind_p321_and_previous_p320(self) -> None:
        lineage = adapter.bind_exact_sources()
        self.assertEqual(lineage["run_id"], adapter.P321_RUN_ID.hex())
        self.assertEqual(
            lineage["predecessor_run_id_rejected"],
            adapter.PREDECESSOR_P320_RUN_ID.hex(),
        )
        acceptance = adapter.validate_acceptance_item(adapter.acceptance_fixture())
        self.assertEqual(acceptance["run_id"], adapter.P321_RUN_ID.hex())
        self.assertEqual(acceptance["decoder"], adapter.P321_DECODER_ID)
        self.assertEqual(acceptance["policy_id"], adapter.P321_POLICY_ID)

    def test_both_predecessor_carrier_ids_are_rejected(self) -> None:
        record = adapter.encode_fixture()
        self.assertEqual(
            adapter.decode_record(record)["carrier"]["run_id"],
            adapter.P321_RUN_ID.hex(),
        )
        for old_run_id in (adapter.P319_RUN_ID, adapter.PREDECESSOR_P320_RUN_ID):
            with self.subTest(old_run_id=old_run_id.hex()):
                with self.assertRaises(adapter.DecodeError):
                    adapter.decode_record(record, expected_run_id=old_run_id)

    def test_audit_reports_previous_p320_without_changing_current_aliases(self) -> None:
        result = adapter.audit()
        self.assertTrue(result["verified"])
        self.assertEqual(result["run_id"], adapter.P321_RUN_ID.hex())
        self.assertEqual(
            result["predecessor_run_id"],
            adapter.PREDECESSOR_P320_RUN_ID.hex(),
        )
        self.assertEqual(result["verdict"], "PASS_P321_STOCK_PROCESS_V2_ADAPTER_H0")


if __name__ == "__main__":
    unittest.main()
